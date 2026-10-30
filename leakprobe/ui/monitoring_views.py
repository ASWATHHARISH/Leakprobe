"""Presentation for the Monitoring record workspace; no inference or storage changes."""
import pandas as pd
import streamlit as st

from leakprobe.ui.alert_queue import ASSESSMENTS, record_name
from leakprobe.ui.monitoring import _baseline_series, _network_map_spec


def render_workspace_header(selected, alert, quality, store, on_acknowledge):
    reviews = ([e for e in store.events(alert["alert_id"]) if e["kind"] == "review"] if store else [])
    status = reviews[-1]["status"] if reviews else "New"
    st.divider()
    st.subheader(f"Record {record_name(selected)} · investigation workspace")
    st.markdown("[↑ Back to monitoring records](#monitoring-records)")
    with st.container(border=True):
        columns = st.columns([1.2, 1, 1, 1])
        columns[0].markdown(f"**{ASSESSMENTS[alert['prediction']]}**")
        columns[1].markdown(f"**Pipe {alert['candidate_pipe']}**" if alert["candidate_pipe"] else "**No candidate pipe**")
        columns[1].caption("Leading pattern match · unconfirmed")
        columns[2].markdown(f"**{quality['reading_coverage']:.1%} usable readings**")
        columns[2].caption(f"{quality['channels_present']} / 209 channels present")
        columns[3].markdown(f"**{status if alert['prediction'] != 'normal' else 'Review not required'}**")
        if store is not None and alert["prediction"] != "normal" and not reviews:
            with columns[3].popover("Acknowledge alert"):
                st.caption("Record receipt only. Field confirmation is a separate review action.")
                prefix = "ack_" + alert["alert_id"]
                with st.form(prefix):
                    st.text_input("Acknowledged by", key=prefix + "_reviewer", max_chars=120)
                    st.form_submit_button("Save acknowledgment", on_click=on_acknowledge,
                                          args=(alert["alert_id"], store, prefix, True))
        columns[3].caption("Use Employee Review for notes and field findings.")
    feedback = st.session_state.pop("ack_feedback_" + alert["alert_id"], None)
    if feedback:
        (st.success if feedback[0] else st.error)(feedback[1])
    freshness = "stale relative to current clock" if quality["stale"] else "within freshness window"
    st.caption("Net3 simulation feed")
    st.caption(f"Latest sensor timestamp: {quality['latest']} · {freshness} · 92 pressure / 117 flow channels")
    if quality["stale_channels"]:
        st.warning(f"{len(quality['stale_channels'])} channels have no readings in the last two samples; evidence is incomplete.")


def workspace_map_spec(layout, candidate):
    """Keep real topology and the existing single pan/zoom binding."""
    spec = _network_map_spec(layout, candidate)
    spec["height"] = 420
    spec["layer"][0]["mark"].update(color="#a6b4be", strokeWidth=1.5)
    spec["layer"][-1]["mark"].update(color="#bd541d", strokeWidth=7)
    return spec


def render_overview(snapshot, alert, layout, rows, counts):
    left, right = st.columns([1.65, 1], gap="medium")
    with left:
        st.subheader("Network schematic")
        st.vega_lite_chart(None, workspace_map_spec(layout, alert["candidate_pipe"]), use_container_width=True)
        st.caption("Orange: leading candidate · teal circles: junctions · dark squares: reservoirs · gray: pipes · dashed: pumps. Hover for IDs; pan and zoom to inspect.")
    with right:
        st.subheader("Current assessment")
        st.write({"leak": "A leak pattern fits this window best. Verify the candidate against sensor health and operating changes before dispatch or confirmation.",
                  "normal": "The current assessment has not identified a leak requiring attention. Review sensor departures and data quality if concerns remain.",
                  "uncertain": "The available pattern comparison does not support a clear leak assessment. Review data quality and competing candidates."}[alert["prediction"]])
        st.markdown("**Important sensor departures**")
        st.caption(f"{counts['pressure']} pressure / {counts['flow']} flow sensors have readings outside their normal reference range.")
        if rows:
            for row in rows[:3]:
                unit = "pressure" if row["Sensor group"] == "Pressure" else "flow"
                st.write(f"• {unit.title()} {row['Channel']}: {row['Readings outside reference']} readings outside range")
        else:
            st.write("No readings fall outside the time-aligned reference ranges.")
        st.caption("Ordered by departure count, not causal importance. These are review cues, not proven leak effects.")
        st.markdown("**Immediate verification**")
        st.markdown("1. Check sensor health and recent demand, pump or valve changes.\n2. Review nearby readings and alternate pipes.\n3. Follow approved field procedures before confirming a leak.")
    with st.expander("Current assessment · evidence and competing candidates"):
        decision = snapshot["comparison"]["decision"]
        st.write(decision.get("reason", "Assessment from the existing physics comparator."))
        st.caption("Fit errors rank stored patterns: lower is closer. They are not probabilities or confirmed locations.")
        ranking = snapshot["comparison"]["ranking"]
        visible = ranking[:5]
        normal = next((row for row in ranking if row["scenario"] == "normal"), None)
        if normal and normal not in visible:
            visible = [*visible, normal]
        st.dataframe(pd.DataFrame([{"Rank": ranking.index(row) + 1,
                                    "Candidate": row["scenario"].replace("leak_pipe:", "Pipe "),
                                    "Fit error · lower is closer": row["normalized_rmse"]}
                                   for row in visible]), hide_index=True, use_container_width=True)


