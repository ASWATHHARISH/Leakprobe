"""Allowlisted investigation tools for the complete Net3 sensor feed."""
import json
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd
from jsonschema import ValidationError, validate

from .coverage import validate_full_channel_coverage
from .paths import NET3_DATA
from .tool_schemas import tool

DATA = NET3_DATA


def _read_json(path):
    if not path.exists():
        raise ValueError("The full Net3 dataset is missing. Run python generate_data.py.")
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _read_hypotheses(data_dir=DATA):
    """Load a dataset's reference bank once per evaluator process."""
    return _read_json(Path(data_dir) / "hypotheses.json")


def net3_tool_schemas(data_dir=DATA):
    _read_json(Path(data_dir) / "metadata.json")
    return [
        tool("get_observations", "Read this case's timestamped full-coverage pressure and flow time series."),
        tool("get_network", "Read Net3 network size, all observed channels, and candidate leak pipes."),
        tool("get_operation_records", "Read available operations records. None are bundled with this benchmark."),
        tool("compare_hypotheses", "Score candidate leak-pipe scenarios against observations; a weak top leak fit may be rejected as uncertain. Scores are fit only, not probabilities."),
    ]


def _score_profiles(observations, models, pressure_nodes, flow_pipes, pressure_sigma_m):
    """Compare full channel sets using per-channel normalized fit error."""
    model_count = len(models)
    channel_errors = []

    pressure_columns = [f"pressure_{node}_m" for node in pressure_nodes]
    observed = observations[pressure_columns].to_numpy(dtype=float, na_value=np.nan).T
    valid_channels = np.isfinite(observed).any(axis=1)
    if valid_channels.any():
        predicted = np.asarray([
            [model["pressure"][str(node)] for node in pressure_nodes]
            for model in models
        ], dtype=float)
        valid = np.isfinite(observed)
        residuals = (observed[None, :, :] - predicted) / pressure_sigma_m
        squared = np.where(valid[None, :, :], np.square(residuals), 0.0)
        counts = valid.sum(axis=1)
        errors = squared.sum(axis=2) / np.maximum(counts[None, :], 1)
        channel_errors.append(errors[:, valid_channels])

    flow_columns = [f"flow_{pipe}_lps" for pipe in flow_pipes]
    observed = observations[flow_columns].to_numpy(dtype=float, na_value=np.nan).T
    valid_channels = np.isfinite(observed).any(axis=1)
    if valid_channels.any():
        predicted = np.asarray([
            [model["flow"][str(pipe)] for pipe in flow_pipes]
            for model in models
        ], dtype=float)
        valid = np.isfinite(observed)
        magnitudes = np.where(valid, np.abs(observed), np.nan)
        with np.errstate(invalid="ignore"):
            sigma = np.maximum(0.15, np.nanmedian(magnitudes, axis=1) * 0.02)
        sigma = np.where(np.isfinite(sigma), sigma, 0.15)
        residuals = (observed[None, :, :] - predicted) / sigma[None, :, None]
        squared = np.where(valid[None, :, :], np.square(residuals), 0.0)
        counts = valid.sum(axis=1)
        errors = squared.sum(axis=2) / np.maximum(counts[None, :], 1)
        channel_errors.append(errors[:, valid_channels])

    if not channel_errors:
        return np.full(model_count, np.inf)
    return np.sqrt(np.concatenate(channel_errors, axis=1).mean(axis=1))


def _decision_with_rejection(ranking, rejection_threshold):
    """Return an actionable class, abstaining on a weak leak fit when configured."""
    if not ranking:
        return {"prediction": "uncertain", "rejected": True,
                "best_fit_score": None, "rejection_threshold": rejection_threshold}
    winner = ranking[0]
    score = winner["normalized_rmse"]
    is_leak = winner["scenario"] != "normal"
    rejected = (is_leak and rejection_threshold is not None
                and score > rejection_threshold)
    return {
        "prediction": "uncertain" if rejected else "leak" if is_leak else "normal",
        "rejected": rejected,
        "best_scenario": winner["scenario"],
        "best_fit_score": score,
        "rejection_threshold": rejection_threshold,
        "reason": ("Best leak fit is above the configured threshold; request review."
                   if rejected else "Best-ranked hypothesis accepted."),
    }


