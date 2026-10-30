import unittest

from leakprobe.evaluate_net3 import _binary_prediction, classification_metrics, select_cases


class ClassificationMetricTests(unittest.TestCase):
    def test_rejected_case_counts_as_no_alarm_for_binary_metrics(self):
        self.assertEqual(_binary_prediction({"prediction": "uncertain"}), "normal")

    def test_select_cases_supports_each_split_and_all_cases(self):
        cases = [
            {"case_id": "case_000", "split": "train"},
            {"case_id": "case_400", "split": "test"},
        ]

        self.assertEqual(select_cases(cases, "train"), ["case_000"])
        self.assertEqual(select_cases(cases, "test"), ["case_400"])
        self.assertEqual(select_cases(cases, "all"), ["case_000", "case_400"])

    def test_confusion_counts_and_metrics_for_mixed_predictions(self):
        actual = ["leak"] * 80 + ["normal"] * 20
        predicted = ["leak"] * 64 + ["normal"] * 16 + ["leak"] * 5 + ["normal"] * 15

        result = classification_metrics(actual, predicted)

        self.assertEqual(result["confusion_matrix"], {"tp": 64, "fn": 16, "fp": 5, "tn": 15})
        self.assertAlmostEqual(result["recall"], 0.8)
        self.assertAlmostEqual(result["precision"], 64 / 69)
        self.assertAlmostEqual(result["specificity"], 0.75)
        self.assertAlmostEqual(result["balanced_accuracy"], 0.775)
        self.assertAlmostEqual(result["accuracy"], 0.79)

    def test_undefined_precision_when_no_cases_are_predicted_as_leaks(self):
        result = classification_metrics(["leak", "normal"], ["normal", "normal"])

        self.assertIsNone(result["precision"])
        self.assertEqual(result["confusion_matrix"], {"tp": 0, "fn": 1, "fp": 0, "tn": 1})


if __name__ == "__main__":
    unittest.main()
