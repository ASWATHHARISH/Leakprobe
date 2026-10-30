# Monitoring workspace redesign

Only Monitoring presentation and its UI tests changed. Existing uncommitted work
was retained. No dependencies, detector settings, provider calls, saved traces,
administrative pages or storage schemas were changed.

The overview retains the four queue KPIs. Employees can filter by assessment or
attention status and search record IDs, pipe IDs and review statuses. All matching
records are available in the record selector; a collapsed table browses ten per
page. Paging does not change the open record. Independent windows are explicitly
identified as separate records rather than simultaneous incidents.

The selected record has a compact assessment, candidate, coverage and review
header. Overview is the first tab, followed by AI Investigation, Sensor Analysis
and Employee Review. Native tabs switch client-side; rendering every tab also
performs no inference. Record selection is retained across rerenders and paging.

The network uses the existing actual topology, with a stronger orange candidate
highlight and the existing single pan/zoom binding. Sensor tables retain signs,
units and missing values. Their reference quantiles use the same aligned final
sample as before. The existing network summary charts explicitly distinguish
pressure from absolute flow magnitude. Detailed observations and technical feed
diagnostics remain expandable.

AI completion/evidence checks and same-record saved-report matching are unchanged.
Existing validated reports appear without another request. Request receipts,
token/cost information, provider configuration and technical traces are collapsed.
The explicit Run AI Investigation action remains the only inference entry point.

Acknowledgment is available in the header and remains separate from field
confirmation. Both actions use the existing persistent review store. Confirmation
appears only after the store succeeds; callbacks refresh the displayed status and
timestamped history. Failed persistence reports failure without claiming success.

## Verification

- Full suite: **81 tests, 79 passed, 2 failed, no errors or skips**. All ten new
  workspace tests and the new chart-runtime test passed. The latter renders the
  candidate and normal maps using Vega-Lite 5.8 and 5.20.
- Real-cache UI check: **500 unique selectable records**, unchanged counts of
  **417 suspected leaks / 83 no alert / 0 review required**. These are assessments,
  not verified outcomes. Opening the last record and filtering the 83 no-alert
  records passed. Scoring was disabled with a failing mock; no rescoring occurred.
- Saved validated investigations, incomplete case_005 reports, offline operation,
  record selection, pagination, acknowledgment, field confirmation and failed-save
  behavior passed. All test reviews used disposable stores. No paid calls occurred.
- **1,536 original protected file hashes** passed verification. A further **15
  hashes** confirmed the unchanged backend, other pages, entry point and real
  queue cache. See `outputs/product_verification/monitoring_ux_before.json`.
- Machine-readable receipts:
  `outputs/product_verification/monitoring_ux_test_results.json` and
  `outputs/product_verification/monitoring_ux_real_queue.json`.

Two existing checks remain failing with the current saved history:

1. `test_real_bundled_trace_matches_current_feed_and_ranking`: the test changes a
   comparison signature while retaining the same modern alert ID. The unchanged
   matching function accepts the modern ID match, whereas this legacy-oriented
   test expects no result. Modern traces now exist for that record.
2. `test_existing_admin_pages_still_render`, Investigation history: the unchanged
   `pages.py:220` expects a legacy ranking row containing `scenario`. A compact
   trace uses a different row shape and raises `KeyError: 'scenario'`.

These involve untouched code outside this Monitoring-only redesign. They have not
been suppressed, and saved traces have not been rewritten to make them pass.
Browser-level visual QA at different viewport sizes remains outstanding; automated
checks use Streamlit AppTest and the JavaScript chart renderer.

## Launch and focused verification

From `D:\LeakProbe-1\github-main`:

```powershell
python -m streamlit run streamlit_app.py
python -m unittest discover -s tests -p test_monitoring_workspace.py
python scripts/product_integrity.py verify outputs/product_verification/nemotron_case005_before.json
```

The full suite is `python -m unittest discover -s tests`. Chart-runtime tests use
the existing optional `requirements-test.txt`; the verification run loaded the
already-installed renderer from the disposable test environment.
