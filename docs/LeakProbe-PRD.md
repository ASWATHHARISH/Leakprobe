# LeakProbe — Product Requirements Document

**Version:** 1.1 · **Date:** 21 October 2026  
**Status:** Proposed product specification. A separate educational demo and synthetic benchmarks now exist; this PRD is not a description of a completed product. No customer commitments or field validation are implied.
**Intended readers:** Founder, AI engineer, hydraulic modeling adviser, utility design partner, product reviewer.  
**Product owner:** Founder; named owner to be assigned before implementation.

> LeakProbe helps water-network engineers choose the next feasible measurement that is expected to reduce uncertainty about a suspected leak.

## 1. Executive decision

### Employee demo update (29 October 2026)

The employee view now uses an automatic simulated feed with explicit freshness and
coverage reporting, persistent employee alert reviews, and an on-demand bounded AI
investigation action. Synthetic labels and replay are under Evaluation / Admin.
The configured showcase is `case_405`; its existing model explanation is reused only
when the readings and ranking match. Legacy reports disclose missing model provenance
and known evidence contradictions. No paid inference or deployment was performed.
See [the implementation audit](EMPLOYEE_DASHBOARD_AUDIT.md) and
[employee guide](EMPLOYEE_DASHBOARD.md). Historical status below describes the prior
implementation; the longer-term PRD remains proposed scope, not completed functionality.

### Current repository status (28 October 2026)

The repository contains a runnable Streamlit workbench with an employee monitoring dashboard. The dashboard loads a configured full-channel window automatically, compares it with normal-operation profiles, and presents a candidate alert with supporting pressure, flow, and network-map evidence; employees do not choose cases or sensors. A separate history page exposes held-out outcomes for after-action review. The app uses a canonical 500-case high-signal Net3 dataset with full coverage (92 junction pressures and 117 pipe flows), 400 development cases, and 100 held-out cases. A separate 1,000-case classifier experiment uses the same channel layout and simulation ranges; it is not an app source and does not add candidate-pipe coverage. The canonical reference bank has 24 leak profiles per candidate pipe and 24 normal profiles, matched to the high-signal leak ranges. The physics-based detector ranks reference patterns; a separate case-level classifier compares baseline, class weighting, and SMOTE.

The monitoring page currently uses the fixed `case_405` feed as a repeatable example; its labeled leak is on pipe 202, and the map highlights that pipe from the top-ranked comparison. The feed is not connected to live utility telemetry. Two saved LLM traces (cases 400 and 405) seed the run-history view. High-signal leak openings are 28–35 mm and last 4–4.5 hours; demand ranges match across development and test. This intentionally makes the benchmark easier. The physics-based ranking currently has no calibrated rejection threshold. The separate classifier chooses its recall-led threshold from out-of-fold development predictions, then reports the held-out set once. See `data/net3_full_high_signal_benchmark/report.md` for current precision, recall, and confusion matrices.

Classifier thresholds and results are specific to the current cases, features, and reference ranges. Normalized fit scores are not probabilities. Re-run evaluations after regenerating cases or reference profiles.

The remaining requirements below describe proposed product scope and future validation, not capabilities implied by the demo.

Build a software-only research MVP for sequential leak investigation in a small water distribution network. Import an existing hydraulic model and pressure/flow observations, rank plausible explanations, simulate possible additional measurements, and recommend a short investigation plan under explicit time and access constraints.

The first product is a decision-support application, not a new leak sensor, an autonomous network controller, or a claim of excavation-ready localization. It can be developed and demonstrated without field access. Proving operational savings requires a utility or engineering partner with a suitable model, recorded incidents, and eventually staff who can collect measurements.

The proposed commercial advantage is **cost-aware selection of the next useful observation, with visible uncertainty and reproducible evidence**. This is a hypothesis, not an established unique capability. Continue only if LeakProbe improves on practical measurement-selection baselines and customers value the improvement.

If the founder requires a business whose effectiveness can be validated entirely without physical-world collaborators, stop at a research/benchmark product or choose an operational software-twin product instead. LeakProbe's interface is digital; its eventual ground truth is physical.

## 2. Assumptions and evidence boundaries

| ID | Working assumption | Consequence if false |
|---|---|---|
| A1 | LeakProbe concerns leaks in pressurized water distribution pipes | Gas, oil, sewer, and building-plumbing use cases need separate requirements |
| A2 | The first release is an English-language browser application with batch file imports | Live connectors and localization are deferred |
| A3 | A usable EPANET-compatible network model exists | Do not promise to reconstruct a trustworthy network from sparse telemetry |
| A4 | Sensor IDs can be mapped to model elements, timestamps, units, and elevations where applicable | Investigation is blocked until mapping is resolved |
| A5 | A partner can supply a list of accessible measurement points | Recommendations remain hypothetical without this list |
| A6 | Measurements are observational; no valve or pump changes are proposed in the MVP | Active hydraulic interventions require separate engineering review and scope |
| A7 | Single dominant leak or no leak is the initial supported inference regime | Multiple leaks and other mismatches must trigger uncertainty, not forced localization |
| A8 | Founder has no guaranteed utility relationship or field engineer | Public simulation is the initial validation path |
| A9 | Human engineers own field decisions | Outputs are recommendations and evidence, never control commands |

