# Streamlit front end

**Status:** the employee monitoring dashboard and supporting review pages are implemented locally. Community Cloud deployment still requires a signed-in account with repository access.

## Run locally

Use Python 3.12 from the repository root:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
streamlit run streamlit_app.py
```

The app starts without an API key and makes no external model call.

## Employee workflow

1. Open **Monitoring**. The dashboard automatically loads the configured monitoring window; the employee does not choose a case or individual sensors.
2. Read the network status and candidate pipe. A leak alert recommends that the employee follow the usual field verification process.
3. Compare network-wide median pressure and flow with the normal-operation reference. The topology map highlights the leading pipe candidate, and the evidence section lists channels outside the normal reference range.
4. Use the scenario-fit details when more context is needed. Fit errors rank candidate patterns; they are not probabilities or field confirmation. The dashboard does not create work orders or dispatch crews.
5. Use **AI Investigation** to read a matching saved explanation or explicitly request a bounded Nemotron investigation. No inference occurs on page load. A missing API key leaves the dashboard functional offline.
6. Acknowledge the alert and record review status, reviewer notes and field assessment. **History & outcomes** contains these employee-entered records. Synthetic reference labels and replay controls are under **Evaluation / Admin**.

The configured monitor window is `case_405` from the canonical 500-case dataset. Its full-channel feed is labeled with a leak on pipe 202, and the scenario comparison ranks pipe 202 first. The map highlights pipe 202 from the comparison result. It provides a repeatable example for the employee workflow; a production deployment would replace that local input with a live or regularly delivered sensor feed.

## Pages

- **Monitoring:** automatic full-channel comparison, normal-reference charts, network topology, alert evidence, and feed details.
- **History & outcomes:** persistent employee-entered reviews and timestamped event history, separate from synthetic labels.
- **Evaluation / Admin:** replay controls and synthetic reference labels. This grouping does not implement authentication or authorization.
- **Run history & traces:** browse all saved full-channel LLM runs, compare their lead fit and metadata, and open an individual explanation. This page reads trace files and does not call the provider. Bundled traces include stable run timestamps; future runs saved on Community Cloud need persistent storage or a repository update to survive redeploys.
- **Model performance:** saved baseline, class-weighted, and SMOTE benchmark results.
- **About:** channel coverage, data provenance, and result limitations.

## Data and scoring

The canonical source is `data/net3_full_high_signal/`. Every observation file must have 92 pressure columns, 117 flow columns, and the timestamp column. A missing value within one of those channels is allowed; a missing channel or smaller sensor set is rejected when loaded.

The Monitoring page calls `Net3Investigation.compare_hypotheses()` automatically and displays the returned ranking. It compares the configured window with the normal-reference bank and calculates per-channel departures from its 5th–95th percentile range. Fit scores are error measures, not probabilities. The classifier table reads the saved report from `data/net3_full_high_signal_benchmark/report.json`; it does not retrain on app page reruns.

## App structure

```text
streamlit_app.py                 Streamlit entry point and navigation
leakprobe/ui/data_access.py      Cached feed, network, outcome, report, and saved-run loading
leakprobe/ui/monitoring.py       Employee monitoring dashboard and baseline evidence
leakprobe/ui/outcomes.py         After-action outcome review
leakprobe/ui/pages.py            Saved-run history, benchmark, and About pages
leakprobe/net3_tools.py          Full-channel scenario comparison
leakprobe/coverage.py             92/117 channel validation
```

Streamlit's `st.Page` and `st.navigation` provide the multipage navigation. Feed, map, and report data are cached as read-only values.

## Hosting

The intended host is Streamlit Community Cloud. The target repository branch is now `main`, entry point `streamlit_app.py`, and Python 3.12. Community Cloud installs dependencies from the root `requirements.txt`. Deployment has not been performed. Use persistent storage for employee records. See [deployment guidance](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy) and [dependency setup](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/app-dependencies).

The CLI and the explicit dashboard **Run AI Investigation** button reuse the optional Nebius adapter. The dashboard never runs inference automatically; it requires a user click and enforces request/tool/attempt budgets. Keep provider credentials in host secrets or `.env`, never in the repository. See [the current employee guide](EMPLOYEE_DASHBOARD.md) for states, persistence and offline verification.

## Current limits

The app does not connect to utility telemetry, GIS, work orders, controls, crew dispatch, or excavation workflows. The high-signal cases are generated benchmark data. They are intentionally easier than routine operating conditions and cannot establish field precision or recall.

The configured feed is a repeatable local sample. No live utility telemetry, GIS, work orders, controls, crew dispatch, or excavation workflow is connected. Replace the local feed source and validate the alert logic with the utility's operating data before using this workflow operationally.
