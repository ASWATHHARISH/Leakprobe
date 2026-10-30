"""Employee operations over the existing detector, topology and baseline evidence."""
import pandas as pd
import sqlite3
import streamlit as st

from leakprobe.ui.ai_service import availability, run_investigation
from leakprobe.ui.alert_store import AlertStore, STATUSES
from leakprobe.ui.alert_queue import load_monitoring_queue
from leakprobe.ui.monitoring_records import render_monitoring_records
from leakprobe.ui.branding import render_product_header
from leakprobe.ui.data_access import (MONITORING_CASE_ID, load_monitoring_snapshot, load_network_layout,
                                     load_llm_trace_history)
from leakprobe.ui.monitoring import _reference_deviations
from leakprobe.ui.monitoring_views import (render_workspace_header, render_overview,
                                          render_sensors, render_prior_alerts)
from leakprobe.ui.operations import build_alert, matching_investigation, validate_feed
from leakprobe.employee_investigator import usage_summary
from leakprobe.investigation_report import ACTIONS, EXPLANATIONS, LIMITATIONS, audit_legacy_report, parse_legacy_sections


def _save_review(alert_id, store, prefix, acknowledge=False):
    """Persist before reporting success; callbacks refresh header and history together."""
    feedback_key = ("ack_feedback_" if acknowledge else "review_feedback_") + alert_id
    try:
        store.review(alert_id, "Acknowledged" if acknowledge else st.session_state[prefix + "_action"],
                     st.session_state[prefix + "_reviewer"],
                     "" if acknowledge else st.session_state[prefix + "_notes"])
        if acknowledge:
            st.session_state["review_" + alert_id + "_reviewer"] = st.session_state[prefix + "_reviewer"]
        st.session_state[feedback_key] = (True, "Review saved with a UTC timestamp.")
    except (ValueError, OSError, sqlite3.Error):
        st.session_state[feedback_key] = (False,
            "Review was not saved. Check your reviewer name and try again; if the problem persists, contact your administrator.")


def render_review(alert, store):
    st.subheader("Employee review")
    st.caption("Acknowledgment records receipt. Only a separate field review can confirm or rule out a leak. Automated assessments stay unchanged.")
    events = store.events(alert["alert_id"])
    reviews = [e for e in events if e["kind"] == "review"]
    latest = reviews[-1] if reviews else {}
    st.write(f"Review status: **{latest.get('status', 'New — requires attention')}**")
    if latest:
        st.caption(f"Last reviewed by {latest['reviewer']} · {latest['at']} (UTC)")
    prefix = "review_" + alert["alert_id"]
    with st.form(prefix):
        st.text_input("Reviewer name", value=latest.get("reviewer", ""), max_chars=120, key=prefix + "_reviewer")
        st.selectbox("Review action", STATUSES, key=prefix + "_action")
        st.text_area("Reviewer notes", max_chars=4000, key=prefix + "_notes",
                     placeholder="Record observations, checks performed and follow-up actions.")
        st.form_submit_button("Save review", on_click=_save_review, args=(alert["alert_id"], store, prefix))
    feedback = st.session_state.pop("review_feedback_" + alert["alert_id"], None)
    if feedback:
        (st.success if feedback[0] else st.error)(feedback[1])
    with st.expander("Timestamped event history", expanded=True):
        st.dataframe(pd.DataFrame([{"Time (UTC)": e["at"], "Event": e["kind"].replace("_", " ").title(),
                                    "Status": e.get("status", "Assessment recorded"),
                                    "Reviewer": e.get("reviewer", "—"), "Notes": e.get("notes", "")}
                                   for e in events]), use_container_width=True, hide_index=True)
    with st.expander("Technical audit details"):
        st.json(events)


