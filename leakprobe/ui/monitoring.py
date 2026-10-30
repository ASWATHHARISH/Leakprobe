"""Automatic employee monitoring dashboard for the configured Net3 feed."""
import numpy as np
import pandas as pd
import streamlit as st
from leakprobe.ui.layout import STRETCH
from leakprobe.ui.charts import baseline_chart_spec

from leakprobe.ui.branding import render_product_header
from leakprobe.ui.data_access import (
    MONITORING_CASE_ID,
    load_case_index,
    load_monitoring_snapshot,
    load_network_layout,
)


def _channel_columns(observations: pd.DataFrame, prefix: str) -> list[str]:
    return [column for column in observations.columns if column.startswith(prefix)]


def _baseline_series(observations: pd.DataFrame, normal_profiles: list[dict]) -> tuple[pd.DataFrame, pd.DataFrame]:
    pressure_columns = _channel_columns(observations, "pressure_")
    flow_columns = _channel_columns(observations, "flow_")
    pressure_nodes = [column.removeprefix("pressure_").removesuffix("_m")
                      for column in pressure_columns]
    flow_pipes = [column.removeprefix("flow_").removesuffix("_lps")
                  for column in flow_columns]

    current_pressure = observations[pressure_columns].to_numpy(dtype=float)
    current_flow = observations[flow_columns].to_numpy(dtype=float)
    reference_pressure = np.asarray([
        [profile["pressure"][node] for node in pressure_nodes]
        for profile in normal_profiles
    ], dtype=float)
    reference_flow = np.asarray([
        [profile["flow"][pipe] for pipe in flow_pipes]
        for profile in normal_profiles
    ], dtype=float)

    pressure_observed_median = np.nanmedian(current_pressure, axis=1)
    pressure_normal_median = np.nanmedian(
        np.nanmedian(reference_pressure, axis=1), axis=0
    )
    flow_observed_median = np.nanmedian(np.abs(current_flow), axis=1)
    flow_normal_median = np.nanmedian(
        np.nanmedian(np.abs(reference_flow), axis=1), axis=0
    )
    elapsed_hours = (
        pd.to_datetime(observations["timestamp_utc"], utc=True)
        - pd.to_datetime(observations["timestamp_utc"], utc=True).iloc[0]
    ).dt.total_seconds() / 3600

    pressure_chart = pd.DataFrame({
        "Current feed": pressure_observed_median,
        "Normal reference": pressure_normal_median,
    }, index=elapsed_hours)
    pressure_chart.index.name = "Elapsed hour"
    flow_chart = pd.DataFrame({
        "Current feed": flow_observed_median,
        "Normal reference": flow_normal_median,
    }, index=elapsed_hours)
    flow_chart.index.name = "Elapsed hour"
    return pressure_chart, flow_chart


def _reference_deviations(
    observations: pd.DataFrame,
    normal_profiles: list[dict],
    channel_type: str,
) -> tuple[int, int, list[dict]]:
    prefix, suffix, group = {
        "pressure": ("pressure_", "_m", "pressure"),
        "flow": ("flow_", "_lps", "flow"),
    }[channel_type]
    columns = _channel_columns(observations, prefix)
    sensors = [column.removeprefix(prefix).removesuffix(suffix) for column in columns]
    references = np.asarray([
        [profile[group][sensor] for sensor in sensors]
        for profile in normal_profiles
    ], dtype=float)
    lower, upper = np.nanpercentile(references, [5, 95], axis=0)
    current = observations[columns].to_numpy(dtype=float).T
    outside = ((current < lower) | (current > upper)) & np.isfinite(current)
    outside_per_sensor = outside.sum(axis=1)
    affected = int(np.count_nonzero(outside_per_sensor))
    total_observations = int(outside.sum())
    rows = [
        {
            "Sensor group": "Pressure" if channel_type == "pressure" else "Flow",
            "Channel": sensors[index],
            "Readings outside reference": int(count),
        }
        for index, count in enumerate(outside_per_sensor)
        if count
    ]
    return affected, total_observations, rows


