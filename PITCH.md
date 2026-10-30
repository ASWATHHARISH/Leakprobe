# LeakProbe: Pitch Brief

## 1. Problem

Water utilities need to detect leaks and narrow down their locations across large pipe networks. Pressure and flow readings can be ambiguous: different leaks, demand changes, and operating conditions can produce similar observations. That can delay repairs and send field crews to investigate the wrong places.

Leaks waste treated water and the energy and chemicals used to produce it. They can also reduce utility revenue and create water-quality concerns. The US EPA describes these as consequences of distribution-system leaks and breaks. [EPA overview](https://www.epa.gov/dwreginfo/drinking-water-distribution-system-tools-and-resources)

**Business value:** LeakProbe aims to reduce the time and field effort needed to investigate a suspected leak. A pilot should measure value in confirmed leak volume, time from alert to repair, crew hours, and cost per confirmed leak. Those savings have not yet been demonstrated by this prototype.

## 2. What LeakProbe does

LeakProbe is a **hydraulic-model-based leak investigation prototype**:

- It uses a water-network model and pressure/flow time-series observations.
- The app uses the canonical full-channel high-signal Net3 dataset: 92 pressure channels and 117 flow channels in each case. A separate 1,000-case classifier experiment is available for sample-size comparison.
- It compares observations against reference patterns for normal operation and candidate leak locations, ranking scenarios by normalized error.
- It ranks normal and leak scenarios by fit error. The score is not a probability, and the active high-signal dataset has no calibrated rejection threshold.
- Its agent can call Python tools to retrieve the complete observation feed and network information, then compare hypotheses using all channels.
- The LLM coordinates and explains tool use; the underlying scenario scoring is deterministic Python logic, not a trained LLM leak classifier.

The current demo uses the WNTR/EPANET Net3 benchmark and generated experimental data. It is a batch prototype, not a live utility monitoring system.

## 3. Why use LeakProbe

LeakProbe is intended to help an operator move from **“something looks wrong”** to **“these locations best fit the measurements; here is the next useful measurement to collect.”** Its focus is investigation support: rank candidate pipes, show why they fit, and guide follow-up measurements.

That could help utilities prioritize field investigations and avoid low-value visits. The business case should be tested against the utility’s current process and measured using operational outcomes, rather than assumed from model scores.

## 4. Why an LLM, and why Nemotron

The hydraulic analysis should determine which network patterns best match the readings. An LLM is required for the natural-language investigation assistant, not for the numerical leak score. A fixed alert can run without it. The assistant experience uses the LLM to coordinate a bounded sequence of analysis tools, then explain the returned evidence in plain language: what pattern ranked first, how it compared with normal operation, what the fit score means, and what should be checked next.

In the current prototype, the LLM can call allowlisted Python tools to retrieve the full feed and network details and run the deterministic scenario comparison. The app saves the tool calls and results so an analyst can review how the explanation was produced. The model does not calculate the hydraulic fit score, change sensor readings, confirm a physical leak, or issue field instructions.

The LLM is intended to turn a technical ranking into a useful investigation handoff. As the workflow grows, it could also help interpret operator questions and summarize maintenance notes or event records alongside the numerical results. Those extensions need their own validation. Reduced analyst effort and improved handoff quality have not yet been measured; saved explanations can contain errors and need evidence review.

The prototype currently configures **NVIDIA Nemotron 3 Super 120B A12B** through **Nebius Token Factory**. NVIDIA describes this model for agentic reasoning and tool use, which match the coordination task in LeakProbe. Nebius provides an OpenAI-compatible API, so the prototype can use its existing client interface to call the model. Nemotron's open-weight availability also leaves a possible self-hosting path if future operational requirements justify the deployment and licensing work. Nemotron is a model choice for evaluation [NVIDIA model documentation](https://docs.api.nvidia.com/nim/reference/nvidia-nemotron-3-super-120b-a12b) · [Nebius Token Factory Nemotron documentation](https://nebius.com/services/token-factory/models/nvidia-nemotron-models-inference)

## 5. Other companies in this market

- **Xylem** — Xylem Vue includes leak-detection and water-network analytics applications. [Xylem Vue](https://www.xylem.com/en-us/catalog/products--services/digital-water/xylem-vue/)
- **Bentley Systems** — OpenFlows Water and OpenFlows WaterSight provide water-network hydraulic modeling and digital-twin capabilities, including leak and anomaly detection. [OpenFlows Water](https://www.bentley.com/products/openflows-water/) · [OpenFlows WaterSight](https://www.bentley.com/products/openflows-watersight/)

## 6. Why LeakProbe could stand out, and how to scale it

The promising product direction is an **operator-facing investigation assistant** that combines hydraulic scenario ranking, explicit uncertainty, and guidance on what to measure next. That is a positioning opportunity, not yet a proven market advantage.

The high-signal cases use deliberately large, long leaks and matching demand ranges across development and test. They are a controlled benchmark for comparing precision and recall, not evidence of field performance. See the saved full-channel classifier report for the current held-out results.

To build a credible product:

1. Validate the model and scoring approach against measured utility data, including confirmed leaks and normal operating periods.
2. Improve leak detection and pipe localization separately, and test across different networks and operating conditions.
3. Add production integrations for SCADA, GIS, and work-order systems, with data-quality checks and traceable recommendations.
4. Run a shadow pilot alongside the utility’s existing process. Compare detection time, field effort, false alarms, missed leaks, and cost per confirmed leak.
5. Make scale-up and commercial claims only after independent pilots show reliable performance and measurable operational value.