Evidence labels must appear in the product and exports:

- **Synthetic experiment:** fully simulated observations and known hidden truth.
- **Public benchmark:** externally published benchmark, with its simulated/observed provenance stated.
- **Historical replay:** recorded partner observations; available future measurements restricted to those actually recorded.
- **Prospective shadow pilot:** recommendations compared with real investigations without directing operations.
- **Prospective assisted pilot:** partner engineers choose whether to act and record outcomes.

No label may be automatically upgraded because model confidence is high.

## 3. Problem and user outcome

A flow or pressure anomaly can be consistent with several explanations: a leak, changing demand, a sensor fault, incorrect model parameters, or an unrecorded operating change. Sparse sensors can leave several pipe groups indistinguishable. An engineer must decide where to gather additional evidence with limited staff time and incomplete access.

LeakProbe addresses the decision after an anomaly is suspected:

> Given these observations, this model, and the measurements we can actually collect, what should we check next—and when is the model too unreliable to recommend anything?

Desired outcomes are fewer low-value measurements, smaller search regions at comparable coverage, clearer handoffs, and faster decisions. Actual reductions in water loss, repairs, or excavation costs are downstream outcomes to measure in a pilot, not MVP promises.

### Illustrative scenario

A hypothetical district has abnormal flow and several plausible leak regions. One accessible pressure point would distinguish two major candidate groups; another nearby point is cheaper but would produce nearly identical readings under all leading hypotheses. LeakProbe ranks the first point higher after considering expected uncertainty reduction and cost. An engineer approves collection, uploads the result, and sees an updated candidate region—or an abstention if the result contradicts the modeled hypotheses.

This scenario is illustrative, not a customer result. Pressure measurements alone may never identify one exact pipe.

## 4. Customers, users, and buying process

| Segment | User / economic buyer | Potential value | First-entry route |
|---|---|---|---|
| Municipal or regional water utility | Leakage analyst / head of network operations | Better use of investigation capacity | One modeled district, one bounded retrospective study |
| Water engineering consultancy | Hydraulic modeler / practice lead | Repeatable investigation analysis for clients | Offline project tool using permitted model exports |
| Leakage investigation contractor | Investigation lead / operations director | Prioritize authorized measurement visits | Supply recommendations through its utility client |
| Large water operator | Regional engineering team / digital or operations leader | Repeatable analysis across service areas | Local operational sponsor before corporate procurement |
| Water software provider | Product/partnership team | Embedded planning capability | Only after independent evidence of added value |

**Prospective account hypotheses:** utilities or operating units associated with Veolia and SUEZ; engineering businesses such as Arcadis, Jacobs, and WSP; platform businesses such as Xylem and Bentley. These names describe possible categories to research, not known demand, accessible data, compatibility, endorsements, or active prospects.

A small consultancy with an existing utility relationship may be a more practical first partner than a global vendor. Required stakeholders include the model owner, leakage engineer, data/security owner, and budget owner. No assumed sales-cycle duration is used in the plan.

### Jobs to be done

1. As an analyst, I need to distinguish plausible leak regions without pretending the strongest score is certainty.
2. As an investigation lead, I need the next recommendation to respect access, equipment, and available time.
3. As a modeler, I need to understand whether disagreement comes from a leak hypothesis or an inadequate model.
4. As a manager, I need a reproducible explanation of why an investigation step was proposed.
5. As a researcher, I need to compare policies under the same observations, costs, and simulation budget.

## 5. Competitive context and proposed positioning

| Existing capability | Verified reference | Implication for LeakProbe |
|---|---|---|
| Hydraulic network simulation | EPA EPANET [S1] | Use an established engine; building a new hydraulic solver is out of scope |
| Leak and pressure-dependent simulation | EPA WNTR [S2] | A practical research foundation; simulation fidelity still needs validation |
| Leak detection and localization | Xylem Vue [S5] | Neither detection nor localization alone is a defensible new claim |
| Operational water twins, anomaly detection, and leak geolocation | Bentley OpenFlows WaterSight [S6] | Complement existing tools only if incremental value is demonstrated |

Positioning hypothesis: **an uncertainty-aware investigation planner that works from exported models and observations and selects affordable, feasible next measurements.**

Do not claim Xylem or Bentley lack this capability because a public page does not describe it. Before commercialization, compare workflow depth, measurement planning, uncertainty handling, integrations, pricing, and customer satisfaction through demonstrations and customer interviews. Active sensing and information-based experimental design are established research areas; a separate literature and IP review is required before novelty or patent claims.

