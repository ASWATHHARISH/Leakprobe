"""Reproducible synthetic cases on the EPA WNTR Net3 example network."""
import math

import numpy as np
import pandas as pd
import wntr
from .paths import DATA

NET3_FILE = DATA / "networks" / "Net3.inp"
DURATION_HOURS = 6
STEP_SECONDS = 900
N_HYPOTHESES = 24
PRESSURE_SIGMA_M = 0.08
DEFAULT_PATTERNS_PER_SCENARIO = 24
LEAK_HYPOTHESIS_RANGES = {
    "leak_diameter_mm": (8.0, 25.0),
    "start_hour": (0.5, 1.5),
    "leak_duration_hours": (3.0, 4.5),
    "demand_scale": (0.85, 1.15),
}
NORMAL_HYPOTHESIS_RANGES = {"demand_scale": (0.85, 1.15)}


def load_network():
    if not NET3_FILE.exists():
        raise FileNotFoundError(f"Net3 input file not found: {NET3_FILE}")
    wn = wntr.network.WaterNetworkModel(str(NET3_FILE))
    wn.options.time.duration = DURATION_HOURS * 3600
    wn.options.time.hydraulic_timestep = STEP_SECONDS
    wn.options.time.report_timestep = STEP_SECONDS
    wn.options.hydraulic.demand_model = "PDD"
    wn.options.hydraulic.minimum_pressure = 0
    wn.options.hydraulic.required_pressure = 15
    wn.options.hydraulic.pressure_exponent = 0.5
    return wn


def choose_sensors(wn, seed=2026):
    """Return the complete supported Net3 observation layout."""
    pipes = [n for n in wn.pipe_name_list if wn.get_link(n).diameter <= 0.9144]
    pipe_coords = {}
    for name in pipes:
        link = wn.get_link(name)
        a = np.asarray(wn.get_node(link.start_node_name).coordinates, dtype=float)
        b = np.asarray(wn.get_node(link.end_node_name).coordinates, dtype=float)
        pipe_coords[name] = (a+b)/2
    first_pipe = max(pipes, key=lambda n: (wn.get_link(n).diameter, n))
    candidates = [first_pipe]
    remaining_pipes = set(pipes) - {first_pipe}
    while remaining_pipes and len(candidates) < min(N_HYPOTHESES, len(pipes)):
        pick = max(remaining_pipes, key=lambda n: (
            min(np.linalg.norm(pipe_coords[n]-pipe_coords[s]) for s in candidates), n))
        candidates.append(pick)
        remaining_pipes.remove(pick)
    rng = np.random.default_rng(seed)
    rng.shuffle(candidates)
    n_train = max(2, round(len(candidates) * 0.7))
    split_pipes = {"train": sorted(candidates[:n_train]), "test": sorted(candidates[n_train:])}

    return {"monitor_pressure_nodes": sorted(wn.junction_name_list),
            "flow_sensors": sorted(wn.pipe_name_list),
            "candidate_pipes": split_pipes}


def simulate_net3(leak_pipe=None, leak_diameter_mm=16.0, start_hour=1.0,
                  leak_duration_hours=4.0, demand_scale=1.0, seed=0,
                  sensors=None):
    """Simulate normal operation or one leak; return all node pressures and pipe flows."""
    wn = load_network()
    if leak_pipe is not None:
        if leak_pipe not in wn.pipe_name_list:
            raise ValueError(f"Unknown Net3 pipe: {leak_pipe}")
        values = (leak_diameter_mm, start_hour, leak_duration_hours, demand_scale)
        if not all(math.isfinite(float(x)) for x in values):
            raise ValueError("Leak and demand parameters must be finite.")
        if not 4 <= leak_diameter_mm <= 40:
            raise ValueError("Leak diameter must be between 4 and 40 mm.")
        if not 0 <= start_hour < DURATION_HOURS or not 0 < leak_duration_hours <= DURATION_HOURS-start_hour:
            raise ValueError("Leak start and duration must fit inside the six-hour run.")
        if not 0.5 <= demand_scale <= 1.5:
            raise ValueError("Demand scale must be between 0.5 and 1.5.")

    if not math.isfinite(float(demand_scale)) or not 0.5 <= demand_scale <= 1.5:
        raise ValueError("Demand scale must be between 0.5 and 1.5.")
    if demand_scale != 1:
        for _, node in wn.junctions():
            for demand in node.demand_timeseries_list:
                demand.base_value *= demand_scale

    if leak_pipe is not None:
        leak_node = f"LP_LEAK_{leak_pipe}"
        new_pipe = f"LP_AFTER_{leak_pipe}"
        wn = wntr.morph.split_pipe(wn, leak_pipe, new_pipe, leak_node, split_at_point=0.5)
        wn.get_node(leak_node).add_leak(
            wn,
            area=math.pi * (leak_diameter_mm / 2000) ** 2,
            discharge_coeff=0.75,
            start_time=start_hour * 3600,
            end_time=(start_hour + leak_duration_hours) * 3600,
        )

    result = wntr.sim.WNTRSimulator(wn).run_sim(convergence_error=True)
    pressure = result.node["pressure"]
    flow = result.link["flowrate"]
    columns = {"timestamp_utc": pd.Timestamp("2026-01-01T00:00:00Z")
               + pd.to_timedelta(pressure.index, unit="s")}
    for node in wn.junction_name_list:
        if node in pressure:
            columns[f"pressure_{node}_m"] = pressure[node].to_numpy()
    for pipe in wn.pipe_name_list:
        if pipe in flow:
            columns[f"flow_{pipe}_lps"] = flow[pipe].to_numpy() * 1000
    return pd.DataFrame(columns)


