# LeakProbe — AI-Assisted Water Leak Detection & Investigation

Monitor network signals, investigate anomalies, identify candidate leaks, and support faster field response.

LeakProbe is a Streamlit workbench for comparing a water-network sensor feed with normal-operation and candidate-leak patterns. The app uses the **canonical 500-case high-signal Net3 dataset**, with pressure at all 92 junctions and flow in all 117 pipes. A separate 1,000-case run is retained for a sample-size comparison; it is not an app data source.

The cases are generated from the EPA EPANET Example Network 3 model. They are useful for a controlled benchmark and do not establish performance on a utility network.

## Start the app

Use Python 3.12, create an environment, and install the pinned packages:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
streamlit run streamlit_app.py
```

The Monitoring page automatically assesses the canonical 500 recorded sensor windows and presents a browsable alert queue. Employees filter and open generated assessments; they do not configure sensor channels or detector inputs. The selected record shows its interactive network schematic, affected sensors, observed readings versus baseline, AI investigation and review form. All 92 pressure and 117 flow channels are retained. The **demo feed** uses archived simulated Net3 observations; these independent windows are not simultaneous live incidents. Archived timestamps and incomplete readings are explicitly flagged.

**AI Investigation** displays a matching saved model explanation and offers an explicit **Run AI Investigation** action using the existing Nebius/Nemotron tool loop. Opening a page never calls the provider. New runs are limited to four model requests and eight tool calls, with two attempts per alert and no automatic retries. Without credentials, monitoring, saved explanations and employee review remain available offline. Legacy traces lacking a model identifier are labeled honestly; their text is not silently rewritten.

Employees can acknowledge alerts, record review status, enter notes, and record leak confirmed / no leak / further investigation required. UTC event history is stored in a local SQLite database. **History & outcomes** shows employee reviews; synthetic labels, replay controls, technical diagnostics, traces, and classifier benchmarks are under **Evaluation / Admin**. Admin is navigation separation, not an authentication boundary.

See [the employee guide](docs/EMPLOYEE_DASHBOARD.md) for launch and verification commands and [the implementation audit](docs/EMPLOYEE_DASHBOARD_AUDIT.md) for scope and limitations.

To run an offline investigation from the terminal:

```bash
python run_demo.py --scripted
```

To use the optional Nebius/Nemotron explanation, install `requirements-llm.txt`, configure `.env` from `.env.example`, and run:

```bash
python run_demo.py
```

The LLM receives the case observations and tool outputs. Provider requests can incur charges. ChatGPT Pro access is not an API credential.

## The only supported sensor layout

Every case must contain exactly:

- 92 pressure columns, one for every Net3 junction.
- 117 flow columns, one for every Net3 pipe.

Missing readings may occur within those columns. The channel definitions and columns must remain complete. The app, physics-based comparator, evaluator, high-signal generator, and classifier all reject a smaller or incomplete channel set.

The canonical dataset is `data/net3_full_high_signal/`. It contains 500 cases: 400 development cases (320 leaks and 80 normal) and 100 held-out cases (80 leaks and 20 normal). It also contains the per-case outcomes and a reference-pattern bank matched to its high-signal leak ranges.

## Separate 1,000-case experiment

`data/net3_full_high_signal_1000/` contains 800 development cases and 200 held-out cases, all with the same 92 pressure and 117 flow channels. It was generated to check how classifier scores vary with a larger sample. Case split, outcome, and leak-pipe assignments from the 500-case set were each reused twice; readings and simulation parameters were generated afresh, so this run adds measurement variation but no new pipe assignments. The app continues to use the canonical 500-case dataset.

The experiment's classifier report is [`data/net3_full_high_signal_1000_benchmark/report.md`](data/net3_full_high_signal_1000_benchmark/report.md). To rerun it:

```bash
python -m leakprobe.smote_benchmark \
  --source data/net3_full_high_signal_1000 \
  --output data/net3_full_high_signal_1000_benchmark
```

## Evaluate and benchmark

Run the physics-based comparison on the held-out cases:

```bash
python evaluate_net3.py --split test
```

Run the recall-led classifier benchmark. SMOTE is applied only inside the training folds, and the alert threshold is selected using out-of-fold development predictions:

```bash
python -m leakprobe.smote_benchmark
```

Results and per-case predictions are written to `data/net3_full_high_signal_benchmark/`. The test split is reserved for final reporting. Use the held-out numbers to compare precision, recall, false alarms, and missed leaks.

The 500-case development split contains 320 leaks and 80 normal cases. Default SMOTE therefore generates normal-like examples to balance training; it does not add synthetic leak cases.

The obsolete demo data, sparse-channel datasets, and separate standard-range archive have been removed. The canonical app data and the documented 1,000-case experiment are the retained Net3 datasets.

## Regenerate the high-signal feed

The generator preserves the 500 case IDs, split, and pipe assignments, then regenerates full-channel observations and a matching reference bank:

```bash
python generate_data.py
```

The benchmark intentionally uses 28–35 mm leak openings lasting 4–4.5 hours. Leak and normal demand ranges are aligned across the development and test splits. This makes the detection task easier and is useful for comparing classifier behavior, but it can overstate performance relative to smaller or shorter leaks, unmodeled operating changes, or real sensor feeds. Re-run the classifier benchmark and physics-based evaluation after regenerating the data; saved metrics do not automatically transfer.

The included network file is `data/networks/Net3.inp`. Net3 has 92 junctions, 117 pipes, two pumps, and two reservoirs. WNTR uses meters, seconds, and cubic meters per second internally; saved pipe flow is in liters per second and pressure is in meters of water head.

## Reading the metrics

Leak is the positive class:

- **Precision**: of the cases flagged as leaks, how many are labeled leaks.
- **Recall**: of the leak cases, how many are flagged.
- **False alarm**: a normal case flagged as a leak.
- **Miss**: a leak case not flagged.

A high-recall operating point can catch more leaks while increasing false alarms. The 80/20 held-out class balance also means an always-leak classifier would have 100% recall, 80% precision, and 0% specificity; that would not be a useful detector. Review the confusion matrix and balanced accuracy alongside precision and recall.

The physics-based matcher ranks reference simulations by normalized fit error. The error is not a probability. Classifier scores and results on these generated cases are not field validation.

## Project layout

```text
leakprobe/                         Python implementation
data/net3_full_high_signal/        Canonical app dataset, 500 cases, 92/117 channels
data/net3_full_high_signal_benchmark/ Canonical classifier reports and predictions
data/net3_full_high_signal_1000/   Separate 800/200 sample-size experiment
data/net3_full_high_signal_1000_benchmark/ Experiment report and predictions
data/networks/Net3.inp             EPANET network model
docs/                              Product and Streamlit documentation
outputs/evaluations/               Current full-channel evaluation report
streamlit_app.py                   Streamlit entry point
```

See [PITCH.md](PITCH.md), [the product requirements](docs/LeakProbe-PRD.md), and [the Streamlit guide](docs/STREAMLIT_FRONTEND_README.md) for product scope and hosting notes.