Potential defensibility could come from validated integrations, trustworthy calibration, accumulated permissioned investigation outcomes, and useful deployment workflows. An LLM, a map, or a GPU is not a moat.

## 6. Goals, non-goals, and release scope

### Goals

- G1: Rank leak regions and alternative explanations from a bounded observation window.
- G2: Recommend a feasible next pressure measurement or available telemetry retrieval.
- G3: Quantify sensitivity to demand, sensor noise, and model uncertainty.
- G4: Update recommendations after a genuine new observation.
- G5: Produce an auditable experiment and investigation record.
- G6: Establish whether an AI-assisted workflow improves on a numerical planner alone.

### MVP boundaries

| Included in research MVP | Deferred to partner pilot | Explicitly excluded |
|---|---|---|
| One versioned network per investigation | Partner-approved model calibration | Automatic excavation instructions |
| EPANET INP + CSV imports | Read-only telemetry connectors | Pump, valve, or SCADA actuation |
| Pressure and flow evidence | SSO and private deployment | Gas/oil/transient/acoustic modeling |
| Single dominant leak + no-leak hypotheses | Broader operational confounders | Universal exact-pipe localization |
| Observational pressure measurement selection | Mobile field workflow | Replacing utility engineering staff |
| Accessible-point catalog and budgets | Multiple simultaneous leaks | Building a model from missing topology |
| Simulation runner, baselines, reports | Work-order export after authorization | Verified water-saving claims from simulation |

Proposed initial performance envelope: approximately 50–200 junctions, up to 20 initial sensors, up to 25 candidate measurement locations, and a 24-hour investigation window. These are engineering targets to profile, not supported limits already achieved. Larger public networks can be used in separate offline experiments.

## 7. User journey and interface

1. **Create workspace:** select evidence mode, network version, and investigation owner.
2. **Import model:** parse INP; show topology, units, unsupported controls, and missing metadata.
3. **Import observations:** map sensors, inspect timestamps and missingness, and resolve validation errors.
4. **Check readiness:** show model-data residuals on an appropriate reference window; avoid calling an unverified baseline leak-free.
5. **Define investigation:** anomaly window, accessible points, equipment, cost/time estimates, and maximum steps.
6. **Analyze:** show candidate regions, alternative hypotheses, residual evidence, and model adequacy.
7. **Review proposed measurements:** rank only feasible actions and show expected benefit, uncertainty, cost, and alternatives.
8. **Record decision:** engineer accepts, rejects, or modifies the plan; changes are versioned.
9. **Ingest result:** record observed value, collection time, quality, and operator; simulated outcomes remain visibly separate.
10. **Update or stop:** narrow hypotheses, recommend another step, or abstain.
11. **Export:** human-readable report and machine-readable reproducibility bundle.

### Required screens

- Workspace and evidence-mode selector.
- Data import and quality report.
- Network schematic or geographic map; missing real coordinates must not create fictitious geographic precision.
- Investigation view with candidate-region overlay and observed-versus-predicted plots.
- Measurement comparison table and confirmation panel.
- Timeline of observations, model versions, recommendations, and operator decisions.
- Benchmark view with baseline comparisons and uncertainty intervals.
- Evidence export and access controls.

Color must not be the only encoding. Tables and charts require labels, units, keyboard access, and readable error states. On-screen language must distinguish “predicted,” “observed,” and “confirmed.”

## 8. Functional requirements and acceptance criteria

P0 = research MVP; P1 = partner pilot; P2 = later release.

| ID | Priority | Requirement | Acceptance condition |
|---|---|---|---|
| FR01 | P0 | Import versioned network model | Valid fixture loads; bad element references and unsupported features produce actionable errors |
| FR02 | P0 | Normalize observation units and timestamps | Conversion fixtures round-trip within specified tolerance; missing timezone/unit blocks analysis |
| FR03 | P0 | Validate sensor mapping and quality | Unknown IDs, conflicting duplicates, stale readings, and invalid quality flags are surfaced |
| FR04 | P0 | Freeze investigation inputs | Every run records immutable hashes of model, observations, settings, and constraints |
| FR05 | P0 | Run baseline model adequacy checks | Excess residuals show a quality failure or reduced-confidence state; no silent pass |
| FR06 | P0 | Maintain hypothesis ensemble | Include no leak and configured leak locations/severities; expose unsupported explanations |
| FR07 | P0 | Rank regions with uncertainty | Report candidate set plus model-conditional scores; do not present uncalibrated scores as validated probabilities |
| FR08 | P0 | Enforce action feasibility | Inaccessible, unavailable, over-budget, or incorrectly mapped locations are never selectable |
| FR09 | P0 | Rank next measurements | Each action has units, sampling window, predicted benefit, cost basis, and uncertainty |
| FR10 | P0 | Incorporate actual new measurements | A new result creates a new run; the prior recommendation is retained |
| FR11 | P0 | Abstain and stop | No feasible action, poor fit, low benefit, or exhausted budget gives an explicit reason |
| FR12 | P0 | Explain from evidence | Reported numerical claims come from structured results; unsupported generated claims fail validation |
| FR13 | P0 | Compare planning policies | Policies use the same initial evidence and action catalog; oracle is isolated from planners |
| FR14 | P0 | Export evidence | Bundle contains report, manifest, scenario identifiers, metrics, and replay configuration |
| FR15 | P0 | Work without an LLM | Numerical analysis and templated report complete when inference is unavailable |
| FR16 | P1 | Roles and tenant isolation | Cross-tenant reads/writes fail; viewer cannot upload or approve changes |
| FR17 | P1 | Private-data handling | Retention, deletion, hosting, and provider routing are agreed and technically enforced |
| FR18 | P1 | Partner result feedback | Confirmed, disproved, unresolved, and repair outcomes are distinguishable |
| FR19 | P2 | External system connectors | Each connector has documented field mapping and read-only permissions by default |

