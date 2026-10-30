"""Generate the full-channel high-signal Net3 benchmark.

This keeps the source dataset's 500 case IDs, labels, split, and pipe assignments,
but uses large, long leaks and matching operating ranges across train and test.
It is a controlled benchmark, not a representative utility dataset.
"""
import argparse
import json
import shutil
from pathlib import Path

import numpy as np
import pandas as pd

from .net3_benchmark import (
    DEFAULT_PATTERNS_PER_SCENARIO,
    PRESSURE_SIGMA_M,
    _hypothesis_metadata,
    generate_hypothesis_bank,
    simulate_net3,
)
from .coverage import validate_full_channel_coverage
from .paths import NET3_DATA

SOURCE = NET3_DATA
OUT = NET3_DATA
LEAK_DIAMETER_MM = (28.0, 35.0)
LEAK_START_HOUR = (0.5, 1.5)
LEAK_DURATION_HOURS = (4.0, 4.5)
DEMAND_SCALE = (0.85, 1.15)
FLOW_NOISE_FRACTION = 0.02
FLOW_NOISE_FLOOR_LPS = 0.15
MISSING_FRACTION = 0.01
LEAK_PARAMETER_RANGES = {
    "leak_diameter_mm": LEAK_DIAMETER_MM,
    "start_hour": LEAK_START_HOUR,
    "leak_duration_hours": LEAK_DURATION_HOURS,
    "demand_scale": DEMAND_SCALE,
}
NORMAL_PARAMETER_RANGES = {"demand_scale": DEMAND_SCALE}