def render_ai(alert, store, observations=None):
    st.subheader("AI Investigation · NVIDIA Nemotron")
    st.caption("Nemotron interprets sensor evidence. The physics detector generates the assessment independently.")
    ready, reason = availability()
    st.caption("Available on request" if ready else "AI investigation is currently unavailable. Saved reports can still be reviewed.")
    run = matching_investigation(load_llm_trace_history(), alert, observations)
    # Existing successful same-window traces are useful offline. No static explanation is substituted.
    if st.button("Run AI Investigation", disabled=not ready or store is None, type="primary"):
        with st.spinner("Nemotron is investigating the sensor evidence…"):
            try:
                run = run_investigation(alert, store)
            except (ValueError, OSError, sqlite3.Error) as exc:
                st.error(str(exc))
    st.caption("Runs only when requested. API charges may apply; saved investigations remain available without another request.")
    if not run:
        st.info("No investigation report is available for this record yet.")
        with st.expander("Technical tool trace"):
            st.caption(reason.replace("this demo window", "this monitoring window"))
            st.caption("On request only: up to 4 model requests, 8 tool calls and 2 attempts per alert. Context is bounded; no automatic retries.")
        return
    status = run.get("status", "incomplete")
    checked = (status == "completed" and run.get("validation_version") == "cited-facts-v1"
               and run.get("validation", {}).get("valid") and isinstance(run.get("report"), dict))
    if checked:
        report = run["report"]
        st.success("Completed · cited facts checked against tool evidence")
        st.write(report["summary"])
        lead = report["leading_candidate"]
        candidate = f"Pipe {lead['pipe']}" if lead["pipe"] else "Normal operation"
        st.caption(f"Leading fit: {candidate} · error {lead['fit_score']:.3f} · rank {lead['rank']}. Fit errors are not probabilities.")
        st.markdown("**Sensor evidence**")
        facts = run.get("evidence_facts", {})
        st.dataframe(pd.DataFrame([{"Sensor": row["channel"], "Observed value": row["value"], "Unit": row["unit"],
                                    "Sign": row["sign"], "Context": facts.get(row["fact_id"], {}).get("timestamp_utc",
                                                facts.get(row["fact_id"], {}).get("statistic", "Cited tool fact"))}
                                   for row in report["evidence"]]), hide_index=True, use_container_width=True)
        st.caption("Flow signs follow model pipe orientation; they do not establish leak outflow or physical direction on their own.")
        st.markdown("**Alternatives to consider**")
        st.dataframe(pd.DataFrame([{"Candidate": f"Pipe {row['pipe']}" if row["pipe"] else "Normal operation",
                                    "Rank": row["rank"], "Fit error": row["fit_score"]}
                                   for row in report["alternatives"]]), hide_index=True, use_container_width=True)
        st.write(" ".join(EXPLANATIONS[key] for key in report["possible_explanations"]))
        st.markdown("**Uncertainty**")
        st.write(" ".join(LIMITATIONS[key] for key in report["uncertainty"]))
        st.markdown("**Recommended field actions**")
        st.markdown("\n".join(f"{index}. {ACTIONS[key]}" for index, key in enumerate(report["actions"], 1)))
        st.caption("Cited measurements and rankings are checked. Possible causes and field outcomes are not independently verified.")
    else:
        audit = (audit_legacy_report(run.get("answer", ""), observations, alert.get("comparison_signature")) if observations is not None
                 and run.get("validation_version") != "cited-facts-v1" else run.get("validation", {}))
        if status == "completed":
            st.warning("Saved model response · not fully evidence-validated")
        else:
            st.warning(f"Investigation {status.replace('_', ' ')} · no completed, validated report")
        if audit.get("errors"):
            st.caption("Evidence checks: " + "; ".join(audit["errors"][:3]))
        if audit.get("sections_found") and not audit.get("missing_sections"):
            st.caption("All six content sections are present. Formatting alone does not establish factual correctness.")
        sections = parse_legacy_sections(run.get("answer", ""))
        summary = sections.get("Investigation summary", "")
        if summary:
            st.markdown("**Draft summary · unvalidated**")
            st.write(summary if len(summary) <= 350 else summary[:347].rsplit(" ", 1)[0] + "…")
        if run.get("error"):
            with st.expander("Completion details"):
                st.write(run["error"])
        if run.get("answer"):
            with st.expander("Original model response · unvalidated"):
                st.markdown(run["answer"])
    totals = usage_summary(run)
    token_label = f"{totals['total_tokens']:,} reported tokens" if totals["usage_reported_for_requests"] else "token usage not reported"
    cost_label = "provider cost information available in trace" if totals["provider_cost_info"] else "cost not reported by provider"
    with st.expander("Technical tool trace"):
        st.caption(reason.replace("this demo window", "this monitoring window"))
        st.caption(f"{totals['requests']} recorded requests · {token_label} · {cost_label}")
        st.caption("On request only: up to 4 model requests, 8 tool calls and 2 attempts per alert. Context is bounded; no automatic retries.")
        st.caption(f"Model: {run.get('model', 'not recorded in legacy trace')} · Saved: {run.get('saved_at_utc', 'not recorded')}")
        st.json({"validation": run.get("validation", {}), "request_receipts": run.get("requests", []),
                 "usage_summary": totals})
        for index, step in enumerate(run.get("trace", []), 1):
            st.write(f"{index}. {step.get('tool', 'unknown')}")
            st.json(step)
        st.json({"usage": run.get("usage", []), "budget": run.get("budget", {})})
        if observations is not None:
            st.download_button("Download full sensor readings", observations.to_csv(index=False),
                               file_name=f"{alert['case_id']}_sensor_readings.csv", mime="text/csv")



