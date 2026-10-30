"""Per-request enforcement around the existing compact Nemotron tool loop."""
import json
from types import SimpleNamespace

from leakprobe.ui.live_policy import (LiveDenied, MAX_BYTES, MAX_OUTPUT, MAX_REQUESTS,
                                      MAX_TOTAL_BYTES, MAX_TOKEN_ALLOWANCE)


def provider(authority, lease):
    # This factory is never constructed during navigation or before authorization.
    if authority.active is not lease:
        raise LiveDenied('No active paid-request authorization.')
    authority.ready(lease['token'], lease['session'])
    import httpx
    from openai import OpenAI
    transport = httpx.Client(follow_redirects=False, trust_env=False,
                            timeout=httpx.Timeout(20, connect=5, write=10, pool=5))
    return OpenAI(api_key=authority.policy.api_key, base_url=authority.policy.endpoint,
                  timeout=20, max_retries=0, http_client=transport)


class ProtectedClient:
    def __init__(self, authority, lease, client):
        self.authority, self.lease, self.client = authority, lease, client
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    def create(self, **payload):
        a, lease = self.authority, self.lease
        with a.lock:
            try:
                a.ready(lease['token'], lease['session'])
            except LiveDenied as exc:
                lease['stop'] = str(exc)
                raise
            if a.active is not lease or lease['stop'] or a.clock() >= lease['deadline']:
                lease['stop'] = lease['stop'] or 'Investigation deadline reached.'
                raise LiveDenied(lease['stop'])
            if (set(payload) != {'model', 'messages', 'tools', 'tool_choice', 'max_tokens'}
                    or payload['model'] != a.policy.model or payload['max_tokens'] != MAX_OUTPUT):
                lease['stop'] = 'Unexpected provider request configuration.'
                raise LiveDenied(lease['stop'])
            size = len(json.dumps(payload, separators=(',', ':'), allow_nan=False).encode())
            allowance = size + 1024 + MAX_OUTPUT
            if (size > MAX_BYTES or lease['bytes'] + size > MAX_TOTAL_BYTES
                    or lease['requests'] >= MAX_REQUESTS or lease['tokens'] + allowance > MAX_TOKEN_ALLOWANCE):
                lease['stop'] = 'Server request, context or token allowance reached.'
                raise LiveDenied(lease['stop'])
            lease['requests'] += 1
            lease['bytes'] += size
            lease['tokens'] += allowance
            receipt = {'request': lease['requests'], 'input_bytes': size,
                       'input_token_allowance': size + 1024, 'max_output_tokens': MAX_OUTPUT,
                       'timeout_seconds': min(20, max(0.1, lease['deadline'] - a.clock())), 'status': 'started'}
            lease['request_receipts'].append(receipt)
        try:
            # Explicit timeout and no SDK retries. The concurrency lease is held until
            # the synchronous request returns, including on browser disconnection.
            response = self.client.chat.completions.create(**payload, timeout=receipt['timeout_seconds'])
        except Exception:
            receipt['status'] = 'failed_or_timeout'
            lease['stop'] = 'Provider unavailable or timed out. No automatic retry; reservation retained.'
            raise LiveDenied(lease['stop']) from None
        receipt['status'] = 'received'
        usage = getattr(response, 'usage', None)
        usage = usage.model_dump() if hasattr(usage, 'model_dump') else usage
        if isinstance(usage, dict):
            receipt['usage'] = {key: usage.get(key) for key in ('prompt_tokens', 'completion_tokens', 'total_tokens')}
            bounds = {'prompt_tokens': size + 1024, 'completion_tokens': MAX_OUTPUT,
                      'total_tokens': allowance}
            if any(type(usage.get(key)) is not int or not 0 <= usage[key] <= bound for key, bound in bounds.items()):
                lease['stop'] = 'Provider usage was incomplete or exceeded the reserved bounds. Live requests locked.'
                a.poisoned = True
        else:
            receipt['usage'] = 'not_reported'
            lease['stop'] = 'Provider did not report usage. No further requests; reservation retained.'
        if a.clock() >= lease['deadline']:
            lease['stop'] = 'Investigation deadline reached; no further requests.'
        return response

    def close(self):
        if callable(getattr(self.client, 'close', None)):
            self.client.close()
