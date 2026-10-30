"""Observation-only queue over the canonical windows; no labels or AI requests."""
import pandas as pd
import streamlit as st
import hashlib
import json
import os
import tempfile
from pathlib import Path

from leakprobe.net3_tools import Net3Investigation
from leakprobe.paths import NET3_DATA, OUTPUTS, ROOT
from leakprobe.ui.data_access import load_case_index
from leakprobe.ui.operations import build_alert, validate_feed

ASSESSMENTS = {"leak": "Suspected leak", "normal": "No alert",
               "uncertain": "Review required", "unavailable": "Feed unavailable"}


def record_name(case_id):
    return "LP-" + case_id.removeprefix("case_").zfill(4)


def assess_window(case_id):
    """Use the unchanged detector, and keep invalid feeds visibly unavailable."""
    try:
        session = Net3Investigation(case_id)
        quality = validate_feed(session.observations, session.metadata, session.hypotheses["normal"])
        comparison = session.compare_hypotheses()
        alert = build_alert({"case_id": case_id, "observations": session.observations,
                             "comparison": comparison})
        return {**alert, "record": record_name(case_id), "latest": quality["latest"], "error": None}
    except (OSError, ValueError, KeyError) as exc:
        return {"case_id": case_id, "record": record_name(case_id), "alert_id": None,
                "prediction": "unavailable", "candidate_pipe": None, "latest": None,
                "error": str(exc)}


def queue_source_digest(cases):
    """Bind the derived queue to observations and detector sources, never truth labels."""
    paths = [NET3_DATA / name for name in ("cases.json", "metadata.json", "hypotheses.json")]
    paths += [NET3_DATA / case["observations_file"] for case in cases]
    paths += [ROOT / "leakprobe" / name for name in ("net3_tools.py", "coverage.py", "ui/operations.py", "ui/alert_queue.py")]
    digest = hashlib.sha256()
    for path in paths:
        digest.update(str(path.relative_to(ROOT)).encode())
        with path.open("rb") as stream:
            digest.update(hashlib.file_digest(stream, "sha256").digest())
    return digest.hexdigest()


def load_or_assess_queue(cases, signature, cache_dir):
    """An additive derived-data cache; no benchmark reports or inputs are written."""
    path = Path(cache_dir) / f"monitoring_queue_{signature}.json"
    try:
        saved = json.loads(path.read_text(encoding="utf-8"))
        rows = saved["records"]
        row_digest = hashlib.sha256(json.dumps(rows, sort_keys=True, allow_nan=False).encode()).hexdigest()
        if (saved["source_digest"] == signature and saved["records_digest"] == row_digest
                and [row["case_id"] for row in rows] == [case["case_id"] for case in cases]
                and all(row["prediction"] in ASSESSMENTS for row in rows)):
            return rows
    except (OSError, ValueError, KeyError, TypeError):
        pass
    rows = [assess_window(case["case_id"]) for case in cases]
    payload = {"source_digest": signature, "records": rows,
               "records_digest": hashlib.sha256(json.dumps(rows, sort_keys=True, allow_nan=False).encode()).hexdigest()}
    # A damaged existing cache is preserved; it is never replaced.
    if not path.exists():
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, suffix=".tmp", delete=False) as stream:
                temporary = Path(stream.name)
                json.dump(payload, stream, allow_nan=False)
                stream.flush()
                os.fsync(stream.fileno())
            try:
                os.link(temporary, path)
            finally:
                temporary.unlink(missing_ok=True)
        except OSError:
            pass  # Queue remains usable on a read-only host.
    return rows


@st.cache_data(show_spinner=False)
def load_monitoring_queue():
    cases = load_case_index()
    if len({case["case_id"] for case in cases}) != len(cases):
        raise ValueError("Duplicate monitoring record identifiers.")
    return load_or_assess_queue(cases, queue_source_digest(cases), OUTPUTS / "operations")


def render_alert_queue(queue, store, default_case_id):
    """An employee opens a generated assessment, never configures detector inputs."""
    known = {a["alert_id"]: a for a in store.alerts()} if store else {}
    statuses = {}
    for alert_id in known:
        reviews = [event for event in store.events(alert_id) if event["kind"] == "review"]
        statuses[alert_id] = reviews[-1]["status"] if reviews else "New"
    metrics = st.columns(4)
    metrics[0].metric("Monitoring records", len(queue))
    metrics[1].metric("Suspected leaks", sum(r["prediction"] == "leak" for r in queue))
    metrics[2].metric("Review required", sum(r["prediction"] == "uncertain" for r in queue))
    metrics[3].metric("No alert", sum(r["prediction"] == "normal" for r in queue))
    st.subheader("Alert queue & monitoring records")
    view = st.radio("Show records", ("All records", "Needs attention", "No alert", "Review required", "Feed unavailable"),
                    horizontal=True, key="monitoring_queue_view")
    filters = {"No alert": "normal", "Review required": "uncertain", "Feed unavailable": "unavailable"}
    closed = {"Leak confirmed", "No leak"}
    visible = [row for row in queue if (
        view == "All records" or
        (view == "Needs attention" and row["prediction"] in ("leak", "uncertain")
         and statuses.get(row["alert_id"]) not in closed) or
        row["prediction"] == filters.get(view))]
    st.caption("Independent recorded windows; these are not simultaneous incidents on one network.")
    if not visible:
        st.info("No monitoring records match this view.")
        return None
    st.dataframe(pd.DataFrame([{
        "Record": row["record"], "Assessment": ASSESSMENTS[row["prediction"]],
        "Candidate pipe": row["candidate_pipe"] or "—",
        "Review": statuses.get(row["alert_id"], "New") if row["prediction"] in ("leak", "uncertain") else "—",
        "Last reading (UTC)": row["latest"] or "Unavailable",
    } for row in visible]), height=245, hide_index=True, use_container_width=True)
    by_id = {row["case_id"]: row for row in visible}
    identifiers = list(by_id)
    default = default_case_id if default_case_id in by_id else identifiers[0]
    if st.session_state.get("monitoring_record_id") not in by_id:
        st.session_state.pop("monitoring_record_id", None)
    selected = st.selectbox("Open monitoring record", identifiers, index=identifiers.index(default),
                            key="monitoring_record_id", format_func=lambda ident:
                            f"{by_id[ident]['record']} · {ASSESSMENTS[by_id[ident]['prediction']]}"
                            + (f" · Pipe {by_id[ident]['candidate_pipe']}" if by_id[ident]["candidate_pipe"] else ""))
    row = by_id[selected]
    if row["prediction"] == "unavailable":
        st.warning(f"{row['record']}: {row['error']}")
        return None
    return selected