## 9. Data sources and acquisition plan

| Source | What it supplies | Appropriate use | Limit |
|---|---|---|---|
| EPANET example models and WNTR examples [S1, S2] | Network models and simulation tools | Small controllable experiments | Not observations of a partner network |
| LeakDB [S3] | Artificially generated leakage scenarios across networks | Detection/localization benchmark and robustness checks | Synthetic; dataset alone may not provide all counterfactual measurements |
| BattLeDIM / L-Town [S4] | Hypothetical network, telemetry-style benchmark, evaluation resources | External benchmark with model uncertainty | Simulated setting; official evaluation differs from custom action-planning metrics |
| Partner exports | INP model, sensor registry, historical observations, confirmed incidents | Retrospective evaluation and model fit | Access, rights, quality, and completeness are unconfirmed |
| Prospective partner observations | Measurements collected during approved investigations | Operational validation | Requires partner staff and protocols |

LeakDB explicitly describes artificial scenarios. BattLeDIM describes a hypothetical town and a modeled investigation setting. Neither should be presented as independent field validation. [S3, S4]

Record license, attribution, permitted commercial use, version, and download checksum before including any dataset or model in a distributed demo. Public availability is not sufficient permission to redistribute.

### Minimum customer onboarding package

- Model export with boundary conditions, operating assumptions, unit system, and owner.
- Sensor registry with element mapping, quantity, units, sampling interval, calibration/noise information, and validity periods.
- Historical observations and known incident/repair records with timestamps and confirmation status.
- Available-point inventory with access, compatible equipment, restrictions, and cost/time estimates.
- Model calibration history, known uncertainties, and operating changes.
- Explicit permission for intended processing, deployment, and third-party inference if any.

Do not require a proprietary vendor API for the first pilot. Start with permitted exports; verify export fidelity rather than assume perfect interoperability.

## 10. Data contracts and core entities

Canonical internal units: meters of pressure head, cubic meters per second for flow, meters for lengths, UTC timestamps, and seconds for elapsed durations. Preserve source units. Conversion from pressure to head must record density and gravity assumptions; pressure head and hydraulic head are different quantities.

| Entity | Minimum fields |
|---|---|
| NetworkVersion | workspace_id, network_id, version, INP hash, source units, coordinate metadata, engine compatibility, assumptions |
| Sensor | sensor_id, element_id, quantity, source unit, uncertainty model, validity interval |
| Observation | sensor_id, timestamp, value, unit, quality, source, collection interval, import_id |
| Incident | incident_id, evidence mode, start/end window, network_version, status, owner |
| Action | action_id, node/element, quantity, sampling window, equipment, feasibility, cost/time, expiry |
| Hypothesis | type, original asset/region, leak parameters, nuisance parameters, prior, result status |
| Run | run_id, input hashes, versions, seed, budget, state, timing, compute cost, warnings |
| Recommendation | run_id, ranked actions, expected gain, uncertainty, cost basis, stop reasons |
| MeasurementResult | action_id, actual observation, provenance, operator, quality, timestamp |
| Outcome | confirmation type, location/region, confirmation date, evidence reference, unresolved reason |

Constraints: retain original pipe IDs when simulation inserts leak nodes; invalid solver results never count as valid zero-flow observations; missing data is never silently replaced with zero. Reject conflicting duplicate observations and distinguish resampling from genuinely new observations. Do not double-count the same telemetry as independent evidence after re-import.

## 11. Inference and measurement-planning design

### 11.1 Hydraulic engine

Use EPANET/WNTR as the reference implementation. WNTR supports explicit leak simulation and pressure-dependent demand; simulator features differ and must be checked against imported controls. [S2]

For pipe leaks, introduce a leakage node on the candidate pipe using a documented transformation and retain a mapping to the original asset. Discretize candidate positions and leak severity for the initial ensemble. This discretization limits localization resolution and must be reported. Model leak discharge using the engine's supported pressure-dependent formulation with explicit coefficient and area assumptions.

