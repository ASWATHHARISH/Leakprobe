"""Bounded, observation-only context for Nemotron. Physics scoring stays unchanged."""
import json

import numpy as np
from jsonschema import validate

from .tool_schemas import tool


def sign(value):
    return "positive" if value > 0 else "negative" if value < 0 else "zero"


class InvestigationEvidence:
    def __init__(self, session):
        self.session = session
        self.observations = session.observations
        self.comparison = session.compare_hypotheses()
        self.facts = {}  # Only facts actually exposed through the compact tools.
        self.channels = [c for c in self.observations if c != "timestamp_utc"]

    def fact(self, identifier, value, unit, channel=None, **context):
        result = {"fact_id": identifier, "value": float(value), "unit": unit,
                  "channel": channel, "sign": sign(value), **context}
        self.facts[identifier] = result
        return result

    def get_sensor_summary(self, channels):
        rows = []
        for channel in channels:
            if channel not in self.channels:
                raise ValueError(f"Unknown sensor channel: {channel}")
            values = self.observations[channel].to_numpy(float)
            valid = values[np.isfinite(values)]
            unit = "m" if channel.startswith("pressure_") else "L/s"
            facts = []
            if len(valid):
                for statistic, value in (("min", valid.min()), ("max", valid.max()), ("mean", valid.mean())):
                    facts.append(self.fact(f"sensor:{channel}:{statistic}", value, unit, channel, statistic=statistic))
            rows.append({"channel": channel, "unit": unit, "available": len(valid),
                         "missing": int(len(values) - len(valid)), "facts": facts})
        return {"sensors": rows, "flow_sign_meaning": "Sign is relative to model link orientation; it does not establish leakage, inflow or outflow."}

    def get_sensor_series(self, channels, offset=0, limit=8):
        # Bound channels, time points and serialization even when called outside dispatch.
        if not 1 <= len(channels) <= 4 or len(set(channels)) != len(channels):
            raise ValueError("Request one to four distinct channels.")
        if not 0 <= offset < len(self.observations) or not 1 <= limit <= 12:
            raise ValueError("Use a valid offset and one to twelve time points.")
        if any(channel not in self.channels for channel in channels):
            raise ValueError("Unknown sensor channel.")
        rows = []
        for index in range(offset, min(offset + limit, len(self.observations))):
            timestamp = str(self.observations.iloc[index]["timestamp_utc"])
            readings = []
            for channel in channels:
                value = self.observations.iloc[index][channel]
                readings.append(self.fact(f"reading:{channel}:{index}", value,
                    "m" if channel.startswith("pressure_") else "L/s", channel,
                    timestamp_utc=timestamp) if np.isfinite(value) else
                    {"channel": channel, "value": None, "timestamp_utc": timestamp, "missing": True})
            rows.append({"timestamp_utc": timestamp, "readings": readings})
        return {"rows": rows, "next_offset": offset + len(rows) if offset + len(rows) < len(self.observations) else None}

    def compare_hypotheses(self, limit=3):
        ranking = self.comparison["ranking"]
        visible = ranking[:limit]
        normal = next((r for r in ranking if r["scenario"] == "normal"), None)
        if normal and normal not in visible:
            visible = [*visible, normal]
        rows = []
        for row in visible:
            rank = ranking.index(row) + 1
            fact = self.fact(f"fit:{row['scenario']}", row["normalized_rmse"], "normalized_rmse",
                             pipe=row["leak_pipe"], rank=rank)
            rows.append({"pipe": row["leak_pipe"], "rank": rank, "fit": fact})
        return {"decision": self.comparison["decision"]["prediction"], "ranking": rows,
                "channels_used_by_detector": 209, "fit_meaning": "Error, not a probability. Lower is closer.",
                "causal_limits": "Aggregate fit does not establish which sensor caused the ranking or prove a hydraulic cause."}

    def get_observations(self):
        # Identify departures using every channel, but send only a bounded evidence shortlist.
        departures = []
        for channel in self.channels:
            group = "pressure" if channel.startswith("pressure_") else "flow"
            sensor = channel.split("_")[1]
            reference = np.median([p[group][sensor] for p in self.session.hypotheses["normal"]], axis=0)
            observed = self.observations[channel].to_numpy(float)
            scale = self.session.metadata["pressure_noise_sigma_m"] if group == "pressure" else max(.15, float(np.nanmedian(np.abs(observed))) * .02)
            valid = np.isfinite(observed)
            departure = float(np.sqrt(np.mean(((observed[valid] - reference[valid]) / scale) ** 2))) if valid.any() else -1
            departures.append((departure, channel))
        chosen = []
        for prefix in ("pressure_", "flow_"):
            chosen.extend(channel for _, channel in sorted(departures, reverse=True)
                          if channel.startswith(prefix) and channel not in chosen)
            chosen = chosen[:3] if prefix == "pressure_" else chosen[:6]
        return {"case_id": self.session.case_id, "pressure_channels": 92, "flow_channels": 117,
                "time_points": len(self.observations),
                "missing_readings": int(self.observations[self.channels].isna().sum().sum()),
                "shortlist_basis": "Largest standardized departures from time-aligned median normal profiles; supporting cues, not proven leak effects.",
                "evidence": self.get_sensor_summary(chosen),
                "details": "Use get_sensor_summary or get_sensor_series for any configured channel; full readings remain in the employee evidence view."}

    def schemas(self):
        channels = {"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 4, "uniqueItems": True}
        return [
            tool("get_observations", "Compact all-channel overview and six evidence channels; no bulk readings."),
            tool("compare_hypotheses", "Unchanged full-channel candidate ranking, compact by default.",
                 {"limit": {"type": "integer", "minimum": 1, "maximum": 25}}),
            tool("get_sensor_summary", "Signed min/max/mean and missing counts for one to four exact channel IDs.", {"channels": channels}, ["channels"]),
            tool("get_sensor_series", "Exact timestamped signed readings, with pagination. Null means missing, never zero.",
                 {"channels": channels, "offset": {"type": "integer", "minimum": 0, "maximum": 24},
                  "limit": {"type": "integer", "minimum": 1, "maximum": 12}}, ["channels"]),
            tool("get_network", "Configured sensor and candidate coverage, without hidden labels."),
            tool("get_operation_records", "Available operations records; none are bundled."),
        ]

    def dispatch(self, name, arguments):
        schema = next((s["function"] for s in self.schemas() if s["function"]["name"] == name), None)
        if schema is None:
            return {"error": "Tool is not allowed."}
        try:
            validate(arguments, schema["parameters"])
            if name == "get_network":
                return {"pressure_channels": 92, "flow_channels": 117,
                        "candidate_pipes": [r["leak_pipe"] for r in self.comparison["ranking"] if r["leak_pipe"]],
                        "limitations": "Single-leak candidate comparison; hydraulic causes and field conditions are not established."}
            if name == "get_operation_records":
                return {"records": [], "available": False}
            return getattr(self, name)(**arguments)
        except Exception as exc:
            from jsonschema import ValidationError
            if isinstance(exc, (ValueError, KeyError, TypeError, ValidationError)):
                return {"error": str(exc)[:200]}
            raise