def _network_map_spec(layout: dict, candidate_pipe: str | None) -> dict:
    pipes = [row for row in layout["pipes"] if row["id"] != candidate_pipe]
    highlighted = [row for row in layout["pipes"] if row["id"] == candidate_pipe]
    encodings = {
        "x": {"field": "x", "type": "quantitative", "axis": None},
        "x2": {"field": "x2"},
        "y": {"field": "y", "type": "quantitative", "axis": None},
        "y2": {"field": "y2"},
        "tooltip": [{"field": "id", "title": "Pipe / link"}],
    }
    return {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "width": "container",
        "height": 460,
        "background": "#ffffff",
        "autosize": {"type": "fit", "contains": "padding"},
        "config": {"view": {"stroke": None}, "axis": {"grid": False}},
        "layer": [
            {"data": {"values": pipes},
             # A top-level selection is duplicated into every layer by Vega-Lite.
             # Bind it once; the layered chart shares the x/y scales by default.
             "params": [{"name": "network_view", "select": "interval", "bind": "scales"}],
             "mark": {"type": "rule", "color": "#9aa9b4", "strokeWidth": 1},
             "encoding": encodings},
            {"data": {"values": layout["pumps"]},
             "mark": {"type": "rule", "color": "#64748b", "strokeWidth": 2,
                      "strokeDash": [5, 3]},
             "encoding": encodings},
            {"data": {"values": layout["junctions"]},
             "mark": {"type": "point", "shape": "circle", "filled": True,
                      "color": "#0f6b78", "size": 28},
             "encoding": {
                 "x": {"field": "x", "type": "quantitative", "axis": None},
                 "y": {"field": "y", "type": "quantitative", "axis": None},
                 "tooltip": [{"field": "id", "title": "Pressure sensor junction"}],
             }},
            {"data": {"values": layout["reservoirs"]},
             "mark": {"type": "point", "shape": "square", "filled": True,
                      "color": "#334155", "size": 90},
             "encoding": {
                 "x": {"field": "x", "type": "quantitative", "axis": None},
                 "y": {"field": "y", "type": "quantitative", "axis": None},
                 "tooltip": [{"field": "id", "title": "Reservoir"}],
             }},
            {"data": {"values": highlighted},
             "mark": {"type": "rule", "color": "#dc2626", "strokeWidth": 6},
             "encoding": encodings},
        ],
    }


