# Live Nemotron in the existing Streamlit application

Use the existing `leakprobe-nemotron-live.streamlit.app`, repository
`ASWATHHARISH/leakprobe-streamlit-demo`, branch `main`, entrypoint
`deploy/live/app.py`, and Python **3.12**. Its adjacent requirements add only
`openai==2.54.0`. No additional application is needed. Push/redeployment still
require owner approval.

## Essential setup

1. Run locally: `python deploy/live_admin.py hash-password`. Enter a private code
   of at least 16 characters at the masked prompt. Keep the code private; use only
   its generated verifier in Cloud Secrets.
2. Enter these root-level TOML fields in the existing app's **Settings > Secrets**:

   ```toml
   NEBIUS_API_KEY = "<existing key, entered only in Cloud Secrets>"
   LEAKPROBE_OPERATOR_PASSWORD_HASH = "<generated verifier>"
   LEAKPROBE_LIVE_MODE = "restricted"
   LEAKPROBE_LIVE_BUDGET_USD = "0.25"
   LEAKPROBE_LIVE_MAX_INVESTIGATIONS = "1"
   ```

   Never commit populated Secrets or paste credentials into chat. No signing key,
   challenge, deadline or permit is needed. Remove obsolete
   `LEAKPROBE_LIVE_ADMIN_KEY` and `LEAKPROBE_LIVE_UNTIL_UTC`; they are ignored.
   Existing matching `NEBIUS_MODEL` and `NEBIUS_BASE_URL` fields may stay. Defaults:
   `nvidia/nemotron-3-super-120b-a12b` and
   `https://api.tokenfactory.us-central1.nebius.com/v1/`.
3. After approved publication, reboot the existing app. Open LP-0405, then
   **AI Investigation > Operator login**. Sign in with the original access code.
   **Run AI Investigation** becomes available immediately with valid configuration
   and available allowance. Click only when authorized to use Nebius credits.
   Page loading, login and navigation never initiate inference.

## Safeguards and limitations

- Monitoring and five original saved reports remain viewable without login.
  The shared code is restricted access, not named employee identity or SSO.
- Salted PBKDF2-SHA256 verifier; browser-bound server sessions expire after
  15 minutes. Six failed logins in ten minutes temporarily lock login globally.
  Credentials/configuration come only from Streamlit Secrets, never `.env` or
  environment fallbacks. Inspection mode and disabled live mode still block AI.
- Defaults: **one investigation**, **$0.25 application allowance**, one concurrent
  investigation across browsers. Each attempt reserves **$0.23296**, including
  failures, using conservative rate bounds of $2 input / $4 output per million
  tokens. These bounds are assumptions, not quoted invoice pricing. Reservations
  are separate from actual reported tokens and provider cost information.
- Limits are **per server process**: logout, reruns and other browser sessions do
  not replenish them; restarts, hibernation or container replacement do. This is
  **not a durable lifetime budget or guaranteed provider-side spending cap**.
  Use provider-side billing controls where available. There is no automatic renewal
  action. The owner must account for hosting restarts when authorizing usage.
- Optional budget is bounded at $1 and attempt count at four. Each attempt reserves
  at most $0.25. Optional upper-rate fields are `LEAKPROBE_INPUT_USD_PER_MILLION`
  and `LEAKPROBE_OUTPUT_USD_PER_MILLION` (defaults 2 and 4). Configuration changes
  fail closed until restart. Logout does not reset usage.
- Existing limits remain: four provider requests, eight tool calls, 2,048 output
  tokens per request, 24,000 request bytes / 72,000 total, 131,072 token allowance,
  90-second deadline, at most 20-second request timeouts, zero SDK retries.
  Two starts per minute globally, two per browser/hour and two per alert across
  browsers. A deadline cannot cancel provider work already accepted.
- Agent, prompts, tools, full-channel detector and cited-fact validation are unchanged.
  Invalid/failed attempts never replace an older validated report. New and saved
  investigations are labeled separately; request/token/cost receipts remain in
  collapsed technical details. Missing usage stops further calls; malformed or
  over-limit usage locks live execution.
- New reports/reviews use ephemeral hosting storage, not durable shared records.
  Original bundled reports and all 500 cached monitoring records remain unchanged.

## Offline verification

`python deploy/verify_release.py` verifies release hashes, frozen cache/source
bindings, 500 records and five saved traces. `python -m unittest discover -s tests`
uses mocked providers and temporary review storage, without spending credits.
`deploy/app.py` remains an offline-compatible entrypoint that always blocks AI.
