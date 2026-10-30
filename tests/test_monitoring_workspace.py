"""Monitoring presentation regressions; no providers, real review DB or scoring calls."""
import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd
from streamlit.testing.v1 import AppTest

from leakprobe.ui.alert_queue import assess_window, record_name
from leakprobe.ui.alert_store import AlertStore
from leakprobe.ui.data_access import load_monitoring_snapshot, load_network_layout
from leakprobe.ui.monitoring_records import filter_records, page_records
from leakprobe.ui.monitoring_views import latest_sensor_values, workspace_map_spec
from leakprobe.ui.operations import build_alert


def records():
    return [{"case_id": f"case_{i:03}", "record": record_name(f"case_{i:03}"),
             "alert_id": str(i), "prediction": "leak" if i % 2 else "normal",
             "candidate_pipe": "202" if i % 2 else None, "latest": "2026-01-01T06:00:00Z"}
            for i in range(500)]


class RecordBrowserTests(unittest.TestCase):
    def test_every_record_is_reachable_without_duplicates_or_mutation(self):
        queue = records()
        original = copy.deepcopy(queue)
        found = []
        for page in range(1, 51):
            rows, current, pages = page_records(filter_records(queue, {}), page)
            self.assertEqual((current, pages), (page, 50))
            self.assertEqual(len(rows), 10)
            found.extend(row["case_id"] for row in rows)
        self.assertEqual(found, [row["case_id"] for row in queue])
        self.assertEqual(len(set(found)), 500)
        self.assertEqual(queue, original)
        self.assertEqual(page_records(queue, 999)[1], 50)
        self.assertEqual(page_records([], 0), ([], 1, 1))

    def test_attention_status_and_search_filters(self):
        queue = records()
        statuses = {"1": "No leak", "3": "Leak confirmed", "5": "Under review"}
        attention = filter_records(queue, statuses, "Needs attention")
        self.assertEqual(len(attention), 248)
        self.assertNotIn("case_001", [row["case_id"] for row in attention])
        self.assertEqual([row["case_id"] for row in filter_records(queue, statuses, search="under review 202")], ["case_005"])
        self.assertEqual(len(filter_records(queue, statuses, "No alert")), 250)
        self.assertEqual(len(filter_records(queue, statuses, "Suspected leak")), 250)
        self.assertFalse(filter_records(queue, statuses, search="not-found"))

    def test_paging_search_selection_and_empty_state_in_ui(self):
        with patch("leakprobe.ui.monitoring_records.review_statuses", return_value={}):
            app = AppTest.from_string("from test_monitoring_workspace import records\n"
                "from leakprobe.ui.monitoring_records import render_monitoring_records\n"
                "render_monitoring_records(records(), None, 'case_405')").run()
            self.assertFalse(app.exception)
            self.assertEqual(len(app.selectbox[0].options), 500)
            self.assertEqual(app.selectbox[0].value, "case_405")
            app.number_input[0].set_value(50).run()
            self.assertFalse(app.exception)
            self.assertEqual(app.dataframe[0].value["Record"].iloc[-1], "LP-0499")
            self.assertEqual(app.selectbox[0].value, "case_405")
            app.text_input[0].set_value("LP-0499").run()
            self.assertEqual(app.selectbox[0].value, "case_499")
            self.assertEqual(app.number_input[0].value, 1)
            app.text_input[0].set_value("").run()
            self.assertEqual(app.selectbox[0].value, "case_499")
            app.text_input[0].set_value("not-found").run()
            self.assertFalse(app.exception)
            self.assertFalse(app.selectbox)
            self.assertTrue(any("No records match" in message.value for message in app.info))


class WorkspaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.queue = [assess_window("case_405"), assess_window("case_402"), assess_window("case_004")]

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = AlertStore(Path(self.tmp.name) / "reviews.db")
        for target, value in (("AlertStore", self.store), ("load_monitoring_queue", self.queue),
                              ("availability", (True, "Ready"))):
            p = patch("leakprobe.ui.employee_dashboard." + target, return_value=value)
            p.start()
            self.addCleanup(p.stop)
        self.paid_patch = patch("leakprobe.ui.employee_dashboard.run_investigation")
        self.paid = self.paid_patch.start()
        self.addCleanup(self.paid_patch.stop)

    def app(self):
        return AppTest.from_string("from leakprobe.ui.employee_dashboard import render_monitoring_dashboard\n"
                                   "render_monitoring_dashboard()").run(timeout=40)

    def test_four_tabs_keep_record_and_no_implicit_ai_requests(self):
        app = self.app()
        self.assertFalse(app.exception)
        self.assertEqual([tab.label for tab in app.tabs], ["Overview", "AI Investigation", "Sensor Analysis", "Employee Review"])
        self.assertTrue(any(heading.value == "Network schematic" for heading in app.tabs[0].subheader))
        self.assertEqual([b.label for b in app.tabs[1].button], ["Run AI Investigation"])
        self.assertTrue(any("Affected sensor readings" in item.value for item in app.tabs[2].markdown))
        self.assertTrue(any(b.label == "Save review" for b in app.tabs[3].button))
        app.selectbox(key="monitoring_record_id").set_value("case_402").run(timeout=40)
        # Native Streamlit tabs switch client-side. Rerendering all four also must not request inference.
        for _ in app.tabs:
            app.run(timeout=40)
            self.assertEqual(app.selectbox(key="monitoring_record_id").value, "case_402")
            self.assertTrue(any("LP-0402" in heading.value for heading in app.subheader))
        self.paid.assert_not_called()
        self.assertTrue(any("Back to monitoring records" in item.value for item in app.markdown))

    def test_saved_validated_report_reused_without_paid_calls(self):
        from test_nemotron_evidence import validated_result
        from leakprobe.net3_tools import Net3Investigation
        snapshot = load_monitoring_snapshot("case_405")
        saved = validated_result(Net3Investigation("case_405"))
        saved.update(build_alert(snapshot))
        with patch("leakprobe.ui.employee_dashboard.load_llm_trace_history", return_value=[saved]):
            app = self.app()
            self.assertFalse(app.exception)
            self.assertTrue(any("cited facts checked" in element.value for element in app.tabs[1].success))
            technical = next(element for element in app.tabs[1].expander if element.label == "Technical tool trace")
            self.assertFalse(technical.proto.expanded)
            self.assertTrue(any("recorded requests" in c.value for c in technical.caption))
            app.run(timeout=40)
        self.paid.assert_not_called()

    def test_acknowledgment_and_field_confirmation_persist_separately(self):
        app = self.app()
        next(field for field in app.text_input if field.label == "Acknowledged by").set_value("Operator A")
        next(b for b in app.button if b.label == "Save acknowledgment").click().run(timeout=40)
        self.assertFalse(app.exception)
        alert = self.store.alerts()[0]
        reviews = [event for event in self.store.events(alert["alert_id"]) if event["kind"] == "review"]
        self.assertEqual([event["status"] for event in reviews], ["Acknowledged"])
        self.assertTrue(any("Review saved" in message.value for message in app.success))
        self.assertEqual(next(field for field in app.text_input if field.label == "Reviewer name").value, "Operator A")
        next(field for field in app.text_input if field.label == "Reviewer name").set_value("Field reviewer")
        next(field for field in app.selectbox if field.label == "Review action").set_value("Leak confirmed")
        app.text_area[0].set_value("Verified using approved field procedure.")
        next(b for b in app.button if b.label == "Save review").click().run(timeout=40)
        self.assertFalse(app.exception)
        # Reopen storage to establish disk persistence, not just widget state.
        reopened = AlertStore(self.store.path)
        reviews = [event for event in reopened.events(alert["alert_id"]) if event["kind"] == "review"]
        self.assertEqual([event["status"] for event in reviews], ["Acknowledged", "Leak confirmed"])
        self.assertEqual(reviews[-1]["notes"], "Verified using approved field procedure.")
        self.assertTrue(all(event["at"].endswith("+00:00") for event in reviews))
        self.assertTrue(any("**Leak confirmed**" == item.value for item in app.markdown))
        self.paid.assert_not_called()

    def test_failed_persistence_never_reports_success(self):
        app = self.app()
        next(field for field in app.text_input if field.label == "Reviewer name").set_value("Operator")
        with patch.object(self.store, "review", side_effect=OSError("disk unavailable")):
            next(b for b in app.button if b.label == "Save review").click().run(timeout=40)
        self.assertFalse(app.exception)
        self.assertFalse(any("Review saved" in element.value for element in app.success))
        self.assertTrue(any("not saved" in element.value for element in app.error))
        self.assertFalse([event for event in self.store.events(self.store.alerts()[0]["alert_id"]) if event["kind"] == "review"])
        self.paid.assert_not_called()

    def test_missing_storage_keeps_monitoring_read_only(self):
        with patch("leakprobe.ui.employee_dashboard.AlertStore", side_effect=OSError("read only")):
            app = self.app()
            self.assertFalse(app.exception)
            self.assertEqual(len(app.tabs), 4)
            self.assertFalse(any(b.label == "Save review" for b in app.button))
            self.assertTrue(next(b for b in app.button if b.label == "Run AI Investigation").disabled)
        self.paid.assert_not_called()


class SensorPresentationTests(unittest.TestCase):
    def test_latest_values_retain_units_signs_missing_values_and_baseline(self):
        snapshot = load_monitoring_snapshot("case_005")
        original = snapshot["observations"].copy(deep=True)
        rows = [{"Channel": "229", "Sensor group": "Flow", "Readings outside reference": 2}]
        values = latest_sensor_values(snapshot, rows)
        self.assertEqual(values[0]["Latest observed"], original["flow_229_lps"].iloc[-1])
        self.assertGreater(values[0]["Latest observed"], 0)
        self.assertEqual(values[0]["Unit"], "L/s")
        references = pd.Series([profile["flow"]["229"][-1] for profile in snapshot["normal_profiles"]])
        self.assertEqual(values[0]["Normal 5%"], references.quantile(.05))
        pd.testing.assert_frame_equal(snapshot["observations"], original)
        local = {**snapshot, "observations": original.copy()}
        local["observations"].loc[local["observations"].index[-1], "flow_229_lps"] = float("nan")
        self.assertEqual(latest_sensor_values(local, rows)[0]["Latest status"], "Missing")

    def test_map_preserves_topology_and_one_zoom_binding(self):
        layout = load_network_layout()
        original = copy.deepcopy(layout)
        spec = workspace_map_spec(layout, "202")
        self.assertEqual(layout, original)
        self.assertEqual(spec["height"], 420)
        self.assertEqual(spec["layer"][-1]["data"]["values"], [row for row in layout["pipes"] if row["id"] == "202"])
        self.assertEqual(sum(len(layer.get("params", [])) for layer in spec["layer"]), 1)
        self.assertNotIn("params", spec)


if __name__ == "__main__":
    unittest.main()
