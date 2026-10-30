"""Operator-gated inference with a shared, process-local usage allowance."""
from collections import deque
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
import hashlib
import hmac
import os
import secrets
import threading
import time

MODEL = 'nvidia/nemotron-3-super-120b-a12b'
ENDPOINTS = ('https://api.tokenfactory.us-central1.nebius.com/v1/',
             'https://api.tokenfactory.nebius.com/v1/')
MAX_REQUESTS, MAX_OUTPUT, MAX_BYTES, MAX_TOTAL_BYTES = 4, 2048, 24000, 72000
MAX_TOKEN_ALLOWANCE = 131072
UNAVAILABLE = 'Restricted live AI is not configured. Saved investigations remain available.'


class LiveDenied(RuntimeError):
    """Safe, fixed policy explanation; never include provider exception text."""


def password_hash(password, salt=None):
    if not isinstance(password, str) or not 16 <= len(password) <= 256:
        raise ValueError('Use an access code of 16–256 characters.')
    salt = salt or secrets.token_hex(16)
    value = hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), 310000).hex()
    return f'pbkdf2_sha256$310000${salt}${value}'


def check_hash_shape(value):
    method, iterations, salt, digest = value.split('$')
    if (method != 'pbkdf2_sha256' or not 200000 <= int(iterations) <= 600000
            or len(bytes.fromhex(salt)) != 16 or len(bytes.fromhex(digest)) != 32):
        raise ValueError('Invalid access-code hash.')


@dataclass(frozen=True)
class Policy:
    api_key: str = field(repr=False)
    access_hash: str = field(repr=False)
    input_rate: Decimal = Decimal('2')
    output_rate: Decimal = Decimal('4')
    budget: Decimal = Decimal('0.25')
    max_runs: int = 1
    model: str = MODEL
    endpoint: str = ENDPOINTS[0]

    @classmethod
    def from_settings(cls, values, now=None):
        # Errors identify field names only, never their secret contents.
        if values.get('LEAKPROBE_LIVE_MODE') != 'restricted':
            raise LiveDenied('Live AI is disabled. Set LEAKPROBE_LIVE_MODE to restricted in Cloud Secrets.')
        missing = [name for name in ('NEBIUS_API_KEY', 'LEAKPROBE_OPERATOR_PASSWORD_HASH')
                   if not values.get(name)]
        if missing:
            raise LiveDenied('Missing Cloud Secrets fields: ' + ', '.join(missing) + '. Saved reports remain available.')
        try:
            policy = cls(api_key=values['NEBIUS_API_KEY'], access_hash=values['LEAKPROBE_OPERATOR_PASSWORD_HASH'],
                input_rate=Decimal(values.get('LEAKPROBE_INPUT_USD_PER_MILLION', '2')),
                output_rate=Decimal(values.get('LEAKPROBE_OUTPUT_USD_PER_MILLION', '4')),
                budget=Decimal(values.get('LEAKPROBE_LIVE_BUDGET_USD', '0.25')),
                max_runs=int(values.get('LEAKPROBE_LIVE_MAX_INVESTIGATIONS', '1')),
                model=values.get('NEBIUS_MODEL', MODEL), endpoint=values.get('NEBIUS_BASE_URL', ENDPOINTS[0]))
            check_hash_shape(policy.access_hash)
            if (not policy.api_key.strip() or policy.api_key == 'replace_with_your_key'
                    or policy.model != MODEL
                    or policy.endpoint not in ENDPOINTS
                    or any(not n.is_finite() or n <= 0 for n in (policy.input_rate, policy.output_rate, policy.budget))
                    or policy.budget > Decimal('1.00') or policy.reserve_usd > Decimal('0.25')
                    or policy.reserve_usd > policy.budget):
                raise ValueError('Invalid limits or provider configuration.')
            if not 1 <= policy.max_runs <= 4:
                raise ValueError('Invalid investigation limit.')
            return policy
        except (ValueError, KeyError, TypeError, InvalidOperation, AttributeError):
            raise LiveDenied(UNAVAILABLE) from None

    @property
    def reserve_usd(self):
        # Count serialized request bytes plus protocol overhead as conservative input
        # token allowances. This is a reservation, not a tokenizer or provider invoice.
        return (MAX_REQUESTS * (MAX_BYTES + 1024) * self.input_rate
                + MAX_REQUESTS * MAX_OUTPUT * self.output_rate) / Decimal(1000000)

    def public(self):
        return {'model': self.model, 'endpoint': self.endpoint, 'allowance_scope': 'server_process',
                'budget_usd': str(self.budget), 'run_reservation_usd': str(self.reserve_usd),
                'input_rate_bound': str(self.input_rate), 'output_rate_bound': str(self.output_rate),
                'max_requests': MAX_REQUESTS, 'max_output': MAX_OUTPUT, 'concurrency': 1,
                'max_runs': self.max_runs, 'max_runs_per_case': 2, 'deadline_seconds': 90}