Extended-period hydraulics is not an acoustic or high-frequency transient model. Pressure averaging and simulator time steps must match the investigation purpose.

### 11.2 Hypotheses and likelihood

Let H denote a leak/no-leak hypothesis and θ uncertain parameters such as demand multipliers, roughness, sensor bias, and boundary conditions. With observations D, estimate model-conditional weights:

`p(H, θ | D) ∝ p(D | H, θ) × p(H, θ)`

Start with weighted simulation ensembles and a documented residual likelihood. Estimate or specify sensor noise and account for correlated observations through an appropriate covariance approximation or time aggregation. Do not inflate confidence by treating strongly correlated readings as independent.

Marginalize nuisance parameters when scoring regions. Preserve no-leak probability and run adequacy checks for unsupported faults. In the MVP, a likely sensor fault or major operating mismatch can produce abstention rather than an overconfident fault classification.

An ensemble's normalized weights are conditional on its assumptions. Label scores accordingly until calibration is demonstrated on held-out cases.

### 11.3 Action selection

For each feasible action a, predict the distribution of possible observations y. Estimate expected information gain about the leak region:

`IG(a) = Entropy[p(H | D)] − E_y[Entropy[p(H | D, y, a)]]`

Use Monte Carlo or quadrature over plausible observations; never substitute the hidden true measurement when choosing an action. Integrate nuisance uncertainty in prediction while targeting uncertainty about H.

The initial planner maximizes IG subject to a fixed monetary/time budget. Show the cost–benefit tradeoff. If a weighted utility is introduced, normalize terms and publish weights; do not subtract arbitrary euros from entropy without a defined tradeoff. Later, an expected decision-loss objective may better represent operational cost.

MVP actions:

- Retrieve an available, not-yet-used permitted telemetry window.
- Collect an observational pressure reading at an approved point and time window.

Acoustic surveys, transient measurements, valve operations, and pump perturbations are excluded until a valid observation/intervention model exists. Waiting and collection time must be included; hypothetical measurements must not change the simulated physical system unless explicitly modeled.

### 11.4 Update and stop

After each genuine observation, update the ensemble and check fit. Stop when budget is exhausted, no valid action remains, predicted benefit is below a preregistered threshold, or all modeled explanations fit poorly. A candidate-region threshold can support an engineer's decision to hand off to conventional investigation; it must not automatically authorize excavation.

When the input network version changes, invalidate dependent recommendations and recompute. A measurement that contradicts all candidates should widen uncertainty or trigger model review, not force the closest pipe to win.

## 12. AI and agent architecture

Use a deterministic workflow with narrowly scoped model calls. Multiple autonomous agents are optional, not required for the product.

```text
INP + observations + permitted operational notes
                      ↓
Validation and versioned evidence store
                      ↓
Hydraulic scenario engine → hypothesis weights / adequacy checks
                      ↓
Feasible-action filter → numerical information-gain planner
                      ↓
Evidence-backed recommendation → engineer review
                      ↓
New observation → new versioned run
```

| Component | Responsibility | Authority limit |
|---|---|---|
| Constraint extraction assistant | Turn authorized notes into candidate access/time constraints with citations | User verifies extracted constraints before use |
| Scenario coordinator | Request schema-valid scenario batches | Cannot invent model elements or bypass bounds |
| Numerical planner | Compute weights, information gain, and cost tradeoffs | Uses validated tool outputs only |
| Report assistant | Explain alternatives and limitations in plain language | Cannot alter measurements, rankings, or approval status |
| Application controller | Manage job states, budgets, and audit trail | Cannot write to operational infrastructure |

Nemotron can be evaluated for constraint extraction and grounded explanation. Model/provider choice must be verified at implementation. Compare against form-based entry and templated reporting. Keep the LLM only where it improves measured usefulness, extraction accuracy, or analyst time.

Nebius Token Factory may host inference if an appropriate model is available and data routing is approved. The user's reported $50 Token Factory credit is not verified remaining balance and is not a GPU-compute allowance. CPU workers are the default for hydraulic simulation; GPU infrastructure is justified only by measured surrogate-training or inference needs. No model training is required for the MVP.

## 13. Proposed software architecture

These are proposed choices, not existing dependencies or implemented interfaces. Pin exact versions after a compatibility spike.

- **UI:** TypeScript/React, accessible forms, network graph, time-series charts.
- **API and analysis:** Python/FastAPI, WNTR, NumPy/SciPy, dataframe tooling.
- **Workers:** isolated CPU processes for simulation jobs; no shared mutable network objects.
- **Storage:** SQLite and local artifacts for research; PostgreSQL and object storage for a partner deployment.
- **Jobs:** persistent queued/running/completed/failed/cancelled states; bounded retries and cancellation.
- **Model interface:** replaceable structured-output adapter with deterministic fallback.
- **Packaging:** containerized local deployment first; tenant isolation before shared private-data hosting.

