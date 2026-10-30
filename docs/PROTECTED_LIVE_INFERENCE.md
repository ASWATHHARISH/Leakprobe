# Protected live Nemotron investigations

Publishing this implementation does not deploy, activate or call the provider.
Cloud Secrets, hosting creation and paid requests require separate authorization.

## Two entrypoints

| Mode | Main file | Requirements | Inference |
|---|---|---|---|
| Offline demo | `deploy/app.py` | `deploy/requirements.txt` | Always blocked by the offline profile |
| Restricted live | `deploy/live/app.py` | `deploy/live/requirements.txt` | Authorized operator button only |

The live requirements add only `openai==2.54.0` to the existing runtime. No dotenv,
SSO SDK, training package or external database is needed. Configuration/navigation
never constructs a provider client. Both modes retain the same frozen 500-record
cache, detector, 209 channels, references, rankings and saved investigations.
The inspection guard still takes precedence. API keys and legacy live flags alone
cannot authorize hosted inference.

The existing compact tool loop, prompt, targeted evidence retrieval, report schema
and cited-fact validator are reused unchanged. The service reconstructs tool facts
and validates again before displaying a completed report.

## Operator access and administrator authorization

This MVP uses a shared operator access code, **not named employee identity or SSO**.
The server stores a salted PBKDF2-SHA256 verifier (310,000 iterations). Successful
sign-in yields an opaque, server-side capability bound to that browser session for
15 minutes. Six failed logins across all sessions within ten minutes lock access
temporarily. Logout/expiry invalidate the capability. Do not share the code publicly.

Sign-in alone cannot spend. A separate administrator must sign the server's
challenge using an independent HMAC-SHA256 key. The permit binds a random boot ID,
immutable policy fingerprint, limits and expiry. A process accepts one activation
only, lasting at most 15 minutes and never beyond its configured UTC deadline.
An old permit cannot rearm a restarted process or another replica. Budget exhaustion
does not renew credit. Configuration changes require restart and a fresh signed
authorization. Clearing Streamlit caches does not reset the module authority.

This avoids an automatically resetting spend ledger on ephemeral hosting. It is a
**per-activation** policy, not a cross-deployment lifetime billing ledger. A new
signed activation explicitly authorizes a new budget. Keep the signing key with
the administrator and server; operators must never receive it.

The service rechecks authorization before client construction and each request,
including with injected test clients. Signed-in operators can read new live traces;
other viewers retain access to original saved reports and offline monitoring.
Restrict the whole live app to approved viewers in Cloud sharing settings as an
additional measure where account permissions allow.

## Server-enforced limits

| Control | Limit |
|---|---|
| Reserved USD per activation | Positive configured amount, **at most $1.00** |
| Reserved USD per attempt | Calculated maximum, **at most $0.25** |
| Attempts per activation | **1 by default and for the initial test**, including failures; explicitly configurable up to 4 |
| Attempts per alert | 2 across all browser sessions |
| Attempts per browser | 2/hour |
| Global start rate | 2/minute |
| Concurrent investigations | 1/process |
| Model requests / tool calls | 4 / 8 per attempt |
| Output tokens | 2,048/request |
| Request JSON | 24,000 bytes/request; 72,000 total |
| Conservative token allowance | 131,072/attempt |
| Existing observed-token stop | 32,000 reported tokens before another round |
| SDK retries | Zero |
| Network timeout | At most 20 seconds per HTTP phase/request option |
| Investigation deadline | 90 seconds, checked before/after calls |

An in-flight synchronous call holds its concurrency slot until return/timeout;
it is not detached into a background thread. A deadline prevents later requests
but cannot cancel work already accepted by the provider. The existing one report
correction opportunity is included in the four-request limit, not an HTTP retry.

### Spending accounting

The administrator configures reviewed **upper rates**, in USD per million tokens,
for the fixed model. No current price is assumed or downloaded. Every attempt
reserves its full conservative maximum before constructing the client:

```
reservation = [4 × (24,000 + 1,024) × input_rate + 4 × 2,048 × output_rate] / 1,000,000
```

Serialized bytes plus overhead are a conservative token allowance, **not a tokenizer
or invoice**. Requests are checked against this allowance. All failures and unknown
usage retain the full reservation; no automatic refund reopens spending. Illustrative
upper rates of $2 input/$4 output reserve $0.23296 for the initial single attempt.
These are not claims about current Nemotron pricing.

Actual reported tokens and provider cost/currency fields are stored separately.
Missing usage stops further calls in the attempt. Malformed or excessive reported
usage locks further live calls in the process. Client method invocations are counted
separately from loop rounds blocked before sending; failed network attempts do not
establish that the provider accepted or billed a request.