def generate(source=SOURCE, output=OUT, seed=2026,
             patterns_per_scenario=DEFAULT_PATTERNS_PER_SCENARIO):
    source = Path(source)
    output = Path(output)
    metadata = json.loads((source / "metadata.json").read_text(encoding="utf-8"))
    cases = json.loads((source / "cases.json").read_text(encoding="utf-8"))
    original_labels = json.loads((source / "truth_labels.json").read_text(encoding="utf-8"))
    staging = output.with_name(output.name + ".building")
    backup = output.with_name(output.name + ".previous")
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True, exist_ok=True)

    pressure_columns = [f"pressure_{node}_m" for node in metadata["monitor_pressure_nodes"]]
    flow_columns = [f"flow_{pipe}_lps" for pipe in metadata["flow_sensors"]]
    validate_full_channel_coverage(
        metadata, ["timestamp_utc", *pressure_columns, *flow_columns], "source metadata"
    )
    observed_columns = [*pressure_columns, *flow_columns]
    rng = np.random.default_rng(seed)
    labels = {}

    for case in cases:
        case_id = case["case_id"]
        truth_label = original_labels[case_id]
        demand_scale = float(rng.uniform(*DEMAND_SCALE))
        if truth_label["incident"] == "normal":
            diameter = start = duration = None
            truth = simulate_net3(demand_scale=demand_scale)
        else:
            diameter = float(rng.uniform(*LEAK_DIAMETER_MM))
            start = float(rng.uniform(*LEAK_START_HOUR))
            duration = float(rng.uniform(*LEAK_DURATION_HOURS))
            truth = simulate_net3(
                leak_pipe=truth_label["leak_pipe"],
                leak_diameter_mm=diameter,
                start_hour=start,
                leak_duration_hours=duration,
                demand_scale=demand_scale,
            )

        observed = truth[["timestamp_utc", *observed_columns]].copy()
        for column in pressure_columns:
            observed[column] += rng.normal(0, PRESSURE_SIGMA_M, len(observed))
        for column in flow_columns:
            sigma = max(FLOW_NOISE_FLOOR_LPS,
                        float(truth[column].abs().median()) * FLOW_NOISE_FRACTION)
            observed[column] += rng.normal(0, sigma, len(observed))
        missing = rng.random(observed[observed_columns].shape) < MISSING_FRACTION
        observed.loc[:, observed_columns] = observed[observed_columns].mask(missing)
        validate_full_channel_coverage(metadata, observed.columns, f"{case_id} observations")
        observed.to_csv(staging / case["observations_file"], index=False)

        labels[case_id] = {
            "split": truth_label["split"],
            "incident": truth_label["incident"],
            "leak_pipe": truth_label["leak_pipe"],
            "leak_diameter_mm": round(diameter, 3) if diameter is not None else None,
            "start_hour": round(start, 3) if start is not None else None,
            "leak_duration_hours": round(duration, 3) if duration is not None else None,
            "demand_scale": round(demand_scale, 4),
        }

    candidate_sensors = {
        "monitor_pressure_nodes": metadata["monitor_pressure_nodes"],
        "flow_sensors": metadata["flow_sensors"],
        "candidate_pipes": metadata["candidate_pipes_by_split"],
    }
    hypotheses = generate_hypothesis_bank(
        candidate_sensors,
        patterns_per_scenario=patterns_per_scenario,
        seed=seed,
        leak_parameter_ranges=LEAK_PARAMETER_RANGES,
        normal_parameter_ranges=NORMAL_PARAMETER_RANGES,
    )

    (staging / "cases.json").write_text(json.dumps(cases, indent=2), encoding="utf-8")
    (staging / "truth_labels.json").write_text(json.dumps(labels, indent=2), encoding="utf-8")
    high_signal_metadata = {
        "dataset_kind": "complete_full_coverage_high_signal",
        "dataset_variant": "high-signal Net3 benchmark",
        "network": metadata["network"],
        "nodes": metadata["nodes"],
        "links": metadata["links"],
        "junctions": metadata["junctions"],
        "pipes": metadata["pipes"],
        "case_counts": metadata["case_counts"],
        "candidate_pipes_by_split": metadata["candidate_pipes_by_split"],
        "monitor_pressure_nodes": metadata["monitor_pressure_nodes"],
        "flow_sensors": metadata["flow_sensors"],
        "pressure_column_count": len(metadata["monitor_pressure_nodes"]),
        "flow_column_count": len(metadata["flow_sensors"]),
        "observation_columns": 1 + len(metadata["monitor_pressure_nodes"]) + len(metadata["flow_sensors"]),
        "observation_coverage": "Pressure at all 92 junctions and flow in all 117 pipes at every timestep.",
        "duration_hours": metadata["duration_hours"],
        "timestep_minutes": metadata["timestep_minutes"],
        "pressure_noise_sigma_m": PRESSURE_SIGMA_M,
        "flow_noise_sigma": "max(0.15 L/s, 2% of median absolute flow)",
        "telemetry_missing_fraction": MISSING_FRACTION,
        "generation_seed": seed,
        "truth_parameter_ranges_by_split": {
            "train": {name: list(bounds) for name, bounds in LEAK_PARAMETER_RANGES.items()},
            "test": {name: list(bounds) for name, bounds in LEAK_PARAMETER_RANGES.items()},
            "normal": {name: list(bounds) for name, bounds in NORMAL_PARAMETER_RANGES.items()},
        },
        **_hypothesis_metadata(patterns_per_scenario, LEAK_PARAMETER_RANGES,
                               NORMAL_PARAMETER_RANGES),
        "reference_profile_total": sum(len(profiles) for profiles in hypotheses.values()),
        "parameters": {
            "leak_diameter_mm": list(LEAK_DIAMETER_MM),
            "leak_start_hour": list(LEAK_START_HOUR),
            "leak_duration_hours": list(LEAK_DURATION_HOURS),
            "demand_scale_for_both_splits": list(DEMAND_SCALE),
        },
        "limitations": (
            "Leaks are intentionally large and long, and train/test operating ranges are aligned. "
            "This is a controlled high-signal benchmark; results do not establish field performance."
        ),
    }
    (staging / "metadata.json").write_text(
        json.dumps(high_signal_metadata, indent=2), encoding="utf-8"
    )
    (staging / "hypotheses.json").write_text(
        json.dumps(hypotheses, separators=(",", ":")), encoding="utf-8"
    )
    if backup.exists():
        shutil.rmtree(backup)
    if output.exists():
        output.rename(backup)
    try:
        staging.rename(output)
    except OSError:
        if backup.exists() and not output.exists():
            backup.rename(output)
        raise
    if backup.exists():
        shutil.rmtree(backup)
    counts = {
        split: {label: sum(row["split"] == split and row["incident"] == label
                           for row in labels.values())
                for label in ("normal", "single_leak")}
        for split in ("train", "test")
    }
    print(f"Generated {len(cases)} high-signal cases at {output}")
    print(f"Split counts: {json.dumps(counts, sort_keys=True)}")
    print("Every stored case contains 92 pressure and 117 flow channels.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--output", type=Path, default=OUT)
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--patterns-per-scenario", type=int,
                        default=DEFAULT_PATTERNS_PER_SCENARIO)
    args = parser.parse_args()
    generate(source=args.source, output=args.output, seed=args.seed,
             patterns_per_scenario=args.patterns_per_scenario)
