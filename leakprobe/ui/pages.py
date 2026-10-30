"""Streamlit pages over the complete Net3 sensor feed and saved results."""
import json

import pandas as pd
import streamlit as st
from leakprobe.ui.layout import STRETCH

from leakprobe.ui.branding import render_product_header
from leakprobe.ui.charts import rate_chart_spec
from leakprobe.ui.investigation_history import saved_comparison, is_validated_report
from leakprobe.employee_investigator import usage_summary
from leakprobe.ui.data_access import (
    load_benchmark_case_history,
    load_llm_trace_history,
    load_report,
)


def _run_comparison(saved_run: dict) -> dict | None:
    return saved_comparison(saved_run)


def _render_benchmark_case_history() -> None:
    st.divider()
    st.subheader(
        "Held-out classifier case history",
        help=(
            "Shows every held-out case already evaluated by the baseline, class-weighted, and "
            "SMOTE classifiers. These are saved classifier results, separate from the LLM run traces above."
        ),
    )
    st.caption(
        "Choose a benchmark size to review each test case, its reference outcome, and the three "
        "classifier alerts. Training cases are excluded."
    )
    benchmark_name = st.selectbox(
        "Benchmark case set",
        options=("500 cases · 100 held-out", "1,000 cases · 200 held-out"),
        key="history_benchmark_case_set",
        help="Select the saved benchmark whose held-out case results you want to inspect.",
    )
    try:
        history = load_benchmark_case_history(benchmark_name)
    except (OSError, ValueError, KeyError) as exc:
        st.error(f"Could not load the saved classifier case history: {exc}")
        return

    if history.empty:
        st.info("No held-out case results are saved for this benchmark.")
        return

    leak_count = int((history["Reference outcome"] == "Leak").sum())
    normal_count = len(history) - leak_count
    st.caption(
        f"{len(history)} held-out cases · {leak_count} leak cases · {normal_count} normal cases · "
        "92 pressure + 117 flow channels"
    )
    st.dataframe(
        history,
        hide_index=True,
        **STRETCH,
        height=520,
        column_config={
            "Case": st.column_config.TextColumn(
                help="Identifier of a held-out test case."
            ),
            "Reference outcome": st.column_config.TextColumn(
                help="The saved correct label for this case: leak or normal operation."
            ),
            "Baseline alert": st.column_config.TextColumn(
                help="Whether the baseline classifier's chosen threshold produced a leak alert."
            ),
            "Baseline leak score": st.column_config.TextColumn(
                help="Model-assigned leak score, shown as a percentage. It is not guaranteed to be calibrated."
            ),
            "Class-weighted alert": st.column_config.TextColumn(
                help="Whether the class-weighted classifier's chosen threshold produced a leak alert."
            ),
            "Class-weighted leak score": st.column_config.TextColumn(
                help="Model-assigned leak score, shown as a percentage. It is not guaranteed to be calibrated."
            ),
            "SMOTE alert": st.column_config.TextColumn(
                help="Whether the SMOTE classifier's chosen threshold produced a leak alert."
            ),
            "SMOTE leak score": st.column_config.TextColumn(
                help="Model-assigned leak score, shown as a percentage. It is not guaranteed to be calibrated."
            ),
        },
    )