The reservation is **not a guaranteed provider invoice ceiling** if prices,
tokenizer/protocol overhead or provider behavior differ. Use a dedicated key/account,
review available credits, promo expiry and billing controls before this demo.
Nebius documents automatic card charging under its billing terms; this code does
not configure or verify a provider-side hard quota or disable those charges.
See [Nebius billing](https://docs.tokenfactory.nebius.com/other-capabilities/billing-new).
Do not activate without approving the rate bounds and accounting assumptions.

## Activation — separate approval required

Nebius's model page checked on 2026-10-30 lists the existing
`nvidia/nemotron-3-super-120b-a12b` on a public endpoint at **$0.30 input / $0.90
output per million tokens**. The integration uses
`https://api.tokenfactory.us-central1.nebius.com/v1/`, also shown in Nebius's
[Nemotron example](https://nebius.com/services/token-factory/nemotron).
See [official model availability and pricing](https://nebius.com/services/token-factory/models/nvidia-nemotron-models-inference).
Account entitlement, remaining Token Factory credits and actual billing are not
verified by an offline test. Confirm the $50 balance in **Token Factory**, not a
separate infrastructure-credit balance, before authorizing the request. The $2/$4
rate bounds above intentionally exceed the listed prices; enter those bounds for
the first activation to reserve $0.23296, independently of actual usage/cost.

Community Cloud permits only **one private app per workspace**. With separate
apps from this private repository, deploy the offline app first and, only after
approval, make that **app** public in its Sharing settings; the repository stays
private. Then deploy the live app as the workspace's private app. Do not change
repository visibility. If an existing private app occupies the slot, resolve that
manually before creating another app; do not delete it automatically.
See [Streamlit sharing limits](https://docs.streamlit.io/deploy/streamlit-community-cloud/share-your-app).

1. Review/approve code before pushing. Keep the repository private; licensing and
   public publication rights remain separate decisions.
2. Generate a long operator code locally and run `python deploy/live_admin.py hash-password`.
   Enter the code at the masked prompt; use only its verifier in Secrets. Independently
   generate a random 32-byte hex administrator key, for example locally with
   `python -c "import secrets; print(secrets.token_hex(32))"`. Treat this output as a secret.
   Never reuse the API key or access
   code as this signing key, and do not paste any key into chat or Git.
3. After approval, configure the restricted Cloud app with branch `main`, main file
   `deploy/live/app.py`, and Python **3.12** in Advanced settings. Adjacent requirements
   install the additional SDK. Leave the original offline app at `deploy/app.py`.
4. Populate Cloud Secrets manually from the credential-free
   `deploy/live/secrets.example.toml`: set `LEAKPROBE_LIVE_MODE="restricted"`, operator
   verifier, signing key, Nebius key, reviewed upper rates, budget and an explicit UTC
   expiry within the next 24 hours. For the first LP-0405 test keep the budget at
   $1.00 and `LEAKPROBE_LIVE_MAX_INVESTIGATIONS="1"`; do not authorize a second attempt
   or automatically renew. Leave legacy demo/live flags alone. Server-side
   environment variables with the same names take precedence. No `.env` is loaded.
5. Sign in under **Restricted live access**, download the process challenge, then
   run locally as administrator:

   ```powershell
   python deploy/live_admin.py sign --challenge PATH_TO_CHALLENGE
   ```

   Review the printed policy, type `AUTHORIZE` and supply the signing key at the
   masked prompt. The command makes no API call. Paste the printed JSON into **Signed
   activation permit** and apply. Do not commit the permit.
6. Only **Run AI Investigation** sends provider requests. Navigation, sign-in,
   activation and loading reports never invoke inference. The UI distinguishes
   freshly generated reports, saved live reports, original reports and invalid attempts.
7. Sign out when finished. Disabling mode or expiration blocks requests; restarting
   requires a fresh administrator authorization, never a replay of the old permit.

See [Cloud Secrets](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management)
and [deployment settings](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy).
Never commit populated `.streamlit/secrets.toml`. No Secrets were opened or changed here.

## Results, persistence and offline verification

New attempts have `origin="live_nebius"`, a run ID, UTC timestamp, provider attempt
receipts, usage/cost data and separate reservation accounting. Unique traces are
atomically saved under `outputs/restricted_live/traces/`, ignored by Git. Bundled
reports under `demo_assets/traces/` remain read-only. A newer invalid attempt cannot
hide the last validated report. A storage failure is not displayed as saved success.

Cloud traces/reviews are ephemeral; this is not durable enterprise audit storage or
named-user authentication. Hosted Linux performance and actual paid-provider access
remain untested until separately approved. No inference was made for verification.

```powershell
python -m pip install -r deploy/requirements-live.txt
python -m unittest discover -s tests -v
python deploy/verify_release.py
```

Tests use actual Net3 evidence with fake responses and the real SDK over
`httpx.MockTransport`; socket connections are blocked. They cover access/permits,
restart/replay, budgets/concurrency, timeouts, redaction, case_005 flow direction,
report validation, persistence and navigation without inference. No real key is needed.