def render_evaluation_replay() -> None:
    render_product_header()
    st.header(
        "Window replay",
        help=(
            "The operations view for the currently selected full-channel sensor feed. "
            "It compares the feed with normal-operation references and candidate leak patterns."
        ),
    )
    st.write("The current full-channel feed is checked automatically against normal operation and candidate leak patterns.")
    st.caption("Open a monitoring record to review its alert, network map and sensor evidence.")
    try:
        case_ids = [case["case_id"] for case in load_case_index()]
        default_case_index = case_ids.index(MONITORING_CASE_ID) if MONITORING_CASE_ID in case_ids else 0
        selected_case_id = st.selectbox(
            "Monitoring record",
            options=case_ids,
            index=default_case_index,
            key="monitoring_case_id",
            help=(
                "Open a saved record. Its alert, candidate pipe, network map, baseline charts "
                "and timestamps update together. This selection changes only the displayed assessment."
            ),
        )
        with st.spinner("Checking the latest monitoring window…"):
            snapshot = load_monitoring_snapshot(selected_case_id)
            layout = load_network_layout()
    except (OSError, ValueError, KeyError, ImportError) as exc:
        st.error(f"The monitoring feed could not be loaded: {exc}")
        return

    observations = snapshot["observations"]
    comparison = snapshot["comparison"]
    ranking = comparison["ranking"]
    decision = comparison["decision"]
    pressure_columns = _channel_columns(observations, "pressure_")
    flow_columns = _channel_columns(observations, "flow_")
    total_sensor_channels = len(pressure_columns) + len(flow_columns)
    missing_readings = int(observations[[*pressure_columns, *flow_columns]].isna().sum().sum())
    sample_count = len(observations)
    latest_time = pd.to_datetime(observations["timestamp_utc"], utc=True).iloc[-1]
    window_hours = (latest_time - pd.to_datetime(observations["timestamp_utc"], utc=True).iloc[0]).total_seconds() / 3600
    candidate_pipe = decision.get("best_scenario", "")
    candidate_pipe = candidate_pipe.removeprefix("leak_pipe:") if candidate_pipe != "normal" else None
    best_leak = next((row for row in ranking if row["scenario"] != "normal"), None)
    normal_fit = next((row for row in ranking if row["scenario"] == "normal"), None)

    pressure_affected, pressure_outside, pressure_rows = _reference_deviations(
        observations, snapshot["normal_profiles"], "pressure"
    )
    flow_affected, flow_outside, flow_rows = _reference_deviations(
        observations, snapshot["normal_profiles"], "flow"
    )

    metrics = st.columns(4)
    metrics[0].metric(
        "Network status",
        decision["prediction"].replace("_", " ").title(),
        help=(
            "The automatic comparison's current outcome: leak pattern, normal operation, "
            "or review required. It is a model result for this feed, not field confirmation."
        ),
    )
    metrics[1].metric(
        "Best candidate",
        f"Pipe {candidate_pipe}" if candidate_pipe else "None",
        help=(
            "The pipe whose stored leak pattern best fits this monitoring window. "
            "It is a candidate for field verification, not a confirmed leak location."
        ),
    )
    metrics[2].metric(
        "Sensor channels",
        f"{total_sensor_channels} / 209",
        help=(
            "Number of full-feed channels present: 92 pressure channels plus 117 flow channels. "
            "Missing individual readings are counted separately below."
        ),
    )
    metrics[3].metric(
        "Monitoring window",
        f"{window_hours:g} h · {sample_count} readings",
        help=(
            "Elapsed time from the first to the latest timestamp, followed by the number "
            "of time-stamped feed records in this window."
        ),
    )
    st.caption("Net3 simulation feed")
    st.caption(
        f"Latest reading: {latest_time.strftime('%d %b %Y %H:%M UTC')} · "
        f"{missing_readings:,} missing sensor values",
        help=(
            "The timestamp is the latest observation in the selected feed. Missing sensor "
            "values are individual channel readings that were not supplied in this window."
        ),
    )

    st.subheader(
        "Current alert",
        help=(
            "The outcome for this selected feed. A leak alert identifies a best-fit candidate "
            "for field verification; a normal result means the normal-operation pattern fits "
            "best; review required means neither result is clear."
        ),
    )
    if decision["prediction"] == "leak":
        st.error(
            f"Leak alert · Feed {snapshot['case_id']} — "
            f"review candidate pipe {candidate_pipe}"
        )
        st.write("The leak pattern for this pipe is the best fit across the complete pressure and flow feed.")
        st.info("Recommended next step: verify the indicated pipe through the normal field-check process. This dashboard does not create a work order or dispatch a crew.")
    elif decision["prediction"] == "normal":
        st.success(
            f"No leak alert · Feed {snapshot['case_id']} — "
            "normal operation is the best-fitting pattern for this window."
        )
    else:
        st.warning(
            f"Review required · Feed {snapshot['case_id']} — "
            "the current feed does not support a clear leak or normal result."
        )

    st.subheader(
        "Network and sensor map",
        help=(
            "A map of the Net3 network topology. The current best candidate pipe is highlighted "
            "in red; pressure sensor junctions, other pipes, and pumps are shown for context."
        ),
    )
    st.vega_lite_chart(None, _network_map_spec(layout, candidate_pipe), **STRETCH)
    if candidate_pipe:
        st.caption(
            f"Candidate pipe {candidate_pipe} is red. Blue circles are pressure junctions; "
            "gray lines are other pipes; dashed lines are pumps.",
            help=(
                "Map key: red is the pipe selected as the best leak candidate, blue circles are "
                "pressure sensor junctions, gray lines are other pipes, and dashed lines are pumps."
            ),
        )
    else:
        st.caption(
            "Blue circles are pressure junctions; gray segments are pipes; dashed segments are pumps. No leak candidate is highlighted.",
            help=(
                "Map key: blue circles are pressure sensor junctions, gray lines are pipes, "
                "and dashed lines are pumps. No candidate pipe is currently available."
            ),
        )

    st.subheader(
        "Readings compared with the normal baseline",
        help=(
            "Network-wide summaries of the selected feed compared with typical normal-operation "
            "profiles. The leak assessment itself uses every pressure and flow channel."
        ),
    )
    pressure_chart, flow_chart = _baseline_series(observations, snapshot["normal_profiles"])
    left, right = st.columns(2)
    with left:
        st.subheader(
            "Median network pressure · m",
            help=(
                "At each timestamp, the middle pressure value across the 92 pressure channels. "
                "The normal reference is the median of the stored normal profiles."
            ),
        )
        st.vega_lite_chart(None, baseline_chart_spec(pressure_chart, "Pressure head (m)"), **STRETCH)
    with right:
        st.subheader(
            "Median absolute pipe flow · L/s",
            help=(
                "At each timestamp, the middle absolute flow value across the 117 pipe channels. "
                "The normal reference is the median of the stored normal profiles."
            ),
        )
        st.vega_lite_chart(None, baseline_chart_spec(flow_chart, "Flow magnitude (L/s)"), **STRETCH)
    st.caption(
        "The normal reference is the median of 24 stored normal-operation profiles. The charts summarize the network; the alert comparison uses all 92 pressure and 117 flow channels.",
        help=(
            "Each chart condenses the whole network into one series at each time point. "
            "The automatic comparison still evaluates all 92 pressure and 117 flow channels."
        ),
    )

    st.subheader(
        "Evidence for this monitoring window",
        help=(
            "Counts of sensor channels and individual readings that fall outside their usual "
            "normal-operation ranges during this feed window. These are supporting evidence, "
            "not a leak probability."
        ),
    )
    evidence = st.columns(4)
    evidence[0].metric(
        "Pressure channels outside reference",
        f"{pressure_affected} / 92",
        help=(
            "How many distinct pressure channels had at least one reading outside that channel's "
            "normal range during this window. The range is the 5th–95th percentile across 24 "
            "normal-operation profiles."
        ),
    )
    evidence[1].metric(
        "Pressure readings outside",
        pressure_outside,
        help=(
            "The total number of individual pressure readings outside their channel's normal "
            "range across all timestamps. Repeated out-of-range readings on one sensor each count."
        ),
    )
    evidence[2].metric(
        "Flow channels outside reference",
        f"{flow_affected} / 117",
        help=(
            "How many distinct flow channels had at least one reading outside that channel's "
            "normal range during this window. The range is the 5th–95th percentile across 24 "
            "normal-operation profiles."
        ),
    )
    evidence[3].metric(
        "Flow readings outside",
        flow_outside,
        help=(
            "The total number of individual flow readings outside their channel's normal range "
            "across all timestamps. Repeated out-of-range readings on one pipe each count."
        ),
    )
    st.caption(
        "Outside-reference counts describe readings beyond the 5th–95th percentile of normal profiles. They are evidence for review, not a calibrated alert probability.",
        help=(
            "The range is calculated separately for every channel from 24 normal-operation "
            "profiles. A reading outside that range is unusual compared with those profiles, "
            "but does not by itself prove a leak."
        ),
    )

    deviation_rows = sorted(pressure_rows + flow_rows,
                            key=lambda row: row["Readings outside reference"], reverse=True)
    if deviation_rows:
        with st.expander(
            "Channels with the most baseline departures",
            icon=":material/info:",
        ):
            st.caption(
                "The ten channels with the most individual readings outside their normal ranges. "
                "A channel can appear here even when the cause is not a leak."
            )
            st.dataframe(
                pd.DataFrame(deviation_rows[:10]),
                hide_index=True,
                **STRETCH,
                column_config={
                    "Sensor group": st.column_config.TextColumn(
                        help="Whether this is a pressure sensor or a pipe-flow sensor."
                    ),
                    "Channel": st.column_config.TextColumn(
                        help="The sensor or pipe identifier associated with these readings."
                    ),
                    "Readings outside reference": st.column_config.NumberColumn(
                        help="Number of timestamps at which this channel was outside its normal range."
                    ),
                },
            )
    if ranking:
        with st.expander("Scenario fit details", icon=":material/info:"):
            st.caption(
                "Shows how closely each stored leak or normal-operation pattern matches the feed. "
                "The fit score is an error measure; lower is closer and it is not a probability."
            )
            fit_metrics = st.columns(2)
            fit_metrics[0].metric(
                "Best leak fit · lower is closer",
                f"{best_leak['normalized_rmse']:.3f}" if best_leak else "—",
                help=(
                    "The lowest normalized fit error among the candidate leak patterns. "
                    "Lower means closer to the feed; it is not a probability or confidence percentage."
                ),
            )
            fit_metrics[1].metric(
                "Normal-operation fit · lower is closer",
                f"{normal_fit['normalized_rmse']:.3f}" if normal_fit else "—",
                help=(
                    "The normalized fit error for the normal-operation pattern. "
                    "Compare it with leak-pattern errors; lower means closer, not more probable."
                ),
            )
            details = [{
                "Rank": rank,
                "Scenario": row["scenario"].replace("leak_pipe:", "Pipe "),
                "Normalized fit error": row["normalized_rmse"],
            } for rank, row in enumerate(ranking[:6], start=1)]
            st.dataframe(
                pd.DataFrame(details),
                hide_index=True,
                **STRETCH,
                column_config={
                    "Rank": st.column_config.NumberColumn(
                        help="Position in the ordered list, from the lowest error upward."
                    ),
                    "Scenario": st.column_config.TextColumn(
                        help="The stored normal-operation pattern or pipe-specific leak pattern being compared."
                    ),
                    "Normalized fit error": st.column_config.NumberColumn(
                        format="%.3f",
                        help="Difference between the feed and this pattern after normalization. Lower is a closer match; it is not a probability.",
                    ),
                },
            )
            st.caption(comparison["score_meaning"])
    with st.expander(
        "Feed record details (read-only)",
        icon=":material/info:",
    ):
        st.caption(
            "A read-only summary of the selected feed ID, time range, channel coverage, and missing readings."
        )
        st.write({
            "Feed record": snapshot["case_id"],
            "Window start": pd.to_datetime(observations["timestamp_utc"], utc=True).iloc[0].strftime("%d %b %Y %H:%M UTC"),
            "Latest reading": latest_time.strftime("%d %b %Y %H:%M UTC"),
            "Pressure channels present": f"{len(pressure_columns)} / 92",
            "Flow channels present": f"{len(flow_columns)} / 117",
            "Missing individual readings": f"{missing_readings:,}",
        })
