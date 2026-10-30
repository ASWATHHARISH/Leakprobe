# Submission readiness — 30 October 2026

Prepared locally from recovery commit `a0954fb0bd289e39561c35ef5e99794684c72c58` for `ASWATHHARISH/leakprobe-streamlit-demo`. No application, detector, agent, prompts, deployment settings, datasets, rankings, reports or original traces are changed. No publication, history rewrite, deployment, paid inference or data deletion was performed.

## Requirements

The [official rules](https://nebiusglobalaihackathon.devpost.com/rules) require publicly accessible source, an identifiable open-source license and sufficient code/assets/instructions for judging. The table distinguishes prepared local material from actual publication.

| Requirement | Status | Evidence / remaining action |
|---|---|---|
| Public code repository | **BLOCKED** | GitHub still reports **Private**. Explicit permission to commit/push these changes and change visibility is still needed; owner licensing consent alone is not an instruction to publish. |
| Code-owner permission | **PASS** | Owner confirmed all code owners approved MIT and public redistribution on 30 October 2026. |
| Root open-source license | **PASS — local** | Complete root `LICENSE` contains MIT text and team contributor copyright. Publish it with the prepared package; GitHub license detection is not yet verified. |
| Python 3.12 setup and run instructions | **PASS — local** | README gives clone/venv/pinned runtime install, verifier and entrypoint commands on Windows and Linux/macOS. Removes the nonexistent `.env.example` dependency. |
| Offline and optional live setup | **PASS — local** | Offline needs no key; live uses the existing placeholder-only Streamlit Secrets template. Viewer restrictions remain required for keyed hosting. |
| NVIDIA and Nebius contributions | **PASS — local** | README and Architecture explain Nemotron tools/reporting, Token Factory inference, physics ranking, citation checks and human review separately. Saved genuine model evidence is retained. |
| Scientific integrity / honest claims | **PASS** | High-signal metrics and their denominators are cited from existing results. Earlier difficult Part C work is not represented as the same test conditions. No new experiment or live performance claim. |
| Third-party provenance and notices | **PASS — source release scope** | Exact Net3 content traced to WNTR 1.3.2; BSD/copyright/disclaimer and included notices retained. Model/service and package terms remain separate from MIT. |
| Credential / database review | **PASS — scan scope below** | No production credential, private key, populated Secrets file or database identified in reachable history. Literal matches are placeholders/test fixtures. |
| Runtime and regression verification | **PASS** | Offline tests and entrypoint checks are recorded below. No real provider request. |
| Final public access / license detection | **BLOCKED** | Requires later approved publication and a signed-out GitHub check. The live app's sharing settings are unchanged. |

## History and sensitive-file audit

- Reviewed all **four commits** reachable from the release's complete, non-shallow history: `865d27a…`, `1f306b6…`, `a899f6a…`, `a0954fb…`.
- Remote advertisement shows only `main` at `a0954fb…` and `backup/pre-dhanya-recovery-20261030-151421` at `a899f6a…`, with no tags. The backup is an ancestor of main and covered by the same scan. Dhanya's repository and original working directories were not modified.
- Scanned **1,673 unique reachable blobs**, totaling **254,156,178 uncompressed bytes**, including files removed from the latest tree. Checks covered provider/GitHub/AWS token patterns, bearer credentials, private keys, credential-bearing URLs, literal credential assignments, sensitive filenames, SQLite signatures, email-shaped content and local paths. No matched credential values are reproduced in audit receipts.
- Fourteen assignment matches were manually triaged: historical documentation and the Secrets template use placeholders; historical/current tests use synthetic credentials or patched environment/Secrets fixtures. No actual credential was identified. No tracked database, key file, populated `.env` or `secrets.toml` was found in any reviewed commit.
- Two commits contain a **personal author/committer email**. Making history public exposes that metadata. Review this before authorizing publication; the address is not reproduced here and no history rewrite is proposed automatically.
- Two historical documents contain local Windows project paths. They are setup/provenance references, not secrets. No customer contact records or real utility sensor data were identified.

This is a pattern scan and manual review of reachable Git content, not a guarantee against every unknown credential format, a vulnerability audit, a check of server-side unreachable objects/PR caches, or an inspection of the owner's actual Secrets or service contract.

## File classification and retention

The [complete baseline file inventory](SUBMISSION_FILE_INVENTORY.csv) classifies all **1,613 tracked files at the recovery commit**. Newly added submission documents are not part of that baseline inventory.

| Class | Files | Decision |
|---|---:|---|
| Source, tests and packaging | 62 | Retain. No code/dependency/deployment changes. |
| Demo / benchmark / saved evidence | 1,537 | Retain all datasets, reference profiles, evaluation outputs, three monitoring caches and all five model attempts. |
| Documentation | 11 | Retain; current README/Architecture are the authoritative setup/scope. |
| Optional development artifacts | 3 | `.vscode/launch.json`, `tasks/plan.md`, `tasks/todo.md`; candidates for later removal/archive only with approval. |

The baseline working tree is **253,348,590 bytes** including its manifest (about 241.6 MiB). Largest files are the two approximately 29.1 MB reference banks and the 28.0/14.0 MB feature tables. These are scientifically relevant, not disposable build output. No tracked file exceeds 100 MB. No datasets or reports were reduced for submission.

The first historical monitoring cache is redundant in record content with the Windows/Linux caches, but it remains preserved. It is not a private review database. A lean hosting package would be a separate task; the submission package retains the documented 1,000-case experiment.

## Documentation that can confuse a reader

| File(s) | Issue | Recommendation |
|---|---|---|
| `deploy/README.md` | Recovery/publication procedure includes assumptions that predate this submission cleanup. | Retain for recovery provenance. Use root README for current setup; do not blindly execute old publication commands. |
| `docs/EMPLOYEE_DASHBOARD.md`, `EMPLOYEE_DASHBOARD_AUDIT.md`, `STREAMLIT_FRONTEND_README.md` | Some historical setup/context statements describe older UI, environment or evidence behavior. | Keep historical records; do not treat them as overriding the current README. Later add historical labels if desired. |
| `PITCH.md`, `docs/LeakProbe-PRD.md` | Product aspirations extend beyond demonstrated behavior. | Treat as proposals. Architecture lists the actual implemented boundaries. |
| `tasks/plan.md`, `tasks/todo.md` | Stale completion/deployment checklists. | Optional archive/removal later, never scientific evidence deletion. |
| `.vscode/launch.json` | Local developer launches, including legacy CLI workflows. | Optional removal later; not needed to run the dashboard. |

No removals were made. Invalid investigation traces are useful negative evidence and are not classified as unnecessary artifacts.

## Verification and preservation

Fresh offline verification: **86 tests passed, zero failures/errors/skips**, in 176.3 seconds. It used the existing Python 3.12 test environment, pinned runtime and mocked SDK, not a new clean installation. Both the real SDK completion method and external socket connections were blocked. Review writes used disposable databases outside this package.

The entrypoint smoke check verifies both `deploy/app.py` and `deploy/live/app.py`, all 500 cached records, consecutive selection, four Monitoring tabs, the validated case_405 report, disabled paid action without credentials, saved history, Model validation and About. This is an AppTest/runtime check, not a new manual browser review or a fresh paid-provider test. Existing Streamlit `use_container_width` and WNTR `pkg_resources` deprecation warnings remain; changing UI code is outside this task.

Integrity checks passed for **1,618 manifest-listed release files**. All **1,610 protected existing files**, including **1,528 data files and five saved traces**, retain their original hashes. All nine declared direct runtime pins match the test environment. Nine representative credential/database/new-trace ignore checks passed, and the original trace files and sample configuration remain includable.

The final release receipt records the unchanged application/data/deployment hashes, refreshed packaging manifest, release verifier result and automated test count. Local raw receipts live outside the release in `outputs/submission_readiness_20261030/` in the parent workspace; they are not deployment assets. The versioned manifest is refreshed only for the approved documentation, license and ignore-rule additions.

## Minimal remaining publication steps

1. Review this local documentation/license diff and acknowledge the personal-email history exposure if acceptable.
2. Explicitly authorize committing/pushing the prepared changes and changing the personal repository to Public. No such actions have occurred during this task.
3. After approved publication, verify signed-out access, root MIT license detection, clone/setup instructions and the final source commit in the submission form.
4. Keep the keyed Streamlit application private. Provide judges appropriate access or the credential-free/offline demonstration; do not publish API credentials to simplify access.

No known unredistributable asset was identified in the reviewed source package once the retained Net3/WNTR notices accompany it. The separate model and account-specific service terms remain applicable; this statement is not a clearance for shipping model weights or a binary/container distribution.
