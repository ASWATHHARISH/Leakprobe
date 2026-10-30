# Full-channel high-signal data and workbench

## Completed in this change

- [x] Make the 500-case high-signal Net3 feed the canonical Streamlit app dataset; keep the 1,000-case run separate for classifier comparison.
- [x] Require exactly 92 pressure and 117 flow columns for cases, comparisons, evaluation, and classifier features.
- [x] Regenerate the high-signal observations with the existing case IDs, split, and candidate-pipe assignments.
- [x] Build a full-channel reference bank using the same high-signal parameter ranges.
- [x] Remove the two-branch and sparse Net3 paths from the CLI and Streamlit app.
- [x] Rerun the saved recall-led classifier benchmark on the full-channel high-signal data.
- [x] Document the canonical app data source and the separate 1,000-case experiment.
- [x] Document the separate 1,000-case, 800/200 classifier experiment and its limitations.

## Employee monitoring dashboard

- [x] Load the configured full-channel feed automatically without asking an employee to select cases or sensors.
- [x] Compare pressure and flow readings against the normal-operation reference bank.
- [x] Show the alert state, leading candidate pipe, network map, baseline charts, and channel-level departures.
- [x] Add a held-out outcome review page for after-action use, separate from alert scoring.
- [x] Update navigation and user documentation to explain the employee workflow and limits.

## Hosting

- [ ] Complete Streamlit Community Cloud setup for the authorized repository.
- [ ] Verify the hosted URL after deployment.