def _sensor_columns(sensors):
    pressure_cols = [f"pressure_{n}_m" for n in sensors["monitor_pressure_nodes"]]
    flow_cols = [f"flow_{n}_lps" for n in sensors["flow_sensors"]]
    return pressure_cols, flow_cols, []


def _sample_hypothesis_parameters(pattern_count, parameter_ranges, rng):
    """Return reproducible stratified samples spanning each parameter range."""
    samples = {}
    for name, (low, high) in parameter_ranges.items():
        strata = (rng.permutation(pattern_count) + rng.random(pattern_count)) / pattern_count
        samples[name] = low + strata * (high - low)
    return [
        {name: float(values[index]) for name, values in samples.items()}
        for index in range(pattern_count)
    ]


def _serialize_hypothesis(prediction, parameters, pressure_cols, point_cols, flow_cols):
    return {
        "parameters": parameters,
        "pressure": {c.removeprefix("pressure_").removesuffix("_m"): prediction[c].round(5).tolist()
                     for c in pressure_cols + point_cols},
        "flow": {c.removeprefix("flow_").removesuffix("_lps"): prediction[c].round(5).tolist()
                 for c in flow_cols},
    }


def generate_hypothesis_bank(sensors, patterns_per_scenario=DEFAULT_PATTERNS_PER_SCENARIO,
                             seed=2026, leak_parameter_ranges=None,
                             normal_parameter_ranges=None):
    """Simulate a dense reference bank for every candidate pipe and normal operation."""
    if isinstance(patterns_per_scenario, bool) or patterns_per_scenario < 1:
        raise ValueError("patterns_per_scenario must be a positive integer.")
    pressure_cols, flow_cols, point_cols = _sensor_columns(sensors)
    leak_parameter_ranges = leak_parameter_ranges or LEAK_HYPOTHESIS_RANGES
    normal_parameter_ranges = normal_parameter_ranges or NORMAL_HYPOTHESIS_RANGES
    candidate_pipes = sorted(set(sensors["candidate_pipes"]["train"] +
                                 sensors["candidate_pipes"]["test"]))
    rng = np.random.default_rng(seed + 1)
    hypotheses = {}

    for pipe in candidate_pipes:
        variants = []
        parameters_list = _sample_hypothesis_parameters(
            patterns_per_scenario, leak_parameter_ranges, rng)
        for parameters in parameters_list:
            prediction = simulate_net3(
                pipe, parameters["leak_diameter_mm"], parameters["start_hour"],
                parameters["leak_duration_hours"], parameters["demand_scale"],
                sensors=sensors)
            variants.append(_serialize_hypothesis(
                prediction, {name: round(value, 5) for name, value in parameters.items()},
                pressure_cols, point_cols, flow_cols))
        hypotheses[pipe] = variants

    normal_variants = []
    parameters_list = _sample_hypothesis_parameters(
        patterns_per_scenario, normal_parameter_ranges, rng)
    for parameters in parameters_list:
        prediction = simulate_net3(demand_scale=parameters["demand_scale"], sensors=sensors)
        normal_variants.append(_serialize_hypothesis(
            prediction, {name: round(value, 5) for name, value in parameters.items()},
            pressure_cols, point_cols, flow_cols))
    hypotheses["normal"] = normal_variants
    return hypotheses


def _hypothesis_metadata(patterns_per_scenario, leak_parameter_ranges=None,
                         normal_parameter_ranges=None):
    leak_parameter_ranges = leak_parameter_ranges or LEAK_HYPOTHESIS_RANGES
    normal_parameter_ranges = normal_parameter_ranges or NORMAL_HYPOTHESIS_RANGES
    return {
        "hypothesis_patterns_per_leak_pipe": patterns_per_scenario,
        "normal_hypothesis_patterns": patterns_per_scenario,
        "hypothesis_parameter_sampling": "Seeded stratified sampling across the stated ranges.",
        "hypothesis_parameter_ranges": {
            "leak": {name: list(bounds) for name, bounds in leak_parameter_ranges.items()},
            "normal": {name: list(bounds) for name, bounds in normal_parameter_ranges.items()},
        },
    }