def render_llm_run_history() -> None:
    render_product_header()
    st.header(
        "Investigation history",
        help=(
            "Browse saved investigation runs, their pattern comparisons, optional LLM summaries, "
            "and the recorded sequence of analysis-tool calls."
        ),
    )
    st.write("Browse saved Net3 investigations and open each run's result and tool trace.")
    st.caption("This page reads local trace files. Opening a saved run does not call the provider.")
    try:
        saved_runs = load_llm_trace_history()
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        st.error(f"Could not read the saved LLM run history: {exc}")
        _render_benchmark_case_history()
        return
    if not saved_runs:
        st.info("No Net3 LLM runs are saved. Run `python run_demo.py` to create one.")
        _render_benchmark_case_history()
        return

    history_rows = []
    for run in saved_runs:
        comparison = _run_comparison(run)
        ranking = comparison["ranking"] if comparison else []
        winner = ranking[0] if ranking else {}
        totals = usage_summary(run)
        history_rows.append({
            "Saved at (UTC)": run["saved_at_utc"],
            "Case": run.get("case_id") or "—",
            "Status": run.get("status", "unknown").title(),
            "Leading fit": winner.get("scenario", "—").replace("leak_pipe:", "Pipe "),
            "Best fit error": winner.get("normalized_rmse"),
            "Evidence validation": "Validated" if is_validated_report(run) else "Not validated",
            "LLM requests": totals["requests"],
            "Reported tokens": totals["total_tokens"],
        })
    st.subheader(
        "Run history",
        help="A list of saved investigations, their case, outcome status, leading pattern, and run usage.",
    )
    st.dataframe(
        pd.DataFrame(history_rows), hide_index=True, **STRETCH,
        column_config={
            "Saved at (UTC)": st.column_config.TextColumn(
                help="Time when this investigation was saved, shown in Coordinated Universal Time."
            ),
            "Case": st.column_config.TextColumn(
                help="Identifier of the sensor-feed case used in the investigation."
            ),
            "Status": st.column_config.TextColumn(
                help="Whether the saved investigation completed or stopped before completion."
            ),
            "Leading fit": st.column_config.TextColumn(
                help="The normal or pipe-specific pattern ranked closest to the feed."
            ),
            "Best fit error": st.column_config.NumberColumn(
                format="%.3f",
                help="Normalized mismatch for the leading pattern. Lower is closer; this is not a probability."
            ),
            "LLM requests": st.column_config.NumberColumn(
                help="Number of calls to the language-model provider. This does not count analysis-tool calls or expose the model's private internal reasoning."
            ),
            "Reported tokens": st.column_config.NumberColumn(
                help="Total input and output tokens reported for the language-model requests."
            ),
        },
    )

    selected_index = st.selectbox(
        "Open a saved run",
        options=list(range(len(saved_runs))),
        index=next((i for i, run in enumerate(saved_runs) if is_validated_report(run)), 0),
        format_func=lambda index: (
            f"{saved_runs[index].get('case_id') or 'Unknown case'} · "
            f"{saved_runs[index]['saved_at_utc']} · "
            f"{saved_runs[index].get('status', 'unknown').title()}"
        ),
        key="saved_llm_run_selector",
        help="Choose which saved investigation to open below. This reads its saved trace and does not start a new provider request.",
    )
    saved_run = saved_runs[selected_index]
    status = saved_run.get("status", "unknown")
    if status != "completed":
        st.warning(f"The saved run status is **{status}**; review its result as incomplete.")
    elif not is_validated_report(saved_run):
        st.warning("Saved response completed · not fully evidence-validated. Review as an unvalidated interpretation.")
    else:
        st.success("Completed · cited facts checked against tool evidence")
    tool_history = saved_run.get("trace", [])
    totals = usage_summary(saved_run)
    total_tokens = totals["total_tokens"]
    summary = st.columns(4)
    summary[0].metric(
        "Case",
        saved_run.get("case_id") or "—",
        help="Identifier of the sensor-feed case used by this saved run.",
    )
    summary[1].metric(
        "Run status",
        status.title(),
        help="Whether the saved investigation completed or ended early.",
    )
    summary[2].metric(
        "LLM requests",
        totals["requests"],
        help=(
            "Number of calls to the language-model provider. This does not count the separate "
            "analysis-tool steps or expose the model's private internal reasoning."
        ),
    )
    summary[3].metric(
        "Reported tokens",
        f"{total_tokens:,}",
        help="Total input and output tokens reported by the language-model provider for this run.",
    )

    comparison = _run_comparison(saved_run)
    if comparison and comparison["ranking"]:
        st.subheader(
            "Full-channel comparison",
            help=(
                "Ranks the stored normal and leak patterns against the complete 92-pressure, "
                "117-flow feed. The comparison score is an error value, not a probability."
            ),
        )
        rows = [
            {"Rank": row["rank"], "Scenario": row["scenario"], "Pipe": row["leak_pipe"] or "—",
             "Normalized fit score": row["normalized_rmse"]}
            for row in comparison["ranking"]
        ]
        st.dataframe(
            pd.DataFrame(rows), hide_index=True, **STRETCH,
            column_config={
                "Rank": st.column_config.NumberColumn(
                    help="Position in the list, ordered from the closest fit upward."
                ),
                "Scenario": st.column_config.TextColumn(
                    help="The stored normal-operation or pipe-specific leak pattern being compared."
                ),
                "Pipe": st.column_config.TextColumn(
                    help="Pipe associated with a leak pattern; a dash means this row is normal operation."
                ),
                "Normalized fit score": st.column_config.NumberColumn(
                    format="%.3f",
                    help="Normalized mismatch between this pattern and the feed. Lower is closer; it is not a probability."
                ),
            },
        )
        st.caption(comparison["score_meaning"])
    if comparison and comparison["skipped_rows"]:
        st.warning("Some saved comparison rows could not be read. Original tool data remains available below.")

    answer = saved_run.get("answer")
    if answer:
        st.subheader(
            "LLM interpretation",
            help="A saved plain-language summary produced for this run. It explains tool results but does not change the detector's comparison.",
        )
        if is_validated_report(saved_run):
            st.write(saved_run["report"]["summary"])
            with st.expander("Full validated investigation"):
                st.markdown(answer)
        else:
            st.caption("This response is not a validated conclusion. Its original contents are preserved below.")
            with st.expander("Original response · unvalidated", expanded=False):
                st.markdown(answer)
    else:
        st.info("The saved run has no final written interpretation.")

    with st.expander("Tool steps", icon=":material/info:"):
        st.caption(
            "The ordered analysis-tool calls recorded during this saved investigation. "
            "Opening the trace does not execute the tools again."
        )
        history = [{"Step": row.get("tool", "unknown").replace("_", " ").title()}
                   for row in tool_history]
        st.dataframe(
            pd.DataFrame(history),
            hide_index=True,
            **STRETCH,
            column_config={
                "Step": st.column_config.TextColumn(
                    help="Name of the analysis tool called at this step."
                )
            },
        )
        st.caption(f"Trace file: `{saved_run['trace_file']}`")
        st.json({"trace": tool_history, "validation": saved_run.get("validation", {}),
                 "usage_summary": totals})

    _render_benchmark_case_history()


