# LeakProbe — Streamlit monitoring and live investigation

This independent private repository preserves the verified LeakProbe application:
the employee UI, physics detector, canonical 500 Net3 monitoring windows, original
reference patterns, frozen monitoring cache, saved benchmark summaries and five
unedited Nemotron investigation traces. The feed uses Net3 simulation data; it is
not a live utility connection or proof of field performance.

## Publication status

- Owner: **ASWATHHARISH** (personal account).
- Repository: **leakprobe-streamlit-demo**.
- Visibility: **Private**. Private repository creation/upload is authorized.
- Existing live app: https://leakprobe-nemotron-live.streamlit.app/.
- No license is selected. Visibility changes, new publication and redeployment
  of prepared changes require approval.
- The team repository and its Git history are not part of this repository.

No API credentials, real `.env`, secrets configuration, review databases, virtual
environments, generated review outputs, raw research campaigns or training/model
artifacts are included. `.env.example` is credential-free. Saved benchmark reports
and five investigation traces are deliberately retained to support offline use.
Detections and saved reports have not been modified to improve reported results.

## Verify and run locally

Use Python **3.12** from this repository root:

```powershell
python deploy/verify_release.py
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r deploy/requirements.txt
.\.venv\Scripts\python.exe -m streamlit run deploy/app.py --server.address 127.0.0.1 --server.port 8503
```

On Linux use `python3.12` and `.venv/bin/python` with the same requirements and
entrypoint. Keep `.gitattributes`: original cache/source bytes must survive Git
checkout across operating systems. The checker verifies file hashes, portable
source bindings, 500 case identities, saved-report inventory and private-file
patterns without generating data, scoring cases or calling providers.

## Offline behavior and saved reports

`deploy/app.py` defaults to `LEAKPROBE_DEMO_MODE=1` and
`LEAKPROBE_ENABLE_LIVE_AI=0`. Public-demo mode blocks inference even if a live flag
is supplied. The offline entrypoint does not accept paid inference. A separate
live entrypoint powers the existing hosted application; see
[live setup](docs/PROTECTED_LIVE_INFERENCE.md). Monitoring remains available to
viewers; operator login enables explicit live requests when Cloud Secrets are valid.
No administrator challenge, signature or permit is needed. Default limits are one
investigation and a $0.25 application allowance, shared across browsers per server
process. Restarts reset this allowance; it is not a provider-side spending cap.
Page loading and navigation never initiate inference. No paid call was made to
verify these changes. Push/redeployment still require approval.
All five saved investigations remain unchanged, including validated LP-0405 and
separate invalid/incomplete attempts. Historical model reports do not represent
new inference. The 500 cached records retain 417 predicted leaks, 83 predicted
normals and zero uncertain; these counts are not accuracy or field confirmation.

Employee reviews are temporary and scoped to a browser session. Same-session
navigation/reruns preserve events; a new session, restart or hosting lifecycle
may lose them. No permanent multi-user review history is claimed.

## Existing Community Cloud application

Update only the existing live app after approval; no third app is needed:

| Setting | Value |
|---|---|
| Repository | `ASWATHHARISH/leakprobe-streamlit-demo` |
| Branch | `main` |
| Main file | `deploy/live/app.py` |
| Python | **3.12**, selected in Community Cloud Advanced settings |
| Requirements | Existing `deploy/live/requirements.txt` next to entrypoint |
| Theme | Existing root `.streamlit/config.toml` |
| Secrets | Five fields in [live setup](docs/PROTECTED_LIVE_INFERENCE.md), entered manually |

`.python-version` is a local-tooling hint; explicitly select Python 3.12 in Cloud.
Keep existing repository visibility and app sharing unchanged. No Render service
or custom Cloud start command is needed. Official instructions:
[deployment](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy),
[file organization](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/file-organization).

Previous offline checks passed 110 automated tests and 12 package checks, including
all 500 records, four Monitoring tabs, all five saved reports, navigation/filtering
and session review isolation. Actual hosted Linux operation, public access,
concurrency and browser layouts remain untested. The unchanged About technical
documentation link points to the original project and may require team access;
it is not used for application startup or data loading.
