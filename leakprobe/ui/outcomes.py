"""After-action view of the held-out monitoring outcomes."""
import pandas as pd
import streamlit as st
from leakprobe.ui.layout import STRETCH

from leakprobe.ui.branding import render_product_header
from leakprobe.ui.data_access import load_outcome_records


def render_reference_outcomes() -> None:
    records = load_outcome_records()
    outcomes = pd.DataFrame(records)
    leak_count = int((outcomes["Reference outcome"] == "Leak").sum())
    normal_count = int((outcomes["Reference outcome"] == "Normal").sum())

    render_product_header()
    st.caption("Reference outcomes for validation, separate from employee assessments.")
    st.header(
        "Reference outcomes",
        help=(
            "Reference outcomes for validation, kept separate from automated alerts and employee reviews."
        ),
    )
    st.write("Compare completed assessments with the recorded reference outcomes. These records are kept out of alert generation.")
    metrics = st.columns(3)
    metrics[0].metric(
        "Leak references",
        leak_count,
        help="Number of reference records labeled leak.",
    )
    metrics[1].metric(
        "Normal references",
        normal_count,
        help="Number of reference records labeled normal operation.",
    )
    metrics[2].metric(
        "Reference records",
        len(outcomes),
        help="Total number of reference records available for validation.",
    )
    st.dataframe(
        outcomes,
        hide_index=True,
        **STRETCH,
        column_config={
            "Window": st.column_config.TextColumn(
                help="Identifier of the monitoring window that was assessed."
            ),
            "Reference outcome": st.column_config.TextColumn(
                help="Recorded reference label used to review the alert after the assessment."
            ),
            "Reference pipe": st.column_config.TextColumn(
                help="Pipe listed in the stored outcome for a confirmed leak; a dash means there is no leak pipe."
            ),
        },
    )
    st.caption(
        "Outcomes are shown here for after-action review. The monitoring alert is computed without reading the outcome label.",
        help=(
            "Keeping the outcome label out of the alert calculation prevents the answer from "
            "being used as an input to its own assessment."
        ),
    )


def render_outcome_review():
    from leakprobe.ui.alert_store import AlertStore
    from leakprobe.ui.alert_queue import record_name
    from leakprobe.ui.runtime_settings import demo_mode
    import sqlite3

    render_product_header()
    st.header("Alert history & employee reviews")
    st.caption("Employee assessments, verification notes and timestamped investigation history.")
    if demo_mode():
        st.caption("Showing reviews from this demo session only. A new session or app restart resets them.")
    try:
        store = AlertStore()
        alerts = store.alerts()
        if not alerts:
            st.info("No alerts have been reviewed yet. Open Monitoring to select an alert and record your assessment.")
            return
        rows = []
        for alert in alerts:
            reviews = [e for e in store.events(alert["alert_id"]) if e["kind"] == "review"]
            latest = reviews[-1] if reviews else {}
            rows.append({"Alert": alert["alert_id"], "Feed": alert["case_id"],
                         "Detector": alert["prediction"], "Candidate": alert["candidate_pipe"],
                         "Review status": latest.get("status", "New"),
                         "Reviewer": latest.get("reviewer", "—"), "Updated UTC": latest.get("at", "—")})
        st.dataframe(pd.DataFrame(rows), hide_index=True, **STRETCH)
        by_id = {a["alert_id"]: a for a in alerts}
        chosen = st.selectbox("Open alert history", list(by_id),
                              format_func=lambda ident: f"{record_name(by_id[ident]['case_id'])} · "
                              + {"leak": "Suspected leak", "normal": "No alert", "uncertain": "Review required"}.get(
                                  by_id[ident]['prediction'], by_id[ident]['prediction']))
        st.dataframe(pd.DataFrame(store.events(chosen)), hide_index=True, **STRETCH)
    except (OSError, sqlite3.Error):
        st.error("Local review storage is unavailable. Configure a writable persistent disk.")