Proposed API resources: `POST /networks`, `POST /observation-imports`, `POST /investigations`, `POST /investigations/{id}/runs`, `GET /runs/{id}`, `POST /investigations/{id}/measurements`, and `GET /runs/{id}/export`. Long jobs return a job ID. Mutating requests use idempotency keys and authorization scoped to the workspace. Failures include stable error codes and user-actionable details.

Cache simulation results by complete physical configuration, engine version, and scenario hash. Never reuse a cache across incompatible demand, boundary, or network settings. Log numerical convergence separately from application errors.

## 14. Validation strategy: what can be proved

| Stage | Evidence obtainable | Claims still unavailable |
|---|---|---|
| Synthetic hidden-truth experiments | Planning improvement under specified simulator assumptions | Field accuracy and real crew savings |
| External public benchmarks | Performance on a published external test setting | Transfer to an unseen utility or unobserved actions |
| Historical partner replay | Fit and ranking using actually recorded observations | Outcome of a measurement nobody collected |
| Shadow pilot | Recommendation feasibility and agreement with later outcomes | Causal savings from following recommendations |
| Assisted prospective pilot | Operational outcomes under approved study design | Generalization beyond studied sites without further evidence |

### 14.1 Experimental protocol

1. Freeze network versions, scenario distributions, candidate actions, costs, noise, and metrics before final evaluation.
2. Separate the hidden-truth generator from the inference model. Perturb demands, roughness, leak positions, sensor calibration, and boundary assumptions rather than testing only identical forward/inverse models.
3. Split by incident/scenario family and time; do not randomly split adjacent readings from one event across training and test.
4. Report same-network and held-out-network results separately.
5. Include no-leak, sensor bias, missing data, demand changes, and unsupported multiple-leak cases.
6. Let every policy start with identical information and feasible actions. Reveal a measurement only after selection through an isolated evaluator.
7. Account for measurement cost, delay, simulation calls, wall time, and LLM spend.
8. Use scenario-level paired comparisons and confidence intervals. An initial suite should contain at least 100 held-out scenarios per network across two networks; revise sample size based on observed variance before strong claims.
9. Reproduce at least one public benchmark's official metrics separately from custom sequential-planning metrics. Do not present custom results as an official challenge score.

Cross-solver agreement is a numerical consistency check, not independent physical validation. Historical replay may reveal only recorded measurements. Simulating an unrecorded action remains simulation even when the initial observations were real.

### 14.2 Required baselines and ablations

- Random selection from the feasible action set, repeated across seeds.
- Lowest-cost feasible measurement.
- A practical sensitivity-based sensor-selection heuristic.
- Numerical expected-information-gain planner without an LLM.
- LeakProbe with constraint extraction and explanation enabled.
- An expert-authored plan if a partner supplies one; do not label a synthetic heuristic “expert.”

Primary comparisons should hold action costs and stopping rules constant. If LeakProbe's numerical planner is identical to the no-LLM baseline, numerical localization gains cannot be attributed to Nemotron. Assess model-assisted constraint handling and user time separately.

### 14.3 Metrics and proposed decision gates

All numerical thresholds below are provisional product targets, not achieved results. Freeze or revise them before examining final test outcomes.

| Metric | Definition | Proposed gate |
|---|---|---|
| Feasibility violations | Recommendations violating supplied hard constraints | Zero in deterministic acceptance suite |
| Candidate-set coverage | Fraction of supported leak cases whose true region is in the nominal 90% set | Report achieved coverage with interval; target at least 85% on held-out synthetic cases |
| Search cost | Total action cost to reach the preregistered useful region size | Target ≥15% lower than strongest practical non-agent baseline at comparable coverage; paired interval must support improvement |
| Region size | Pipe length or number of regions remaining | Report jointly with coverage; small inaccurate sets are failures |
| No-leak false localization | No-leak cases issued a confident leak-region recommendation | Provisional target ≤5%; report denominator and interval |
| Mismatch abstention | Unsupported/bad-fit cases correctly referred for review | Report by failure family, together with excessive abstention on supported cases |
| Reproducibility | Same inputs/seed reproduce numerical outputs within declared tolerance | 100% of deterministic fixture suite |
| Explanation grounding | Numeric statements match structured evidence | Zero unsupported numerical claims in export fixtures |
| Constraint extraction | Match to independently labeled constraints | Target ≥95% field-level accuracy; human confirmation remains required |
| Analyst utility | Time and correctness on structured tasks versus form/template baseline | Evaluate with partner users; no pretense of field validation from founder-only testing |

Use censoring/failure accounting for cases not localized within budget; do not drop them from averages. An oracle can provide a theoretical comparison bound but is never an attainable practical baseline.

## 15. Nonfunctional, security, and operational requirements

