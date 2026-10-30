"""Compatibility command for regenerating the canonical high-signal dataset."""
import argparse

from .generate_high_signal_dataset import generate
from .net3_benchmark import DEFAULT_PATTERNS_PER_SCENARIO, load_network
from .paths import NET3_DATA


def observation_columns(network):
    """Return every junction pressure and pipe flow column in Net3."""
    return ["timestamp_utc"] + [f"pressure_{node}_m" for node in network.junction_name_list] + [
        f"flow_{pipe}_lps" for pipe in network.pipe_name_list
    ]


def generate_full_dataset(seed=2026, patterns_per_scenario=DEFAULT_PATTERNS_PER_SCENARIO):
    network = load_network()
    columns = observation_columns(network)
    pressure_count = sum(column.startswith("pressure_") for column in columns)
    flow_count = sum(column.startswith("flow_") for column in columns)
    if (pressure_count, flow_count) != (92, 117):
        raise ValueError(f"Expected 92 pressure and 117 flow columns; found {pressure_count} and {flow_count}.")
    return generate(NET3_DATA, NET3_DATA, seed, patterns_per_scenario)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--patterns-per-scenario", type=int,
                        default=DEFAULT_PATTERNS_PER_SCENARIO)
    args = parser.parse_args()
    generate_full_dataset(args.seed, args.patterns_per_scenario)


if __name__ == "__main__":
    main()