def render_benchmarks() -> None:
    render_product_header()
    st.header(
        "Model validation",
        help=(
            "Compare the held-out scores of three ways of training the same leak classifier: "
            "baseline, class-weighted, and SMOTE."
        ),
    )
    st.write("Compare baseline, class-weighted, and SMOTE results on complete sensor feeds.")
    report_name = "High-signal Net3"
    try:
        report = load_report(report_name)
    except (OSError, ValueError, KeyError) as exc:
        st.error(f"Could not load the saved benchmark report: {exc}")
        return

    st.caption("High-signal Net3 validation · see About for evaluation conditions and limitations.")
    st.caption(
        f"Positive class: leak · {report['pressure_channel_count']} pressure + "
        f"{report['flow_channel_count']} flow channels · Development threshold target: "
        f"{report['target_leak_recall']:.0%} recall · Test cases: "
        f"{report['test_counts']['leak']} leaks, {report['test_counts']['normal']} normal",
        help=(
            "Leak is treated as the positive result when calculating scores. The development "
            "recall target is used to choose the alert threshold before final evaluation on the "
            "held-out test cases."
        ),
    )
    rows = []
    for name, variant in report["variants"].items():
        score = variant["held_out_test"]
        matrix = score["confusion_matrix"]
        rows.append({
            "Variant": name.replace("_", " ").title(),
            "Leak precision": score["leak_precision"],
            "Leak recall": score["leak_recall"],
            "Balanced accuracy": score["balanced_accuracy"],
            "TP leaks caught": matrix["tp_leak"],
            "FN leaks missed": matrix["fn_leak"],
            "FP false alarms": matrix["fp_false_alarm"],
            "TN normal cleared": matrix["tn_normal"],
        })
    scores = pd.DataFrame(rows)
    precision_col, recall_col = st.columns(2)
    with precision_col:
        st.subheader(
            "Leak precision",
            help=(
                "Of the cases a classifier flags as leaks, the share that are actually labeled "
                "leaks in this test set. Higher precision means fewer false alarms."
            ),
        )
        st.vega_lite_chart(None, rate_chart_spec(scores, "Leak precision"), **STRETCH)
    with recall_col:
        st.subheader(
            "Leak recall",
            help=(
                "Of the actual leak cases in this test set, the share that a classifier catches. "
                "Higher recall means fewer missed leaks."
            ),
        )
        st.vega_lite_chart(None, rate_chart_spec(scores, "Leak recall"), **STRETCH)
    st.subheader(
        "Held-out test results",
        help=(
            "Final comparison on cases kept out of model training and threshold selection. "
            "Use these results as the main benchmark comparison."
        ),
    )
    st.dataframe(
        scores, hide_index=True, **STRETCH,
        column_config={
            "Variant": st.column_config.TextColumn(
                help="Training approach used for this version of the leak classifier."
            ),
            "Leak precision": st.column_config.NumberColumn(
                format="percent",
                help="Among alerts labeled leak, the fraction that are actual leaks. Higher means fewer false alarms.",
            ),
            "Leak recall": st.column_config.NumberColumn(
                format="percent",
                help="Among actual leaks, the fraction flagged by the classifier. Higher means fewer missed leaks.",
            ),
            "Balanced accuracy": st.column_config.NumberColumn(
                format="percent",
                help="Average of the classifier's correct-leak rate and correct-normal rate; it gives both classes equal weight.",
            ),
            "TP leaks caught": st.column_config.NumberColumn(
                help="True positives: leak cases correctly flagged as leaks."
            ),
            "FN leaks missed": st.column_config.NumberColumn(
                help="False negatives: actual leak cases incorrectly left unflagged."
            ),
            "FP false alarms": st.column_config.NumberColumn(
                help="False positives: normal cases incorrectly flagged as leaks."
            ),
            "TN normal cleared": st.column_config.NumberColumn(
                help="True negatives: normal cases correctly left unflagged."
            ),
        },
    )
    with st.expander(
        "Development cross-validation and in-sample results",
        icon=":material/info:",
    ):
        st.caption(
            "Cross-validation repeatedly trains on part of the development set and checks held-aside "
            "development cases to choose a threshold. In-sample scores reuse training cases and are "
            "optimistic diagnostics; the held-out test table remains the main result."
        )
        development_rows = []
        for name, variant in report["variants"].items():
            score = variant["development_oof"]
            development_rows.append({
                "Variant": name.replace("_", " ").title(),
                "Threshold": variant["threshold"],
                "Leak precision": score["leak_precision"],
                "Leak recall": score["leak_recall"],
                "Balanced accuracy": score["balanced_accuracy"],
            })
        st.dataframe(
            pd.DataFrame(development_rows), hide_index=True, **STRETCH,
            column_config={
                "Variant": st.column_config.TextColumn(
                    help="Training approach used for this version of the leak classifier."
                ),
                "Threshold": st.column_config.NumberColumn(
                    format="%.3f",
                    help="Decision cutoff selected using held-aside development predictions."
                ),
                "Leak precision": st.column_config.NumberColumn(
                    format="percent",
                    help="Among development cases flagged as leaks, the fraction labeled as leaks."
                ),
                "Leak recall": st.column_config.NumberColumn(
                    format="percent",
                    help="Among development leaks, the fraction caught at this threshold."
                ),
                "Balanced accuracy": st.column_config.NumberColumn(
                    format="percent",
                    help="Average of the development leak-catch rate and normal-clearance rate."
                ),
            },
        )
        in_sample_rows = []
        for name, variant in report.get("development_in_sample", {}).items():
            score = variant["in_sample"]
            in_sample_rows.append({
                "Variant": name.replace("_", " ").title(),
                "Leak precision": score["leak_precision"],
                "Leak recall": score["leak_recall"],
                "Balanced accuracy": score["balanced_accuracy"],
            })
        if in_sample_rows:
            st.subheader(
                "In-sample training scores (optimistic diagnostic)",
                help=(
                    "Scores calculated on cases used to fit the classifier. They tend to look "
                    "better than performance on new cases, so use only as a training diagnostic."
                ),
            )
            st.dataframe(
                pd.DataFrame(in_sample_rows),
                hide_index=True,
                **STRETCH,
                column_config={
                    "Variant": st.column_config.TextColumn(
                        help="Training approach used for this version of the leak classifier."
                    ),
                    "Leak precision": st.column_config.NumberColumn(
                        format="percent",
                        help="Among training cases flagged as leaks, the fraction labeled as leaks."
                    ),
                    "Leak recall": st.column_config.NumberColumn(
                        format="percent",
                        help="Among training leaks, the fraction caught."
                    ),
                    "Balanced accuracy": st.column_config.NumberColumn(
                        format="percent",
                        help="Average of training leak-catch rate and normal-clearance rate."
                    ),
                },
            )
        st.caption(
            "In-sample scores evaluate cases used for training. Use the held-out table as the main comparison.",
            help="The classifier has already seen these cases while fitting, so these scores can overstate performance on new feeds.",
        )


