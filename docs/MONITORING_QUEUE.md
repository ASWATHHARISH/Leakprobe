# Monitoring queue

The Monitoring page now automatically assesses all 500 windows from the canonical
Net3 feed. Employees browse generated assessments rather than configure a sensor
set or manually supply detector inputs. The queue can show all records, records
needing attention, no-alert records, review-required records or unavailable feeds.
Opening a record updates its network schematic, measurements, AI investigation
and review form together. Reviewer status stays attached to the original alert identity.

The records are independent archived windows, not simultaneous incidents on one
network. They include the canonical development and test windows; queue counts are
operational navigation counts, not a new held-out performance estimate. No truth
labels are read while constructing the queue. Invalid feeds remain unavailable.

Initial assessment runs the existing physics comparator. It runs no hydraulic
simulations or AI requests. Compact results are cached under `outputs/operations/`
using hashes of the source observations, reference bank, metadata and detector/UI
logic. Cached records also have an integrity hash. Publication is atomic and never
replaces an existing cache or benchmark report. The original 500/1,000-case datasets,
physics thresholds and classifier reports remain unchanged.

The sidebar now uses Administration, Window replay, Reference outcomes,
Investigation history and Model validation. This remains navigation separation,
not access control. Normal operator pages use operational language. One compact
demo-feed caption remains on Monitoring; About describes the simulated Net3 source
and field-validation limits. These observations must not be represented as live
utility telemetry or field-validated results.

Verification: 49 offline tests passed, including queue integrity, record switching,
no-alert filtering, employee review, truth isolation, AI-call guards and JavaScript
chart rendering. The real cache contains 500 records: 417 detector-flagged records
and 83 no-alert records. These are detector counts, not verified leak counts or an
accuracy estimate. Initial assessment took 119.41 seconds; a fresh-process cache
load took 0.35 seconds on the development host. The full app was also checked with
the real queue and paid inference disabled. All 1,535 protected file hashes remained
unchanged.
