Deploy the restored dashboard to the existing PRIVATE Streamlit application.

1. After publication is approved, publish this recovery `app/` tree to
   `ASWATHHARISH/leakprobe-streamlit-demo`, without importing the source clone's
   Git history or any operational database. Do not publish `baseline/`, local
   verification logs, environments or recovery receipts.
2. In the existing private app settings keep branch `main`, entry point `deploy/live/app.py`
   and Python **3.12**. Runtime dependencies are `deploy/requirements.txt`.
   Keep private viewer access enabled and invite only authorized viewers.
3. Enter the three settings in `deploy/secrets.example.toml` in Cloud Secrets,
   substituting the API key privately. There is no operator password, activation
   permit, application mode, signing key or process-wide spending/attempt cap.
4. Open Monitoring, select LP-0405, then AI Investigation. A configured host
   enables Run AI Investigation; only pressing it starts a provider request.
   Do not test the real provider until spending is explicitly approved.

Local launch (from this app folder):

```powershell
python -m pip install -r deploy/requirements.txt
python -m streamlit run deploy/live/app.py
```

Without a local Secrets file the dashboard and saved investigations work, while
the AI button is unavailable. For an authorized local live test, configure the
same keys privately in `.streamlit/secrets.toml` (ignored by Git).
`deploy/app.py` also remains available for the existing credential-free demo.

The original per-alert ledger permits two attempts and prevents overlapping
requests for the same alert. The original model loop retains four requests,
eight tool calls, bounded context/output, a 30-second request timeout and zero
SDK retries. These are not a guaranteed monetary cap. There is no new global
limiter. Python does not verify Cloud sharing settings or a viewer's identity:
private viewer access is enforced by Streamlit and must remain enabled.

All original data, benchmark evidence, prompts, tools and five saved traces are
retained. Two existing report-display defects are repaired: modern compact
rankings render in History, and older validated reports remain discoverable
after failed attempts. Saved trace contents and factual validators are unchanged.
Additional platform cache files contain identical, independently rechecked
500-record assessments; no hydraulic data was regenerated.

Cloud's local filesystem is ephemeral. New reviews and investigations can be
lost on restart/redeployment; the five bundled saved reports remain in Git.
No external persistence service has been added for this demo.
