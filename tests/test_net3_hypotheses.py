import unittest

import numpy as np

from leakprobe.net3_benchmark import _sample_hypothesis_parameters


class HypothesisSamplingTests(unittest.TestCase):
    def test_sampled_parameters_cover_each_stratum_and_are_reproducible(self):
        ranges = {"diameter": (8.0, 25.0), "demand": (0.85, 1.15)}
        first = _sample_hypothesis_parameters(20, ranges, np.random.default_rng(2026))
        second = _sample_hypothesis_parameters(20, ranges, np.random.default_rng(2026))

        self.assertEqual(first, second)
        self.assertEqual(len(first), 20)
        for name, (low, high) in ranges.items():
            values = [row[name] for row in first]
            self.assertTrue(all(low <= value <= high for value in values))
            strata = {min(19, int((value - low) / (high - low) * 20)) for value in values}
            self.assertEqual(strata, set(range(20)))


if __name__ == "__main__":
    unittest.main()
