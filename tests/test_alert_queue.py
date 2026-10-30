import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from leakprobe.ui.alert_queue import assess_window, load_or_assess_queue


class QueueTests(unittest.TestCase):
    def test_invalid_input_is_unavailable_never_cleared_as_normal(self):
        with patch("leakprobe.ui.alert_queue.Net3Investigation", side_effect=ValueError("Invalid time grid")):
            result = assess_window("case_001")
        self.assertEqual(result["prediction"], "unavailable")
        self.assertIsNone(result["alert_id"])

    def test_complete_cache_is_reused_without_detector_calls(self):
        cases = [{"case_id": "case_001"}, {"case_id": "case_002"}]
        rows = [{"case_id": case["case_id"], "prediction": "leak"} for case in cases]
        with tempfile.TemporaryDirectory() as tmp:
            with patch("leakprobe.ui.alert_queue.assess_window", side_effect=rows) as detector:
                first = load_or_assess_queue(cases, "source-a", tmp)
                self.assertEqual(detector.call_count, 2)
            with patch("leakprobe.ui.alert_queue.assess_window") as detector:
                self.assertEqual(load_or_assess_queue(cases, "source-a", tmp), first)
                detector.assert_not_called()
            self.assertEqual(len(list(Path(tmp).glob("*.json"))), 1)
            self.assertFalse(list(Path(tmp).glob("*.tmp")))

    def test_partial_cache_preserved_and_source_changes_use_new_paths(self):
        cases = [{"case_id": "case_001"}]
        row = {"case_id": "case_001", "prediction": "normal"}
        with tempfile.TemporaryDirectory() as tmp:
            original = Path(tmp) / "monitoring_queue_old.json"
            original.write_text('{"records":', encoding="utf-8")
            damaged = original.read_bytes()
            with patch("leakprobe.ui.alert_queue.assess_window", return_value=row):
                self.assertEqual(load_or_assess_queue(cases, "old", tmp), [row])
                self.assertEqual(load_or_assess_queue(cases, "new", tmp), [row])
            self.assertEqual(original.read_bytes(), damaged)
            self.assertEqual(json.loads((Path(tmp) / "monitoring_queue_new.json").read_text())["records"], [row])

    def test_changed_cached_records_cannot_silently_replace_detector_results(self):
        cases = [{"case_id": "case_001"}]
        row = {"case_id": "case_001", "prediction": "leak"}
        with tempfile.TemporaryDirectory() as tmp:
            with patch("leakprobe.ui.alert_queue.assess_window", return_value=row):
                load_or_assess_queue(cases, "s", tmp)
            path = Path(tmp) / "monitoring_queue_s.json"
            saved = json.loads(path.read_text())
            saved["records"][0]["prediction"] = "normal"
            path.write_text(json.dumps(saved))
            with patch("leakprobe.ui.alert_queue.assess_window", return_value=row) as detector:
                self.assertEqual(load_or_assess_queue(cases, "s", tmp), [row])
                detector.assert_called_once()


if __name__ == "__main__":
    unittest.main()