def render_about() -> None:
    from leakprobe.ui.branding import render_compact_style

    render_compact_style()
    st.title("LeakProbe")
    st.caption("Water Leak Detection & Investigation")
    st.header("About LeakProbe")
    st.write(
        "LeakProbe is a water network monitoring and investigation platform designed to help operators "
        "identify potential leaks, understand unusual pressure and flow patterns, and take informed action."
    )
    st.write(
        "By bringing network monitoring, leak alerts, investigation insights, and review history into "
        "one place, LeakProbe helps teams investigate potential problems more efficiently."
    )

    st.divider()
    st.subheader("What LeakProbe Does")
    features = (
        ("Network Monitoring", "Monitor pressure and flow readings across the water network and identify unusual operating patterns."),
        ("Leak Detection", "Identify suspected leaks and highlight the most likely affected pipes based on available sensor evidence."),
        ("Intelligent Investigation", "Review evidence-based explanations, understand possible causes, and receive recommended next steps for verification."),
        ("Alert Management", "Acknowledge alerts, record findings, and maintain an investigation history for future reference."),
    )
    for start in (0, 2):
        columns = st.columns(2)
        for column, (title, description) in zip(columns, features[start:start + 2]):
            with column:
                with st.container(border=True):
                    st.markdown(f"**{title}**")
                    st.write(description)

    st.divider()
    st.subheader("How LeakProbe Works")
    st.markdown(
        "1. **Monitor:** LeakProbe checks incoming network readings.\n"
        "2. **Detect:** Unusual patterns are analyzed to identify potential leaks.\n"
        "3. **Investigate:** Employees review candidate locations, supporting evidence, and investigation recommendations.\n"
        "4. **Review:** Employees acknowledge alerts and record their findings."
    )

    st.divider()
    st.subheader("Understanding Alerts")
    # Match the labels in the employee alert queue; do not introduce new detector states.
    st.markdown(
        "- **Suspected leak:** An abnormal pattern suggests a possible leak that requires verification.\n"
        "- **No alert:** The current assessment has not identified a leak requiring attention.\n"
        "- **Review required:** Available evidence or data quality is insufficient for a clear assessment."
    )

    st.divider()
    st.subheader("Product Scope")
    st.caption(
        "Current feed: Net3 demonstration data. See the "
        "[technical documentation](https://github.com/drkrishnan8109/LeakProbe/blob/main/docs/STREAMLIT_FRONTEND_README.md#current-limits) "
        "for evaluation limitations."
    )
