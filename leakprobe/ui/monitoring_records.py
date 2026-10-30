"""Monitoring-only record browsing; assessments are supplied unchanged by the queue."""
import math

import pandas as pd
import streamlit as st
from leakprobe.ui.layout import STRETCH

from leakprobe.ui.alert_queue import ASSESSMENTS


PAGE_SIZE = 10
VIEWS = ("All records", "Needs attention", "Suspected leak", "No alert",
         "Review required", "Feed unavailable")


def review_statuses(store):
    if store is None:
        return {}
    statuses = {}
    for alert in store.alerts():
        reviews = [event for event in store.events(alert["alert_id"]) if event["kind"] == "review"]
        statuses[alert["alert_id"]] = reviews[-1]["status"] if reviews else "New"
    return statuses


def filter_records(queue, statuses, view="All records", search=""):
    """Filter display fields only. Never inspect outcomes or modify supplied records."""
    predictions = {"Suspected leak": "leak", "No alert": "normal",
                   "Review required": "uncertain", "Feed unavailable": "unavailable"}
    terms = search.casefold().split()
    visible = []
    for row in queue:
        status = statuses.get(row["alert_id"], "New")
        matches_view = (view == "All records" or row["prediction"] == predictions.get(view)
                        or (view == "Needs attention" and row["prediction"] in ("leak", "uncertain")
                            and status not in ("Leak confirmed", "No leak")))
        text = " ".join(str(value or "") for value in (
            row["record"], row["case_id"], ASSESSMENTS[row["prediction"]],
            row["candidate_pipe"], status)).casefold()
        if matches_view and all(term in text for term in terms):
            visible.append(row)
    return visible


def page_records(rows, page, page_size=PAGE_SIZE):
    pages = max(1, math.ceil(len(rows) / page_size))
    page = min(max(1, int(page)), pages)
    return rows[(page - 1) * page_size:page * page_size], page, pages


def render_monitoring_records(queue, store, default_case_id):
    metrics = st.columns(4)
    for column, label, value in zip(metrics,
            ("Monitoring records", "Suspected leaks", "Review required", "No alert"),
            (len(queue), *(sum(row["prediction"] == p for row in queue)
                           for p in ("leak", "uncertain", "normal")))):
        column.metric(label, value)
    statuses = review_statuses(store)
    st.subheader("Monitoring records", anchor="monitoring-records")
    st.caption("Independent recorded windows; these are not simultaneous incidents on one network.")
    view = st.radio("Show records", VIEWS, horizontal=True, key="monitoring_queue_view")
    search = st.text_input("Search records", key="monitoring_record_search",
                           placeholder="Record ID, pipe, assessment or review status")
    visible = filter_records(queue, statuses, view, search)
    if not visible:
        st.info("No records match. Clear the search or choose All records to see more windows.")
        return None
    # The selector spans every matching record, independent of the table's page.
    # Paging never changes the employee's currently opened record.
    by_id = {row["case_id"]: row for row in visible}
    identifiers = list(by_id)
    default = default_case_id if default_case_id in by_id else identifiers[0]
    remembered = st.session_state.get("monitoring_selected_record", default)
    options = tuple(identifiers)
    if (st.session_state.get("monitoring_record_options") != options
            or st.session_state.get("monitoring_record_id") not in by_id):
        st.session_state["monitoring_record_id"] = remembered if remembered in by_id else default
        st.session_state["monitoring_record_options"] = options
    selected = st.selectbox("Open monitoring record", identifiers,
                            # A changing default index changes widget identity in Streamlit 1.37.
                            # Restore state above only when the option list changes; keep this fixed.
                            index=0, key="monitoring_record_id",
                            format_func=lambda ident: f"{by_id[ident]['record']} · {ASSESSMENTS[by_id[ident]['prediction']]}"
                            + (f" · Pipe {by_id[ident]['candidate_pipe']}" if by_id[ident]["candidate_pipe"] else ""),
                            help="Search or type in this list to open any matching record. Table pagination does not limit this list.")
    st.session_state["monitoring_selected_record"] = selected
    with st.expander(f"Browse matching records · {len(visible)}", expanded=False):
        signature = (view, search)
        if st.session_state.get("monitoring_page_filter") != signature:
            st.session_state["monitoring_page"] = 1
            st.session_state["monitoring_page_filter"] = signature
        _, current, pages = page_records(visible, st.session_state.get("monitoring_page", 1))
        st.session_state["monitoring_page"] = current
        page = st.number_input("Records page", min_value=1, max_value=pages, step=1,
                               key="monitoring_page", help=f"{PAGE_SIZE} records per page. Use Open monitoring record to select a window.")
        rows, page, pages = page_records(visible, page)
        st.caption(f"Page {page} of {pages} · {len(visible)} matching records")
        st.dataframe(pd.DataFrame([{
            "Record": row["record"], "Assessment": ASSESSMENTS[row["prediction"]],
            "Candidate pipe": row["candidate_pipe"] or "—",
            "Review": statuses.get(row["alert_id"], "New") if row["prediction"] in ("leak", "uncertain") else "Not required",
            "Last reading (UTC)": row["latest"] or "Unavailable",
        } for row in rows]), height=245, hide_index=True, **STRETCH)
    row = by_id[selected]
    if row["prediction"] == "unavailable":
        st.warning(f"{row['record']}: {row['error']}")
        return None
    return selected