- Proposed local benchmark target: interactive cached results within five seconds and a fresh bounded analysis within five minutes at the MVP envelope on a documented eight-core CPU/16 GB RAM machine. Measure before committing to a service level.
- Every run has a simulation-call cap, wall-time limit, memory limit, and optional token-spend ceiling. Partial results are explicitly labeled.
- Failed simulations return diagnostics; no silent imputation or apparently successful recommendation.
- All imports are size-limited and validated. Models and notes are untrusted input; uploaded text cannot instruct the agent to access secrets or execute code.
- Research demo uses public/synthetic data only. Before private utility data, implement authenticated access, role checks, encrypted transport/storage, backup/restore tests, and deletion verification.
- Infrastructure topology and operational telemetry are treated as sensitive business data. Send only necessary pseudonymized structured context to inference providers, and only under agreed handling terms.
- Do not claim pseudonymization makes data anonymous. Do not train shared models on customer data without explicit permission.
- Retention period, deployment region, backup deletion delay, and model-provider retention must be documented in the pilot agreement. No compliance certification is implied.
- Audit upload, model version, run, approval, export, and deletion events. Keep secrets and raw telemetry out of application logs.
- Monitor convergence rate, run failures, latency, cache correctness, analysis cost, abstention rate, and observed calibration drift. Alerts go to the application operator; no automated field dispatch.

## 16. Delivery stages and resourcing

Estimates assume one experienced AI/software engineer working full time. They are planning ranges, not guarantees, and exclude waiting for partner access.

| Stage | Indicative effort | Deliverable | Exit condition |
|---|---|---|---|
| Discovery and data feasibility | 3–5 engineering days plus outreach | Confirm workflow, sample data, baseline, and intended user | A bounded problem and viable public simulation input |
| Hydraulic spike | 3–5 days | Network import, leak scenario, sensor predictions | Stable simulations and recorded limitations |
| Numerical vertical slice | 1–2 weeks | Hypothesis ensemble, next-action planner, measurement update | Reproducible end-to-end synthetic case and baselines |
| Research MVP | 1–2 weeks | UI, constraints, reports, evaluation harness | P0 acceptance suite and held-out results |
| Robustness and partner package | 1–2 weeks | Mismatch tests, model-assisted ablation, onboarding guide | Honest evidence report and explicit go/no-go |
| Partner validation | Partner-dependent | Replay, then prospective protocol if justified | Agreed operational evidence and buyer decision |

A hackathon slice can show one small network, one leak scenario, two competing hypotheses, a choice among a few measurements, and the resulting update. It must retain a visible “simulated” label and distinguish precomputed replay from live computation. That demo does not constitute the full research MVP.

Required outside expertise before a field pilot: a hydraulic modeler to review assumptions and a utility/contractor investigation owner to approve practical measurement procedures. Neither must be a full-time hire for the initial prototype.

## 17. Commercial hypothesis and discovery plan

Sell a bounded analysis project first: one district, fixed input package, agreed baselines, an evidence report, and no operational savings guarantee. A recurring license becomes credible only if the partner wants repeated investigations or model updates.

Potential packaging:

- Research workbench: local simulation and benchmarking for consultancies/research teams.
- Pilot project: onboarding and evaluation for one network area.
- Operational subscription: validated workflow, support, and agreed run/network limits.
- Embedded API: later, if a platform partner demonstrates demand.

No market size, price, conversion rate, or ROI is asserted. Price discovery should establish investigation frequency, staff cost, current tooling, budget owner, and willingness to pay for a measured improvement.

Use a customer-populated value model:

`Estimated annual net value = investigations/year × verified average avoided investigation cost − subscription − onboarding − incremental measurement/compute costs`

Keep water-loss savings separate unless a study supports causality. Report ranges and uncertainty, and avoid double-counting avoided crew time and costs that already include it.

Interview topics: what triggers investigations; how measurement points are chosen; most common model failures; available data and export rights; physical access constraints; typical unresolved cases; trusted evidence; current vendor capabilities; and who approves procurement. A credible initial commercial gate is one willing design partner with representative inputs and a named evaluator—not a list of large company logos.

## 18. Risks, mitigations, and stop conditions

| Risk | Mitigation | Stop/pivot condition |
|---|---|---|
| Inaccurate topology or operating state | Adequacy checks and uncertainty ensembles | Planner repeatedly confident under mismatch |
| Sparse sensors make regions indistinguishable | Return sets and abstain | Feasible observations do not meaningfully improve decisions |
| Synthetic success fails to transfer | Independent generator, robustness tests, then partner replay | No improvement on partner data |
| No access to utility collaborators | Research workbench scope and consultancy discovery | No viable route to representative evaluation |
| Existing software already solves the need | Direct workflow comparison | No meaningful user-valued advantage |
| LLM adds cost without value | Numerical baseline and structured UI | Remove LLM from critical path if ablation fails |
| Compute too slow | Caching, bounded hypotheses, adaptive fidelity | Surrogate complexity exceeds likely product value |
| Illegal/inaccessible measurements recommended | Validated action inventory and hard filtering | Any systematic feasibility violation blocks pilot |
| Sensitive infrastructure data mishandled | Local processing, access control, minimum disclosure | Partner requirements cannot be met |
| Claimed precision exceeds evidence | Coverage reporting, explicit provenance, abstention | No stable calibration even in bounded scope |