class Authority:
    def __init__(self, policy, clock=time.time, enabled=lambda: True):
        self.policy, self.clock = policy, clock
        self.enabled = enabled
        self.lock = threading.RLock()
        self.tickets, self.failures, self.runs = {}, deque(), []
        self.active, self.spent, self.poisoned = None, Decimal(0), False

    def authenticate(self, password, session):
        with self.lock:
            now = self.clock()
            self.tickets = {key: item for key, item in self.tickets.items() if item[1] > now}
            self.failures = deque(t for t in self.failures if t > now - 600)
            if len(self.failures) >= 6 or len(self.tickets) >= 100:
                raise LiveDenied('Operator access is temporarily locked. Contact the administrator.')
            self.failures.append(now)  # Global across sessions; charge every attempt before hashing.
            try:
                check_hash_shape(self.policy.access_hash)
                _, rounds, salt, wanted = self.policy.access_hash.split('$')
                if not isinstance(password, str) or not 16 <= len(password) <= 256:
                    raise ValueError('Invalid access code.')
                actual = hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), int(rounds)).hex()
                valid = hmac.compare_digest(actual, wanted)
            except (ValueError, AttributeError, TypeError):
                valid = False
            if not valid:
                raise LiveDenied('Operator access was not granted.')
            self.failures.pop()
            token = secrets.token_urlsafe(32)
            self.tickets[token] = (session, now + 900)
            return token

    def authorized(self, token, session):
        with self.lock:
            known = self.tickets.get(token)
            return bool(known and known[0] == session and self.clock() < known[1])

    def logout(self, token):
        with self.lock:
            self.tickets.pop(token, None)

    def ready(self, token, session):
        if not self.enabled():
            raise LiveDenied('Live inference was disabled or its server configuration changed. No further requests.')
        if not self.authorized(token, session):
            raise LiveDenied('Operator sign-in is required before paid requests.')
        if self.poisoned:
            raise LiveDenied('Live AI is locked after a usage-verification error. Saved reports remain available.')

    def can_start(self, token, session):
        """UI and direct calls share these checks; active requests use ready()."""
        with self.lock:
            self.ready(token, session)
            now = self.clock()
            if self.active:
                raise LiveDenied('Another investigation is running. Please wait; no request was sent.')
            if len(self.runs) >= self.policy.max_runs or self.spent + self.policy.reserve_usd > self.policy.budget:
                raise LiveDenied('The server AI usage allowance is exhausted. Saved reports remain available.')
            if (sum(r['session'] == session and r['at'] > now - 3600 for r in self.runs) >= 2
                    or sum(r['at'] > now - 60 for r in self.runs) >= 2):
                raise LiveDenied('Live request rate limit reached. No request was sent.')

    def begin(self, token, session, alert_id):
        with self.lock:
            self.can_start(token, session)
            if not isinstance(alert_id, str) or not 1 <= len(alert_id) <= 256:
                raise LiveDenied('A current monitoring alert is required.')
            now = self.clock()
            if sum(r['alert'] == alert_id for r in self.runs) >= 2:
                raise LiveDenied('The investigation limit for this record was reached. No request was sent.')
            lease = {'id': secrets.token_hex(16), 'alert': alert_id, 'session': session, 'token': token,
                     'at': now, 'deadline': now + 90, 'requests': 0, 'bytes': 0, 'tokens': 0,
                     'stop': None, 'request_receipts': []}
            self.runs.append(lease)
            self.spent += self.policy.reserve_usd  # Never refund, including failures/unknown usage.
            self.active = lease
            return lease

    def end(self, lease):
        with self.lock:
            if self.active is lease:
                self.active = None

    def audit(self, lease):
        return {'source': 'live_nebius', 'run_id': lease['id'], 'reservation_usd': str(self.policy.reserve_usd),
                'allowance_scope': 'server_process',
                'campaign_reserved_usd': str(self.spent), 'campaign_limit_usd': str(self.policy.budget),
                'rate_bounds_usd_per_million': [str(self.policy.input_rate), str(self.policy.output_rate)],
                'input_count_method': 'serialized_bytes_plus_1024_per_request_conservative_allowance',
                'not_a_provider_invoice': True, 'requests': lease['request_receipts'], 'stop': lease['stop']}


_authority = None
_singleton_lock = threading.RLock()


def restricted_profile():
    return os.getenv('LEAKPROBE_DEPLOYMENT_PROFILE') == 'restricted_live'


def server_settings():
    """Only the explicit restricted entrypoint reads Cloud Secrets. Never load .env."""
    if not restricted_profile():
        raise LiveDenied(UNAVAILABLE)
    names = ('LEAKPROBE_LIVE_MODE', 'LEAKPROBE_OPERATOR_PASSWORD_HASH',
             'NEBIUS_API_KEY', 'NEBIUS_MODEL', 'NEBIUS_BASE_URL',
             'LEAKPROBE_INPUT_USD_PER_MILLION', 'LEAKPROBE_OUTPUT_USD_PER_MILLION', 'LEAKPROBE_LIVE_BUDGET_USD',
             'LEAKPROBE_LIVE_MAX_INVESTIGATIONS')
    import streamlit as st
    try:
        cloud = {name: str(st.secrets[name]) for name in names if name in st.secrets}
    except Exception:
        cloud = {}
    return cloud  # Credentials/configuration never fall back to .env or process environment.


def authority():
    global _authority
    policy = Policy.from_settings(server_settings())
    with _singleton_lock:
        if _authority is None:
            _authority = Authority(policy, enabled=lambda: current_policy_matches(policy))
        elif _authority.policy != policy:
            raise LiveDenied('Live configuration changed. Restart the app to apply the new server limits.')
        return _authority


def current_policy_matches(policy):
    try:
        return (os.getenv('LEAKPROBE_INSPECTION_MODE', '').strip().lower() not in ('1', 'true', 'yes')
                and Policy.from_settings(server_settings()) == policy)
    except LiveDenied:
        return False