class Net3Investigation:
    def __init__(self, case_id=None, data_dir=DATA, rejection_threshold=None):
        self.data_dir = Path(data_dir)
        self.metadata = _read_json(self.data_dir / "metadata.json")
        validate_full_channel_coverage(
            self.metadata,
            [*(f"pressure_{node}_m" for node in self.metadata.get("monitor_pressure_nodes", [])),
             *(f"flow_{pipe}_lps" for pipe in self.metadata.get("flow_sensors", []))],
            "Net3 metadata",
        )
        self.rejection_threshold = (self.metadata.get("rejection_threshold")
                                    if rejection_threshold is None
                                    else rejection_threshold)
        self.cases = _read_json(self.data_dir / "cases.json")
        test_cases = [case["case_id"] for case in self.cases if case["split"] == "test"]
        self.case_id = case_id or (test_cases[0] if test_cases else None)
        available = {case["case_id"] for case in self.cases}
        if self.case_id not in available:
            raise ValueError(f"Unknown Net3 case id: {self.case_id}")
        case = next(c for c in self.cases if c["case_id"] == self.case_id)
        self.split = case["split"]
        self.observations = pd.read_csv(self.data_dir / case["observations_file"])
        validate_full_channel_coverage(
            self.metadata, self.observations.columns, f"{self.case_id} observations"
        )
        self.hypotheses = _read_hypotheses(str(self.data_dir.resolve()))

    def get_observations(self):
        rows = self.observations.astype(object).where(pd.notna(self.observations), None).to_dict("records")
        return {
            "case_id": self.case_id,
            "provenance": "Net3 full-coverage sensor feed",
            "pressure_channel_count": 92,
            "flow_channel_count": 117,
            "missing_values": "Missing readings are represented as null; channel definitions remain complete.",
            "readings": rows,
        }

    def get_network(self):
        split_pipes = self.metadata["candidate_pipes_by_split"][self.split]
        return {
            "network": self.metadata["network"], "case_id": self.case_id,
            "nodes": self.metadata["nodes"], "links": self.metadata["links"],
            "junctions": self.metadata["junctions"], "pipes": self.metadata["pipes"],
            "monitor_pressure_nodes": self.metadata["monitor_pressure_nodes"],
            "flow_sensors": self.metadata["flow_sensors"],
            "pressure_channel_count": len(self.metadata["monitor_pressure_nodes"]),
            "flow_channel_count": len(self.metadata["flow_sensors"]),
            "candidate_leak_pipes": split_pipes,
            "normal_operation_included": True,
            "rejection_threshold": self.rejection_threshold,
            "assumptions": "One leak; six-hour WNTR simulation; 15-minute reporting; demand scale, leak size, and onset vary by case.",
        }

    def get_operation_records(self):
        return []

    def compare_hypotheses(self):
        pressure_nodes = self.metadata["monitor_pressure_nodes"]
        flow_pipes = self.metadata["flow_sensors"]
        candidates = [*self.metadata["candidate_pipes_by_split"][self.split], "normal"]
        ranking = []
        for pipe in candidates:
            models = self.hypotheses[pipe]
            scores = _score_profiles(
                self.observations, models, pressure_nodes, flow_pipes,
                self.metadata["pressure_noise_sigma_m"],
            )
            best_index = int(np.argmin(scores))
            model = models[best_index]
            ranking.append({
                "scenario": "normal" if pipe == "normal" else f"leak_pipe:{pipe}",
                "leak_pipe": None if pipe == "normal" else pipe,
                "normalized_rmse": float(scores[best_index]),
                "best_fit_parameters": model["parameters"],
            })
        ranking.sort(key=lambda row: row["normalized_rmse"])
        if len(ranking) > 1:
            relative_gap = ((ranking[1]["normalized_rmse"] - ranking[0]["normalized_rmse"])
                            / max(ranking[1]["normalized_rmse"], 1e-9))
        else:
            relative_gap = None
        return {
            "ranking": ranking,
            "decision": _decision_with_rejection(ranking, self.rejection_threshold),
            "measurements_used": "All 92 pressure and 117 flow channels in the case feed.",
            "score_meaning": "Standardized fit across all pressure and flow channels and candidate pipes in this split; not a probability.",
            "model_mismatch": "Each pipe is fit across sampled simulation parameters in the dataset metadata. Train/test cases use separate candidate-pipe groups and truth-parameter ranges; scores are fit diagnostics, not calibrated probabilities.",
            "leading_scenarios_are_close": relative_gap is not None and relative_gap < 0.1,
            "relative_fit_gap": round(relative_gap, 4) if relative_gap is not None else None,
        }


def dispatch_net3(session, name, arguments):
    definitions = {item["function"]["name"]: item["function"]
                   for item in net3_tool_schemas(session.data_dir)}
    if name not in definitions:
        return {"error": "Tool is not allowed."}
    try:
        validate(arguments, definitions[name]["parameters"])
        return getattr(session, name)(**arguments)
    except (ValidationError, ValueError, KeyError) as exc:
        return {"error": str(exc)[:500]}
