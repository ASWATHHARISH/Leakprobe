# Employee dashboard and AI investigation

Updated 29 October 2026. Implementation is in the existing `github-main` checkout;
the parent workspace's historical Part C campaign is untouched.

## Launch on Windows

From PowerShell:

```powershell
cd D:\LeakProbe-1\github-main
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run streamlit_app.py
```

If using the already installed Python environment instead:

```powershell
cd D:\LeakProbe-1\github-main
python -m streamlit run streamlit_app.py
```

No key is needed. Monitoring now lists all 500 automatically assessed records, with
filters for attention, no-alert, review-required and unavailable records. Open a record
to update its evidence, map, AI report and review form. The initial selection is
`case_405`, which has a bundled completed explanation; it is not an accuracy estimate.
Employees do not configure sensor channels or supply detector inputs. All assessments
come from the existing physics comparison. Administration contains window replay,
reference outcomes and model validation. See [the queue guide](MONITORING_QUEUE.md).

## Employee workflow

1. Read the simulated-feed banner, latest timestamp, data coverage and freshness warning.
   These archived January 2026 readings must not be interpreted as current network health.
2. Review the suspected-leak/normal/uncertain outcome, leading candidate and evidence.
   The schematic supports pan/zoom and hover. Red identifies a candidate, not a confirmed leak.
3. Compare observed measurements with time-aligned normal profiles. Network medians
   summarize the full feed; the table includes actual readings and normal ranges for
   automatically chosen affected sensors. Missing readings remain missing.
4. Read the saved AI summary/full report or explicitly request a new investigation.
   Compare its assertions with the numerical evidence. Existing legacy reports are
   shown unchanged and identify missing model provenance and known contradictions.
5. Enter a reviewer and acknowledge / mark under review / record leak confirmed,
   no leak, or further investigation required, with notes. These are employee-entered
   assessments, not changes to synthetic labels or detector results.
6. Review UTC event history on Monitoring or History & outcomes.

## Optional Nemotron configuration

Install the existing optional requirements:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-llm.txt
```

Configure `NEBIUS_API_KEY` through host environment variables or the existing
ignored `.env` mechanism. `NEBIUS_MODEL` and `NEBIUS_BASE_URL` retain their existing
defaults. No secret was created, inspected, changed or included in a report during
this implementation. Do not commit credentials. This implementation made no paid requests.

The button makes a provider request only when explicitly clicked with a configured
adapter. Each attempt permits at most four requests, eight executed tool calls and
2,048 output tokens per request. There are at most two attempts per alert identity,
including failures, with no provider retries. A transactional reservation prevents
concurrent tabs from launching duplicate work. These are request limits, not a
guaranteed currency limit; input tokens include the full sensor window.

New responses are requested with six sections: summary, anomalous sensor evidence,
leading-pipe rationale, alternatives, uncertainty/limitations, and verification actions.
The adapter uses the existing allowlisted observation, network, operations and
comparison tools. No tool reads truth labels, alters controls or dispatches a crew.

States are unavailable, running (spinner), completed, incomplete/budget exhausted,
failed, and storage failed. Completion requires successful observation and comparison
tool evidence and all six nonempty employee-report sections, not just an answer string.
Partial answers are labeled incomplete. Legacy reports are clearly exempt from this new
format check and shown as legacy responses with their missing provenance disclosed.
Saved reports are matched by alert identity; legacy reports must match timestamps,
channel sets, missing values, readings and ranking within tiny serialization tolerances.
Legacy files do not record model identity; the UI does not invent one.

## Persistence and failure recovery

Employee events and AI request receipts are appended to
`outputs/operations/alerts.sqlite3`. New traces are uniquely named in
`outputs/traces/`, published atomically without replacing existing files. Both paths
are ignored by Git. Retain them on persistent disk or back them up before redeploying.
SQLite connections close explicitly, including on Windows.

An interrupted AI attempt remains pending and blocks more paid requests for that alert.
Do not automatically retry: the provider may already have processed a billable request.
A maintainer must reconcile the receipt and provider state before authorizing further work.
There is no automatic deployment, authentication, work-order connection, crew dispatch,
or field confirmation integration. Reviewer names are self-entered and not authenticated.

## Verification

```powershell
cd D:\LeakProbe-1\github-main
python -m unittest discover -s tests -v
python scripts/product_integrity.py verify outputs/product_verification/employee_dashboard_before.json
```

Use `.\.venv\Scripts\python.exe` in place of `python` for a fresh virtual environment.
The tests exercise mocked API success/failure/budgets and Streamlit rendering without
paid requests. The integrity manifest preserves all 1,535 pre-existing protected input,
detector, benchmark and output files. The verification command never regenerates data.

The expected sensor grid is the bundled simulator's January 1 UTC origin, 15-minute
steps and 25 samples over six hours. Misaligned/duplicate/out-of-order timestamps,
missing channels, infinite readings or invalid normal profiles block the monitoring
assessment. Null readings are permitted and explicitly counted; channels without
readings in the last two samples are flagged. No interpolation changes detector inputs.
These checks are a demo feed contract, not a general utility telemetry ingestion layer.

The canonical 500-case high-signal dataset and separate 1,000-case experiment are
unchanged. The harder historical Part C results remain a distinct negative experiment;
none of these high-signal results establishes equivalent conditions or field accuracy.
