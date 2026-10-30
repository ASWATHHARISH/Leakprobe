# Employee product audit and completion

29 October 2026. Source checkout: `github-main`, baseline commit `1c56fc7`.

## Findings before implementation

| Area | Existing implementation | Finding |
|---|---|---|
| Detector | Full-channel reference matching, split-specific candidate catalog, optional leak-only rejection | Working; retained unchanged. Fit is an error, not probability; normal winners cannot be rejected by the existing policy. |
| Data | Canonical 500-case high-signal feed, separate 1,000-case sample-size experiment | Working; all input files/reference banks/metrics retained. The larger set reuses pipe assignments and is not independent pipe coverage. |
| Monitoring | Baseline charts, affected-channel counts, topology map and candidate | Mostly complete. Employee page exposed a case selector despite plan/README claiming otherwise; freshness and reference-time validation were missing. |
| Alert lifecycle | Synthetic held-out label table called verified outcomes | Missing employee acknowledgment, reviewer notes, status history and persistence. Synthetic labels could be mistaken for field confirmation. |
| Nemotron | Bounded allowlisted agent, CLI and two saved traces, history browser | Working offline trace display; no per-alert request action or employee report state in Monitoring. Legacy traces omit model identity. |
| Messaging | Workbench / Water Leak Detection System naming | Needed AI investigation positioning and prominent simulated-feed disclosure; pitch asserted analyst-effort improvement without evidence. |
| Tests | Detector/scoring/agent tests | One pre-existing import failure: wrapper did not export `observation_columns`. No employee workflow tests. |
| Plan versus code | `tasks/plan.md`, `tasks/todo.md` mark automatic employee monitoring complete | Current case selector contradicted that item; after-action synthetic labels did not implement an employee review workflow. |

Reviewed README, PRD, dashboard plan/checklist, Streamlit guide and pages, paths and
coverage validation, physics pipeline, classifier benchmark code and saved reports,
Nemotron loop, saved tool traces and tests. The PRD contains proposed active measurement
planning and commercial validation goals; these are not implemented by this dashboard
and were not introduced here.

The selected case's known outcome must not be interpreted as representative accuracy.
The existing split-specific candidate catalog also makes this a constrained benchmark,
not unrestricted localization over all 117 pipes. All 117 flow channels are still used.

## Changes

- Employee Monitoring automatically loads a configured archived feed. Replay controls,
  synthetic labels, detailed fit diagnostics and benchmark pages remain in Evaluation / Admin.
- Added observation-only validation for reference time alignment, finite/missing readings,
  stale channels, current-clock freshness and channel coverage. No detector input is imputed
  or altered. The unchanged comparator still makes every valid-feed prediction.
- Retained baseline calculations, added actual observed/normal values for automatically
  chosen affected sensors, enabled schematic pan/zoom and pipe tooltips.
- Added append-only SQLite employee events, idempotent alert registration, acknowledgment,
  review/outcome statuses, notes and UTC history. Reviews never modify benchmark labels.
- Added an explicit AI action reusing the agent and its tools. Default CLI behavior is
  preserved; an optional employee-report instruction argument requests the six report sections.
- Added missing-key/offline, loading, success, partial, budget, failure and storage states;
  bounded requests, attempt accounting, concurrent-request protection, sanitized provider errors
  and unique atomic trace publication. No inference occurs on page load or retry.
- Reuse saved model text only when feed and ranking match. The configured showcase is now
  `case_405`, already used in documentation and backed by a completed saved trace. This
  configuration change does not alter that case's observations, scores or predictions.
- The bundled case 405 answer incorrectly says all leak candidates improve on normal;
  its own ranking contradicts this. The UI explicitly flags this known assertion, preserves
  the original text, and labels missing legacy model provenance. Generic AI text remains
  unverified; the check is not a general natural-language fact checker.
- Corrected the entry-point export that caused the existing test failure; updated positioning,
  operational instructions, persistence guidance and field-validation limitations.

## Files

New: `leakprobe/ui/operations.py`, `alert_store.py`, `ai_service.py`,
`employee_dashboard.py`, `tests/test_employee_dashboard.py`,
`scripts/product_integrity.py`, this audit and `docs/EMPLOYEE_DASHBOARD.md`.

Updated: `streamlit_app.py`, `leakprobe/agent.py` (optional prompt argument only),
`leakprobe/ui/branding.py`, `data_access.py`, `monitoring.py`, `outcomes.py`, `pages.py`,
the dataset compatibility entry point, `.gitignore`, README, PRD, pitch, and Streamlit guide.

## Validation and limitations

Offline unit and Streamlit AppTest coverage exercises valid/invalid data, truth isolation,
stable alert identity, reviews and persistence, AI request budgets and concurrency, mocked
success/failure, unavailable credentials, partial reports, interrupted traces, atomic storage,
legacy evidence matching, entry-point navigation, employee review submission and existing
Admin pages. Final result: **39 tests passed** (27 new tests), 7.720 seconds on the
installed environment. Compilation and `git diff --check` passed. All **1,535**
protected original file hashes remain unchanged. Machine-readable receipt:
`outputs/product_verification/employee_dashboard_verification_20261029.json`.

The host has Streamlit 1.37.1; existing repository requirements pin 1.66.0. Tests were run
against the installed version, and all existing Admin pages were included. Pinned-package
installation was not performed. No browser surface was available for screenshot-based
visual review; interactive UI structure and behavior were verified with Streamlit AppTest.

No new live Nemotron report was requested: paid inference was explicitly excluded. New
six-section report quality and live endpoint behavior remain unvalidated. Legacy text is
real saved model output but cannot prove the exact model identity from its file metadata.
No claim of superior LLM reasoning or improved employee efficiency is established.

Remaining: live ingestion, authenticated employees/Admin access, persistent hosted storage,
work-order/field systems, deployment and field accuracy validation. The UI is an operational
demo over simulated archive data, not a deployed real-time utility monitoring system.
