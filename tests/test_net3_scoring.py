import unittest

import numpy as np
import pandas as pd

from leakprobe.net3_tools import _decision_with_rejection, _score_profiles


class VectorizedProfileScoringTests(unittest.TestCase):
    def test_rejects_a_weak_leak_match_but_keeps_a_normal_winner(self):
        weak_leak = [{"scenario": "leak_pipe:105", "leak_pipe": "105",
                      "normalized_rmse": 70.0}]
        clear_normal = [{"scenario": "normal", "leak_pipe": None,
                         "normalized_rmse": 80.0}]

        rejected = _decision_with_rejection(weak_leak, 64.3)
        normal = _decision_with_rejection(clear_normal, 64.3)

        self.assertEqual(rejected["prediction"], "uncertain")
        self.assertTrue(rejected["rejected"])
        self.assertEqual(normal["prediction"], "normal")
        self.assertFalse(normal["rejected"])

    def test_scores_channels_equally_and_ignores_missing_samples(self):
        observations = pd.DataFrame({
            "pressure_1_m": [1.0, 3.0],
            "pressure_2_m": [np.nan, 4.0],
            "flow_10_lps": [2.0, 4.0],
        })
        models = [
            {"pressure": {"1": [1.0, 1.0], "2": [5.0, 5.0]},
             "flow": {"10": [2.0, 2.0]}},
            {"pressure": {"1": [3.0, 3.0], "2": [4.0, 4.0]},
             "flow": {"10": [4.0, 4.0]}},
        ]

        scores = _score_profiles(observations, models, ["1", "2"], ["10"], 1.0)

        flow_channel_error = ((2 / 0.15) ** 2) / 2
        expected = [
            np.sqrt((2.0 + 1.0 + flow_channel_error) / 3),
            np.sqrt((2.0 + 0.0 + flow_channel_error) / 3),
        ]
        np.testing.assert_allclose(scores, expected)

if __name__ == "__main__":
    unittest.main()
