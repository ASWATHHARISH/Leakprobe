# LeakProbe

**AI-Assisted Water Leak Monitoring & Investigation**

LeakProbe helps operators follow a suspected leak from network readings to a candidate pipe, supporting sensor evidence, a Nemotron investigation and a recorded human review. This is a product demonstration using **simulated EPA Net3 data**, not a connected utility deployment.

The application includes 500 browsable records, 92 pressure and 117 flow channels, an interactive network schematic, four record-workspace tabs, employee review history and five original saved investigation traces. A matching validated report is preferred over a newer failed attempt. Not every saved trace is a successful validated report.

## Clone, install and run (Python 3.12)

No GPU, API key, data generation or training is needed to view the included demo. If accessing a private copy of the repository, cloning requires repository permission.

```bash
git clone https://github.com/ASWATHHARISH/leakprobe-streamlit-demo.git
cd leakprobe-streamlit-demo
```

Create and activate an environment:

```powershell
# Windows PowerShell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

```bash
# Linux / macOS
python3.12 -m venv .venv
source .venv/bin/activate
```

Then, on either platform:

```bash
python -m pip install -r deploy/requirements.txt
python deploy/verify_release.py
python -m streamlit run deploy/app.py
```

Open **http://localhost:8501**. If PowerShell blocks activation, use `.\.venv\Scripts\python.exe` instead of `python`; changing system execution policy is unnecessary. Direct runtime dependencies are pinned; this is not a complete transitive dependency lockfile.

For offline viewing, leave `NEBIUS_API_KEY` unset in Streamlit Secrets, including any user-level Secrets file. Monitoring, network and sensor views, saved reports, reviews, Investigation history and Model validation work without provider requests. Loading and navigating pages do not initiate inference.

### Suggested walkthrough

1. In **Monitoring**, search for **LP-0405** (`case_405`) and open the record.
2. Explore **Overview**, **AI Investigation**, **Sensor Analysis** and **Employee Review**. The AI tab can show the saved evidence-validated Nemotron report without a new API call.
3. Open **History & outcomes** for employee actions, **Investigation history** for saved model runs and **Model validation** for frozen classifier results. Reference outcomes are separate from employee confirmations.

Reviews create a local SQLite database under `outputs/operations/`; new investigations create separate trace files. These are runtime records, not files to commit. Cloud-local storage can disappear on restart; durable shared storage is future work. The release verifier intentionally rejects extra runtime files: run it on a clean checkout before starting the app, rather than deleting review history to make it pass.

## Optional live NVIDIA Nemotron investigation

Live inference uses **Nebius Token Factory**, not a local model, and can incur charges. Keep a keyed hosted app restricted to invited viewers through Streamlit Community Cloud. This release has no separate operator login and Python cannot verify Cloud sharing permissions. Public source does not require public access to the keyed app.

For local use, copy `deploy/secrets.example.toml` to `.streamlit/secrets.toml` and replace the placeholder privately. For Community Cloud, enter the same fields in **App settings → Secrets**:

```toml
NEBIUS_API_KEY = "replace_with_your_key"
NEBIUS_BASE_URL = "https://api.tokenfactory.us-central1.nebius.com/v1/"
NEBIUS_MODEL = "nvidia/nemotron-3-super-120b-a12b"
```

Never commit the populated file or paste credentials into a report. The UI reads Streamlit Secrets directly; a repository `.env` is not its configuration mechanism. Both entrypoints use the same app: `deploy/app.py` does not enforce offline mode when a key is present. The existing live Cloud entrypoint remains **`deploy/live/app.py`**, branch **`main`**, Python **3.12**, with `deploy/live/requirements.txt`.

Open **AI Investigation** and explicitly click **Run AI Investigation**. Nemotron retrieves compact evidence and targeted sensor readings, submits a structured employee report and checks its cited facts against tool evidence. Incomplete or invalid attempts remain separate; a failed run does not replace an older valid report.

The recovered implementation retains its existing limits: four model requests, eight tool calls, 2,048 output tokens per request, 30-second SDK timeouts, zero SDK retries and two attempts per alert in the local review ledger, including failures. It prevents overlapping pending runs for the same alert. These are not a provider-side dollar cap or a global concurrency guarantee. A validation correction may use a remaining request within that investigation budget. Previous operator-login, signing-permit and process-wide activation implementations are not present in this release.

## NVIDIA Nemotron and Nebius contributions

- **Physics first:** deterministic reference matching produces leak/normal assessments and candidate rankings from all 209 channels. Nemotron does not replace the detector or alter its ranking.
- **NVIDIA Nemotron:** the configured Nemotron 3 Super model selects allowlisted evidence tools, examines unusual readings and alternatives, and produces employee explanations and verification recommendations.
- **Nebius Token Factory:** hosts model inference through its OpenAI-compatible API. Streamlit hosts the interface; Nebius is not claimed as the UI host or hydraulic simulator.
- **Validation and human review:** local checks verify cited values, signs, units, sensors and ranking facts. Employees acknowledge alerts and record findings independently of generated labels.

See [Architecture](docs/ARCHITECTURE.md) for code responsibilities and implemented versus planned capabilities. Model/API access has separate [third-party terms](THIRD_PARTY_NOTICES.md); the MIT source license does not provide API credits or model weights.

## Data and evaluation boundaries

| Included evidence | Scope |
|---|---|
| `data/net3_full_high_signal/` | Canonical 500 simulated windows: 400 development, 100 held-out; 92 pressure and 117 flow channels. |
| `data/net3_full_high_signal_benchmark/` | Saved experimental classifier reports and predictions; the classifier is not the operational detector. |
| `data/net3_full_high_signal_1000/` and its benchmark directory | Separate sample-size experiment, not the Monitoring feed. The 500-case split/label/pipe assignments were reused twice with fresh measurements, not independent broader pipe coverage. |
| `outputs/evaluations/net3_full_pipes_comparison.md` | Existing physics/classifier comparison, retained unchanged. |
| `outputs/traces/` | All five original model attempts, including invalid and legacy attempts. |

The saved physics result on the **100-case high-signal held-out set** is TP/FN/FP/TN **76/4/1/19**: 95% recall, 95% specificity and exact pipe on 75/80 actual leaks. These are original synthetic-benchmark results, not new evaluations or field accuracy. The [comparison report](outputs/evaluations/net3_full_pipes_comparison.md) provides denominators, false alarms and limitations.

The benchmark uses 28–35 mm leak openings lasting 4–4.5 hours and aligned demand ranges. Candidate sets are declared per split: 17 development pipes and seven held-out pipes, not all 117 observed pipes. RMSE is a fit error, **not a probability**. Earlier difficult Part C experiments are different conditions: this showcase does not overturn their negative results or demonstrate reliable detection of small, short or unmodeled leaks.

Do not regenerate data, train models or overwrite saved evaluations to start the demo. Historical generation/evaluation commands may write outputs. There is no live utility connection, verified field accuracy, automatic dispatch, active sensor planning or Nemotron fine-tuning in this release.

## Offline tests

These checks mock provider requests and use disposable review storage:

```bash
python -m unittest discover -s tests -p test_cloud_recovery.py -v
python -m unittest discover -s tests -p test_employee_dashboard.py -v
```

For the full suite, add the test-only chart renderer:

```bash
python -m pip install vl-convert-python==1.8.0
python -m unittest discover -s tests -v
```

`requirements.txt`, `requirements-llm.txt` and `requirements-test.txt` retain broader development/classifier dependencies. They are unnecessary for basic viewing when using the pinned deployment runtime.

## License and documentation

Team-owned LeakProbe code is under the root [MIT License](LICENSE). All code owners approved MIT and public redistribution on 30 October 2026. Net3 and installed third-party packages retain their own terms; see [Third-party notices](THIRD_PARTY_NOTICES.md) and the retained [WNTR notices](licenses/WNTR-1.3.2-LICENSE.md).

The [submission checklist](docs/SUBMISSION_READINESS.md) records audit scope, verification and remaining publication steps. This README and [Architecture](docs/ARCHITECTURE.md) describe the recovered release. Older guides, PRD, pitch and task notes are retained for provenance and may describe earlier behavior or proposals; they do not override current setup or establish completed capabilities.
