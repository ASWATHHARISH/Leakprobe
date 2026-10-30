"""Observation-only presentation checks; never changes physics decisions."""
import hashlib
import json
import re

import numpy as np
import pandas as pd

from leakprobe.coverage import validate_full_channel_coverage

REPORT_SECTIONS = ("Investigation summary", "Anomalous sensor evidence",
                   "Why the leading pipe ranked highest", "Competing explanations or alternate pipes",
                   "Uncertainty and limitations", "Recommended employee verification actions")


def feed_fingerprint(observations):
    rows = observations.astype(object).where(pd.notna(observations), None).to_dict("records")
    return records_fingerprint(rows)


def records_fingerprint(rows):
    return hashlib.sha256(json.dumps(rows, sort_keys=True, allow_nan=False,
                                     separators=(",", ":")).encode()).hexdigest()


def validate_feed(observations, metadata, normal_profiles, now=None):
    """Require the reference time grid, permit null readings, expose stale channels."""
    validate_full_channel_coverage(metadata, observations.columns, "Monitoring feed")
    if observations.columns.duplicated().any() or observations.empty:
        raise ValueError("Empty feed or duplicate channel definitions.")
    times = pd.to_datetime(observations["timestamp_utc"], utc=True, errors="raise")
    if times.isna().any() or times.duplicated().any() or not times.is_monotonic_increasing:
        raise ValueError("Feed timestamps must be valid, unique and increasing.")
    step = pd.Timedelta(minutes=metadata["timestep_minutes"])
    expected = int(metadata["duration_hours"] * 60 / metadata["timestep_minutes"]) + 1
    if len(times) != expected or not times.diff().iloc[1:].eq(step).all():
        raise ValueError("Feed does not align with the reference time grid; comparison unavailable.")
    # The bundled simulator anchors every profile at this UTC origin (net3_benchmark).
    origin = pd.Timestamp("2026-01-01T00:00:00Z")
    if times.iloc[0] != origin:
        raise ValueError("Feed start does not match the bundled simulation reference origin.")
    channels = [c for c in observations if c.startswith(("pressure_", "flow_"))]
    values = observations[channels].apply(pd.to_numeric, errors="raise").to_numpy(float)
    if np.isinf(values).any() or not np.isfinite(values).any():
        raise ValueError("Feed contains infinite values or has no usable readings.")
    if not normal_profiles:
        raise ValueError("Normal baseline is unavailable.")
    for profile in normal_profiles:
        for group, sensors in (("pressure", metadata["monitor_pressure_nodes"]),
                               ("flow", metadata["flow_sensors"])):
            for sensor in sensors:
                series = np.asarray(profile[group][sensor], dtype=float)
                if series.shape != (expected,) or not np.isfinite(series).all():
                    raise ValueError("Normal baseline dimensions or values do not match the feed.")
    current_time = pd.Timestamp.now(tz="UTC") if now is None else pd.Timestamp(now)
    if current_time.tzinfo is None:
        current_time = current_time.tz_localize("UTC")
    age = (current_time - times.iloc[-1]).total_seconds()
    if age < -step.total_seconds():
        raise ValueError("Feed timestamp is in the future.")
    finite = np.isfinite(values)
    stale_channels = [channels[i] for i in range(len(channels)) if not finite[-2:, i].any()]
    return {"latest": times.iloc[-1].isoformat(), "age_seconds": max(0, age),
            "stale": age > step.total_seconds() * 2,
            "channels_present": len(channels), "channels_with_readings": int(finite.any(axis=0).sum()),
            "latest_channel_coverage": int(finite[-1].sum()),
            "missing_readings": int((~finite).sum()), "stale_channels": stale_channels,
            "reading_coverage": float(finite.mean())}


def build_alert(snapshot):
    """Stable identity from feed content and deterministic comparison, never labels."""
    comparison = snapshot["comparison"]
    decision = comparison["decision"]
    fingerprint = feed_fingerprint(snapshot["observations"])
    identity = json.dumps({"feed": fingerprint, "case": snapshot["case_id"],
                           "comparison": comparison}, sort_keys=True, allow_nan=False)
    alert_id = hashlib.sha256(identity.encode()).hexdigest()[:24]
    return {"alert_id": alert_id, "case_id": snapshot["case_id"],
            "feed_fingerprint": fingerprint, "prediction": decision["prediction"],
            "comparison_signature": [{"scenario": r["scenario"], "score": r["normalized_rmse"]}
                                     for r in comparison.get("ranking", [])],
            "candidate_pipe": (decision.get("best_scenario", "").split(":", 1)[1]
                               if decision.get("best_scenario", "").startswith("leak_pipe:") else None)}


def matching_investigation(runs, alert, observations=None):
    """Do not attach another window's explanation, including same-ID changed feeds."""
    for run in runs:
        if run.get("case_id") != alert["case_id"]:
            continue
        if run.get("alert_id") == alert["alert_id"]:
            return run
        if run.get("alert_id"):
            continue  # Modern trace from another comparison must not fall back to legacy matching.
        expected = alert.get("comparison_signature", [])
        if expected:
            comparisons = [step["result"] for step in run.get("trace", [])
                           if step.get("tool") == "compare_hypotheses" and isinstance(step.get("result"), dict)]
            prior = comparisons[-1].get("ranking", []) if comparisons else []
            if [r.get("scenario") for r in prior] != [r["scenario"] for r in expected]:
                continue
            if not np.allclose([r.get("normalized_rmse", np.inf) for r in prior],
                               [r["score"] for r in expected], rtol=1e-12, atol=1e-10):
                continue
        # Legacy traces predate alert IDs. Match their actual observation payload.
        for step in run.get("trace", []):
            result = step.get("result", {})
            if step.get("tool") == "get_observations" and isinstance(result, dict):
                if records_fingerprint(result.get("readings", [])) == alert["feed_fingerprint"]:
                    return run
                if observations is not None:
                    # Older JSON/CSV parsers round floats differently. Tolerance is far below
                    # sensor resolution; timestamps, channel IDs and missing masks must agree.
                    try:
                        prior = pd.DataFrame(result.get("readings", []))
                        if set(prior.columns) != set(observations.columns):
                            continue
                        if prior["timestamp_utc"].tolist() != observations["timestamp_utc"].tolist():
                            continue
                        columns = [c for c in observations if c != "timestamp_utc"]
                        if np.allclose(prior[columns].to_numpy(float), observations[columns].to_numpy(float),
                                       rtol=1e-12, atol=1e-10, equal_nan=True):
                            return run
                    except (ValueError, TypeError, KeyError):
                        continue
    return None


def report_summary(answer):
    """Extract existing model text verbatim; never synthesize a substitute explanation."""
    match = re.search(r"(?im)^#{1,6}\s+(?:Investigation summary|Summary)\s*$", answer)
    if match:
        rest = answer[match.end():].strip()
        return re.split(r"(?m)^#{1,6}\s+", rest, maxsplit=1)[0].strip()
    return None


def employee_report_sections(answer):
    """Require all employee report dimensions; preserve the model's actual wording."""
    headings = list(re.finditer(r"(?m)^#{1,6}[ \t]+([^\n]+)\n", answer))
    sections = {}
    canonical = {name.casefold(): name for name in REPORT_SECTIONS}
    for index, heading in enumerate(headings):
        title = heading.group(1).strip().strip("*").strip().casefold()
        if title in canonical:
            end = headings[index + 1].start() if index + 1 < len(headings) else len(answer)
            body = answer[heading.end():end].strip()
            if body:
                sections[canonical[title]] = body
    return sections
