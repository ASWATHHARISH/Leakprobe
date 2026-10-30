"""Regenerate the sole supported complete-channel high-signal dataset."""
import argparse

from .generate_high_signal_dataset import generate
from .net3_benchmark import DEFAULT_PATTERNS_PER_SCENARIO
from .paths import NET3_DATA


def main():
    parser = argparse.ArgumentParser(
        description="Regenerate the 500-case high-signal Net3 feed with all 92 pressure and 117 flow channels."
    )
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--patterns-per-scenario", type=int,
                        default=DEFAULT_PATTERNS_PER_SCENARIO)
    args = parser.parse_args()
    generate(source=NET3_DATA, output=NET3_DATA, seed=args.seed,
             patterns_per_scenario=args.patterns_per_scenario)


if __name__ == "__main__":
    main()