def latest_sensor_values(snapshot, rows):
    observations = snapshot["observations"]
    result = []
    for row in rows:
        group, sensor = row["Sensor group"].lower(), row["Channel"]
        column = f"pressure_{sensor}_m" if group == "pressure" else f"flow_{sensor}_lps"
        reference = pd.Series([p[group][sensor][-1] for p in snapshot["normal_profiles"]])
        latest, low, high = observations[column].iloc[-1], reference.quantile(.05), reference.quantile(.95)
        result.append({"Sensor": column, "Unit": "m head" if group == "pressure" else "L/s",
                       "Latest observed": latest, "Normal median": float(reference.median()),
                       "Normal 5%": float(low), "Normal 95%": float(high),
                       "Latest status": "Missing" if pd.isna(latest) else "Outside range" if latest < low or latest > high else "Within range",
                       "Readings outside reference": row["Readings outside reference"]})
    return result


def render_sensors(snapshot, quality, rows):
    st.subheader("Sensor analysis")
    st.caption("Current observations and time-aligned normal baselines. Missing readings remain missing.")
    pressure, flow = _baseline_series(snapshot["observations"], snapshot["normal_profiles"])
    left, right = st.columns(2)
    with left:
        st.markdown("**Pressure · meters of head**")
        st.line_chart(pressure, height=235)
    with right:
        st.markdown("**Flow magnitude · L/s**")
        st.line_chart(flow, height=235)
    st.caption("Charts show network medians across channels by elapsed hour. Flow magnitude is absolute; the signed measurements below preserve pipe orientation.")
    st.markdown("**Affected sensor readings**")
    if rows:
        values = latest_sensor_values(snapshot, rows)
        st.dataframe(pd.DataFrame(values[:12]), hide_index=True, use_container_width=True)
        with st.expander(f"All affected sensors · {len(values)}"):
            st.dataframe(pd.DataFrame(values), hide_index=True, use_container_width=True)
    else:
        st.info("No sensor readings are outside the time-aligned normal reference ranges.")
    st.caption("Latest values and 5–95% reference ranges use the final aligned sample. Departure counts span the full window.")
    st.markdown("**Data quality & freshness**")
    left, right = st.columns(2)
    with left:
        st.write(f"{'Review needed' if quality['stale'] else 'Within freshness window'} · latest reading {quality['latest']} (UTC)")
        st.caption("Freshness is measured against the current clock; recorded timestamps are preserved.")
    with right:
        st.write(f"{quality['reading_coverage']:.1%} usable readings · {quality['missing_readings']:,} missing")
        st.caption(f"Latest sample: {quality['latest_channel_coverage']} / 209 channels reporting. Channels present: {quality['channels_present']} / 209.")
    if quality["stale_channels"]:
        st.write("No readings in the last two samples: " + ", ".join(quality["stale_channels"]))
    with st.expander("Detailed measurements · all 209 channels"):
        st.caption("Original time-aligned observations, including signed flows and missing values.")
        st.dataframe(snapshot["observations"], hide_index=True, use_container_width=True)
        st.download_button("Download measurements", snapshot["observations"].to_csv(index=False),
                           file_name=f"{snapshot['case_id']}_measurements.csv", mime="text/csv")
    with st.expander("Technical feed diagnostics"):
        st.json(quality)


def render_prior_alerts(alert, store):
    previous = [a for a in store.alerts() if a["alert_id"] != alert["alert_id"]] if store else []
    if previous:
        with st.expander(f"Previously recorded alerts · {len(previous)}"):
            st.caption("Stored assessments and employee reviews. Use Monitoring records to open another window.")
            history = []
            for prior in previous:
                reviews = [e for e in store.events(prior["alert_id"]) if e["kind"] == "review"]
                latest = reviews[-1] if reviews else {}
                history.append({"Alert": prior["alert_id"], "Feed": prior["case_id"],
                                "Assessment": ASSESSMENTS.get(prior["prediction"], prior["prediction"]),
                                "Candidate": prior.get("candidate_pipe"), "Review": latest.get("status", "New"),
                                "Updated (UTC)": latest.get("at", "—")})
            st.dataframe(pd.DataFrame(history), hide_index=True, use_container_width=True)
