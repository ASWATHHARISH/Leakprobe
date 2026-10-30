# LeakProbe — offline Streamlit demonstration

This independent private repository preserves the verified LeakProbe application:
the employee UI, physics detector, canonical 500 Net3 monitoring windows, original
reference patterns, frozen monitoring cache, saved benchmark summaries and five
unedited Nemotron investigation traces. The feed uses Net3 simulation data; it is
not a live utility connection or proof of field performance.

## Publication status

- Owner: **ASWATHHARISH** (personal account).
- Repository: **leakprobe-streamlit-demo**.
- Visibility: **Private**. Private repository creation/upload is authorized.
- Public code publication, licensing and hosting deployment are **not approved**.
- No license is selected. Do not change visibility or deploy without approval.
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
restricted entrypoint is included; see [protected live inference](docs/PROTECTED_LIVE_INFERENCE.md).
Activation, Cloud Secrets changes and deployment require separate approval. The
initial live configuration permits one investigation, reserves at most $0.25 for
that attempt and caps the activation budget at $1.00. Nothing activates on push.
All five saved investigations remain unchanged, including validated LP-0405 and
separate invalid/incomplete attempts. Historical model reports do not represent
new inference. The 500 cached records retain 417 predicted leaks, 83 predicted
normals and zero uncertain; these counts are not accuracy or field confirmation.

Employee reviews are temporary and scoped to a browser session. Same-session
navigation/reruns preserve events; a new session, restart or hosting lifecycle
may lose them. No permanent multi-user review history is claimed.

## Future Community Cloud deployment — separate approval required

Do not deploy or make this repository public as part of private publication.
If team publication rights/licensing and hosting are subsequently approved, use:

| Setting | Value |
|---|---|
| Repository | `ASWATHHARISH/leakprobe-streamlit-demo` |
| Branch | `main` |
| Main file | `deploy/app.py` |
| Python | **3.12**, selected in Community Cloud Advanced settings |
| Requirements | Existing `deploy/requirements.txt` next to entrypoint |
| Theme | Existing root `.streamlit/config.toml` |
| Secrets | Leave empty; no Nebius credentials |

`.python-version` is a local-tooling hint; explicitly select Python 3.12 in Cloud.
Private-repository access and app sharing must be reviewed separately. No public
URL is reserved or promised. No Render service or custom Cloud start command is
needed. Official instructions: [deployment](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy),
[file organization](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/file-organization).

Previous offline checks passed 110 automated tests and 12 package checks, including
all 500 records, four Monitoring tabs, all five saved reports, navigation/filtering
and session review isolation. Actual hosted Linux operation, public access,
concurrency and browser layouts remain untested. The unchanged About technical
documentation link points to the original project and may require team access;
it is not used for application startup or data loading.