def render_monitoring_dashboard():
    render_product_header(compact=True)
    # Styles apply only when this page is rendered. Keep controls responsive and readable.
    st.markdown("""<style>
    .block-container [data-baseweb="tab-list"] { gap: .25rem; flex-wrap: wrap; height: auto; }
    .block-container [data-baseweb="tab"] { padding: .45rem .75rem; height: auto; }
    .block-container [data-testid="stMetricValue"] { font-size: 1.25rem; }
    </style>""", unsafe_allow_html=True)
    store = None
    try:
        store = AlertStore()
    except (OSError, sqlite3.Error):
        st.warning("Review storage unavailable. Monitoring remains read-only.")
    try:
        with st.spinner("Loading monitoring records and alert assessments…"):
            queue = load_monitoring_queue()
        try:
            selected = render_monitoring_records(queue, store, MONITORING_CASE_ID)
        except (OSError, sqlite3.Error):
            st.warning("Review storage unavailable. Monitoring remains read-only.")
            store = None
            selected = render_monitoring_records(queue, None, MONITORING_CASE_ID)
        if selected is None:
            return
        snapshot = load_monitoring_snapshot(selected)
        observations = snapshot["observations"]
        quality = validate_feed(observations, snapshot["metadata"], snapshot["normal_profiles"])
        layout = load_network_layout()
        alert = build_alert(snapshot)
    except (OSError, ValueError, KeyError, ImportError) as exc:
        st.error(f"Monitoring unavailable: {exc}")
        st.info("Restore an aligned, complete sensor window before interpreting an alert.")
        return
    decision = snapshot["comparison"]["decision"]
    try:
        if store is not None and decision["prediction"] != "normal":
            store.register(alert)
        render_workspace_header(selected, alert, quality, store, _save_review)
    except (OSError, sqlite3.Error):
        st.warning("Review storage unavailable. Monitoring remains read-only.")
        store = None
        render_workspace_header(selected, alert, quality, None, _save_review)
    rows, affected_counts = [], {}
    for group in ("pressure", "flow"):
        affected, _, evidence = _reference_deviations(observations, snapshot["normal_profiles"], group)
        affected_counts[group] = affected
        rows.extend(evidence)
    rows.sort(key=lambda row: row["Readings outside reference"], reverse=True)
    overview, ai, sensors, review = st.tabs(["Overview", "AI Investigation", "Sensor Analysis", "Employee Review"])
    with overview:
        render_overview(snapshot, alert, layout, rows, affected_counts)
    with ai:
        # Tabs render eagerly. Only the explicit button inside render_ai can request inference.
        render_ai(alert, store if decision["prediction"] != "normal" else None, observations)
    with sensors:
        render_sensors(snapshot, quality, rows)
    with review:
        if store is None:
            st.info("Review storage unavailable. Reviews cannot be saved right now.")
        elif decision["prediction"] == "normal":
            st.info("No alert requires acknowledgment for this record.")
        else:
            render_review(alert, store)
        if store is not None:
            render_prior_alerts(alert, store)