Proceed to a pilot only with a completed P0 suite, credible comparative results, documented limitations, data-handling agreement, and named partner engineering owner. Do not infer partner authorization from use of this PRD.

## 19. Engineering handoff appendix

The repository now contains a Python learning demo and benchmark tools in the `leakprobe/` package, with thin root-level command launchers for compatibility. They do not implement the full product described in this PRD. The layout and command contract below remain a proposed future architecture, not instructions claimed to work today.

```text
apps/web/                 browser application
services/api/             import and investigation API
packages/domain/          typed models, units, schemas
packages/hydraulics/      engine adapters and model transformations
packages/inference/       hypothesis weights and adequacy checks
packages/planning/        feasibility and action selection
packages/agents/          optional constrained model calls
evaluation/               hidden-truth runner, baselines, metrics
tests/                    unit, integration, regression, isolation tests
fixtures/                 small licensed synthetic fixtures
docs/                     PRD, assumptions, model cards, runbooks
```

Implementation should expose `make dev`, `make lint`, `make test`, `make test-integration`, `make benchmark-smoke`, and `make build`, with exact underlying commands documented when dependencies are pinned. Avoid inventing working package commands before scaffolding.

Style: typed Python at numerical boundaries, explicit SI units in names, immutable run inputs, structured errors, and typed frontend schemas. Example naming convention: `pressure_head_m`, `flow_m3_s`, `observed_at_utc`, `network_version_id`. Suggested domain record:

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class PressureObservation:
    sensor_id: str
    timestamp_utc: str
    pressure_head_m: float
    standard_deviation_m: float
```

Proposed testing stack: pytest for domain/numerical integration tests and browser end-to-end tests for import→recommendation→measurement→export. Use tolerance-based assertions for numerical outputs. Test unit conversions, impossible constraints, stale network versions, solver failure, no-leak cases, oracle isolation, and missing-data handling. Prioritize meaningful failure cases over blanket line-coverage targets.

Always preserve provenance, run relevant tests, and label simulated results. Obtain explicit authorization before operational integration or sharing private utility data with a new provider. Never expose hidden benchmark truth to the planner or promote a simulation result to a field claim.

## 20. Open decisions

1. Is the intended deliverable a hackathon demonstrator, research workbench, or customer pilot?
2. Which public model and data licenses will be selected for distribution?
3. Is any hydraulic adviser or prospective partner available?
4. Which region-size and investigation-cost thresholds matter to the target user?
5. Which confounders must be supported rather than handled through abstention?
6. Are actions limited to existing telemetry or can partner staff collect additional pressure readings?
7. What deployment and privacy constraints apply to real data?
8. Does measured LLM value justify provider integration?
9. What evidence would make a buyer replace or supplement their current workflow?

These questions do not prevent a public-data prototype. They do prevent presenting it as a validated operational product.

## 21. Definition of done

The research MVP is complete when an independent reviewer can import the documented example inputs; run a bounded investigation; inspect candidate regions and fit; select a feasible recommended measurement; ingest a separately sourced result; see the updated recommendation or abstention; export a reproducibility bundle; and reproduce a held-out comparison against the required baselines.

All P0 requirements must pass. Failed quality thresholds must be reported, not hidden. A technically complete MVP can still produce a commercial no-go decision.

## 22. Sources and evidence register

Sources checked 22 September 2026. Vendor statements establish described capabilities, not independent performance or exhaustive competitive coverage. All proposed architecture, requirements, targets, timelines, and commercial hypotheses in this document are product design judgments.

- **[S1] EPA — EPANET.** Hydraulic network modeling foundation. https://www.epa.gov/water-research/epanet
- **[S2] EPA WNTR — Hydraulic simulation.** Simulator differences, leak support, and pressure-dependent demand. https://usepa.github.io/WNTR/hydraulics.html
- **[S3] KIOS Research — LeakDB.** Artificial leakage benchmark and evaluation resources. https://github.com/KIOS-Research/LeakDB/blob/master/README.md
- **[S4] BattLeDIM — Challenge.** Hypothetical L-Town setting, observations, model uncertainty, dataset and evaluation links. https://battledim.ucy.ac.cy/?page_id=30
- **[S5] Xylem — Leak Detection application.** Vendor-described detection and localization capabilities. https://www.xylem.com/en-uk/resources/videos/leak-detection-application/
- **[S6] Bentley — OpenFlows WaterSight.** Vendor-described operational water twin and leak analytics capabilities. https://www.bentley.com/products/openflows-watersight
- **[S7] EPA WNTR — Advanced simulation techniques.** Stochastic leak-scenario simulation examples. https://usepa.github.io/WNTR/advancedsim.html

