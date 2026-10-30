import copy
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import numpy as np
import pandas as pd

from leakprobe.net3_tools import Net3Investigation
from leakprobe.paths import NET3_DATA, ROOT
from leakprobe.ui.ai_service import run_investigation, save_trace
from leakprobe.ui.alert_store import AlertStore, STATUSES
from leakprobe.ui.operations import (build_alert, feed_fingerprint, matching_investigation,
                                     REPORT_SECTIONS, report_summary, validate_feed)


class FeedChecks(unittest.TestCase):
    def test_summary_is_extracted_verbatim_or_unavailable(self):
        self.assertEqual(report_summary("### Summary\nActual model text.\n### Next\nOther."), "Actual model text.")
        self.assertIsNone(report_summary("No summary was provided."))

    def setUp(self):
        self.metadata = json.loads((NET3_DATA / "metadata.json").read_text())
        self.frame = pd.DataFrame({"timestamp_utc": pd.date_range("2026-01-01", periods=25, freq="15min", tz="UTC").astype(str)})
        channels = {**{f"pressure_{n}_m": np.ones(25) for n in self.metadata["monitor_pressure_nodes"]},
                    **{f"flow_{p}_lps": np.ones(25) for p in self.metadata["flow_sensors"]}}
        self.frame = pd.concat([self.frame, pd.DataFrame(channels)], axis=1)
        self.profiles = [{"pressure": {n: [1.] * 25 for n in self.metadata["monitor_pressure_nodes"]},
                          "flow": {p: [1.] * 25 for p in self.metadata["flow_sensors"]}}]

    def check(self, frame=None, profiles=None):
        return validate_feed(self.frame if frame is None else frame, self.metadata,
                             self.profiles if profiles is None else profiles, now="2026-01-02T00:00:00Z")

    def test_stale_and_partial_readings_are_explicit(self):
        self.frame.loc[23:, "pressure_10_m"] = np.nan
        quality = self.check()
        self.assertTrue(quality["stale"])
        self.assertEqual(quality["channels_present"], 209)
        self.assertEqual(quality["latest_channel_coverage"], 208)
        self.assertEqual(quality["missing_readings"], 2)
        self.assertEqual(quality["stale_channels"], ["pressure_10_m"])

    def test_rejects_duplicates_disorder_gaps_and_missing_timestamps(self):
        for value in (self.frame.iloc[0, 0], "not a timestamp", None, "2026-01-01T00:01:00Z"):
            frame = self.frame.copy()
            frame.loc[1, "timestamp_utc"] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.check(frame)
        with self.assertRaises(ValueError):
            self.check(self.frame.iloc[::-1])

    def test_rejects_missing_channel_nonfinite_and_bad_baselines(self):
        with self.assertRaises(ValueError):
            self.check(self.frame.drop(columns="pressure_10_m"))
        for value in (np.inf, -np.inf, "invalid"):
            frame = self.frame.astype(object)
            frame.loc[0, "pressure_10_m"] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.check(frame)
        profiles = copy.deepcopy(self.profiles)
        profiles[0]["pressure"]["10"] = [1]
        with self.assertRaises(ValueError):
            self.check(profiles=profiles)

    def test_all_missing_or_wrong_sample_count_blocked(self):
        frame = self.frame.copy()
        frame.loc[:, frame.columns[1:]] = np.nan
        with self.assertRaises(ValueError):
            self.check(frame)
        with self.assertRaises(ValueError):
            self.check(self.frame.iloc[:-1])
        shifted = self.frame.copy()
        shifted["timestamp_utc"] = (pd.to_datetime(shifted["timestamp_utc"]) + pd.Timedelta(minutes=15)).astype(str)
        with self.assertRaises(ValueError):
            self.check(shifted)

    def test_alert_does_not_consume_truth_and_changed_feed_changes_identity(self):
        snapshot = {"case_id": "case_402", "observations": self.frame,
                    "comparison": {"decision": {"prediction": "leak", "best_scenario": "leak_pipe:247"}}}
        alert = build_alert(snapshot)
        snapshot.update(actual="normal", truth_labels={"incident": "normal"})
        self.assertEqual(build_alert(snapshot), alert)
        self.assertEqual(alert["candidate_pipe"], "247")
        self.frame.loc[0, "pressure_10_m"] = 50
        self.assertNotEqual(build_alert(snapshot)["alert_id"], alert["alert_id"])

    def test_normal_and_uncertain_stay_distinct(self):
        for prediction in ("normal", "uncertain"):
            alert = build_alert({"case_id": "x", "observations": self.frame,
                "comparison": {"decision": {"prediction": prediction, "best_scenario": "normal"}}})
            self.assertEqual(alert["prediction"], prediction)
            self.assertIsNone(alert["candidate_pipe"])

    def test_saved_trace_requires_matching_window(self):
        alert = {"case_id": "x", "alert_id": "a", "feed_fingerprint": feed_fingerprint(self.frame)}
        run = {"case_id": "other", "alert_id": "a", "status": "completed"}
        self.assertIsNone(matching_investigation([run], alert))
        run["case_id"] = "x"
        self.assertEqual(matching_investigation([run], alert), run)
        run["alert_id"] = "old-reference-comparison"
        self.assertIsNone(matching_investigation([run], alert))
        rows = self.frame.to_dict("records")
        legacy = {"case_id": "x", "trace": [{"tool": "get_observations", "result": {"readings": rows}}]}
        self.assertEqual(matching_investigation([legacy], alert), legacy)
        rows[0]["pressure_10_m"] = 99
        self.assertIsNone(matching_investigation([legacy], alert))

    def test_legacy_float_tolerance_requires_same_times_channels_and_readings(self):
        alert = {"case_id": "x", "alert_id": "a", "feed_fingerprint": feed_fingerprint(self.frame)}
        rows = self.frame.to_dict("records")
        rows[0]["pressure_10_m"] += 1e-14
        run = {"case_id": "x", "trace": [{"tool": "get_observations", "result": {"readings": rows}}]}
        self.assertEqual(matching_investigation([run], alert, self.frame), run)
        rows[0]["pressure_10_m"] += .001
        self.assertIsNone(matching_investigation([run], alert, self.frame))


class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "alerts.db"
        self.store = AlertStore(self.path)
        self.store.register({"alert_id": "a", "prediction": "leak"})

    def test_acknowledgment_review_and_notes_persist_in_order(self):
        for status in STATUSES:
            self.store.review("a", status, "Engineer", "Field assessment, not reference truth")
        events = [e for e in AlertStore(self.path).events("a") if e["kind"] == "review"]
        self.assertEqual([e["status"] for e in events], list(STATUSES))
        self.assertTrue(all(e["at"].endswith("+00:00") for e in events))
        self.assertEqual(len(self.store.alerts()), 1)
        self.store.register({"alert_id": "a"})
        self.assertEqual(self.store.alerts()[0]["prediction"], "leak")

    def test_invalid_review_rejected(self):
        for status, reviewer in (("fake", "x"), ("Acknowledged", "")):
            with self.assertRaises(ValueError):
                self.store.review("a", status, reviewer)
        with self.assertRaises(ValueError):
            self.store.review("unknown", "Acknowledged", "x")

    def test_concurrent_pending_duplicate_result_and_lifetime_budget(self):
        first = self.store.reserve_ai("a")
        with self.assertRaises(ValueError):
            AlertStore(self.path).reserve_ai("a")
        self.store.finish_ai("a", first, "failed")
        with self.assertRaises(ValueError):
            self.store.finish_ai("a", first, "completed")
        second = self.store.reserve_ai("a")
        self.store.finish_ai("a", second, "completed")
        with self.assertRaises(ValueError):
            self.store.reserve_ai("a")


class AIIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.session = Net3Investigation("case_402")
        cls.alert = build_alert({"case_id": cls.session.case_id, "observations": cls.session.observations,
                                "comparison": cls.session.compare_hypotheses()})

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.output = Path(self.tmp.name)
        self.store = AlertStore(self.output / "reviews.db")
        self.store.register(self.alert)

    def run_fake(self, result):
        with patch("leakprobe.ui.ai_service.investigate", return_value=result) as loop:
            outcome = run_investigation(self.alert, self.store, client_factory=Mock(), output=self.output)
        return outcome, loop

    def test_no_credentials_never_creates_client_or_reserves_budget(self):
        with patch("leakprobe.ui.ai_service.availability", return_value=(False, "offline")), \
             patch("leakprobe.ui.ai_service.provider_client") as client:
            outcome = run_investigation(self.alert, self.store)
        self.assertEqual(outcome["status"], "unavailable")
        client.assert_not_called()
        self.assertEqual([e["kind"] for e in self.store.events(self.alert["alert_id"])], ["detected"])

    def test_completed_actual_model_answer_budget_and_unique_storage(self):
        from test_nemotron_evidence import validated_result
        result = validated_result(self.session)
        answer = result["answer"]
        outcome, loop = self.run_fake(result)
        self.assertEqual(outcome["answer"], answer)
        self.assertEqual(outcome["status"], "completed")
        self.assertEqual(loop.call_args.kwargs["max_rounds"], 4)
        self.assertEqual(loop.call_args.kwargs["max_tool_calls"], 8)
        self.assertTrue(loop.call_args.kwargs["compact"])
        self.assertIn("submit_employee_report", loop.call_args.kwargs["instructions"])
        before = (self.output / outcome["trace_file"]).read_bytes()
        save_trace(outcome, self.output)
        self.assertEqual((self.output / outcome["trace_file"]).read_bytes(), before)
        self.assertEqual(len(list(self.output.glob("*_llm_trace.json"))), 2)

    def test_ungrounded_answer_is_incomplete(self):
        result, _ = self.run_fake({"status": "completed", "answer": "No tool evidence", "trace": [], "usage": []})
        self.assertEqual(result["status"], "incomplete")

    def test_missing_employee_sections_are_incomplete_even_with_tools(self):
        trace = [{"tool": "compare_hypotheses", "result": self.session.compare_hypotheses()},
                 {"tool": "get_observations", "result": self.session.get_observations()}]
        result, _ = self.run_fake({"status": "completed", "answer": "## Investigation summary\nOnly one section.",
                                   "trace": trace, "usage": []})
        self.assertEqual(result["status"], "incomplete")
        self.assertTrue(result["validation"]["missing_sections"])

    def test_real_agent_tool_loop_with_mocked_provider(self):
        from test_agent import FakeClient, Message
        from test_nemotron_evidence import sample_report, summary_call, report_call
        from leakprobe.investigation_evidence import InvestigationEvidence
        report = sample_report(InvestigationEvidence(self.session))
        client = FakeClient([Message(calls=[summary_call()]), Message(calls=[report_call(report)])])
        result = run_investigation(self.alert, self.store, client_factory=lambda: client, output=self.output)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(len(client.requests), 2)
        self.assertEqual(len(result["report_sections"]), 6)
        self.assertTrue(all(request["max_tokens"] == 2048 for request in client.requests))
        self.assertIn("submit_employee_report", client.requests[0]["messages"][0]["content"])

    def test_provider_failure_sanitized_and_retains_attempt(self):
        factory = Mock(side_effect=RuntimeError("secret credential string"))
        outcome = run_investigation(self.alert, self.store, client_factory=factory, output=self.output)
        self.assertEqual(outcome["status"], "failed")
        self.assertNotIn("secret credential", json.dumps(outcome))
        factory.assert_called_once()
        self.assertEqual(len(self.store.events(self.alert["alert_id"])), 3)

    def test_changed_feed_identity_prevents_paid_call(self):
        alert = {**self.alert, "alert_id": "changed"}
        factory = Mock()
        with self.assertRaises(ValueError):
            run_investigation(alert, self.store, client_factory=factory, output=self.output)
        factory.assert_not_called()

    def test_trace_storage_failure_does_not_leave_pending_request(self):
        with patch("leakprobe.ui.ai_service.investigate", return_value={"status": "incomplete", "trace": [], "answer": ""}), \
             patch("leakprobe.ui.ai_service.save_trace", side_effect=OSError("disk full")):
            result = run_investigation(self.alert, self.store, client_factory=Mock(), output=self.output)
        self.assertEqual(result["status"], "storage_failed")
        self.assertEqual(self.store.events(self.alert["alert_id"])[-1]["status"], "storage_failed")

    def test_detector_and_agent_tools_never_open_truth_labels(self):
        original = Path.read_text
        def guarded(path, *args, **kwargs):
            if path.name == "truth_labels.json":
                raise AssertionError("Ground truth leaked to inference")
            return original(path, *args, **kwargs)
        with patch.object(Path, "read_text", guarded):
            session = Net3Investigation("case_402")
            self.assertTrue(session.compare_hypotheses()["ranking"])
            self.assertNotIn("incident", session.get_observations())
            self.assertNotIn("actual_pipe", session.get_network())

    def test_truncated_trace_files_do_not_hide_valid_history(self):
        from leakprobe.ui.data_access import load_llm_trace_history
        traces = self.output / "traces"
        traces.mkdir()
        (traces / "net3_full_high_signal_bad_llm_trace.json").write_text('{"status":', encoding="utf-8")
        (traces / "net3_full_high_signal_array_llm_trace.json").write_text('[]', encoding="utf-8")
        save_trace({"case_id": "case_402", "status": "failed", "trace": []}, traces)
        with patch("leakprobe.ui.data_access.OUTPUTS", self.output):
            history = load_llm_trace_history()
        self.assertEqual(len(history), 1)

    def test_real_bundled_trace_matches_current_feed_and_ranking(self):
        from leakprobe.ui.data_access import load_llm_trace_history
        session = Net3Investigation("case_405")
        alert = build_alert({"case_id": session.case_id, "observations": session.observations,
                             "comparison": session.compare_hypotheses()})
        result = matching_investigation(load_llm_trace_history(), alert, session.observations)
        self.assertIsNotNone(result)
        self.assertEqual(result["status"], "completed")
        alert["comparison_signature"][0]["score"] += 1
        self.assertIsNone(matching_investigation(load_llm_trace_history(), alert, session.observations))


class OfflineUITests(unittest.TestCase):
    def setUp(self):
        from leakprobe.ui.alert_queue import assess_window
        self.queue_patch = patch("leakprobe.ui.employee_dashboard.load_monitoring_queue",
                                 return_value=[assess_window("case_405")])
        self.queue_patch.start()
        self.addCleanup(self.queue_patch.stop)

    def test_employee_page_has_no_manual_selectors_or_paid_calls(self):
        from streamlit.testing.v1 import AppTest
        with tempfile.TemporaryDirectory() as tmp, \
             patch("leakprobe.ui.employee_dashboard.AlertStore", return_value=AlertStore(Path(tmp) / "reviews.db")), \
             patch("leakprobe.ui.employee_dashboard.availability", return_value=(False, "Offline")), \
             patch("leakprobe.ui.employee_dashboard.run_investigation") as paid:
            app = AppTest.from_string("from leakprobe.ui.employee_dashboard import render_monitoring_dashboard\nrender_monitoring_dashboard()")
            app.run(timeout=40)
            self.assertFalse(app.exception, str(app.exception))
            self.assertEqual([x.label for x in app.selectbox], ["Open monitoring record", "Review action"])
            self.assertTrue(next(b for b in app.button if b.label == "Run AI Investigation").disabled)
            paid.assert_not_called()
            self.assertEqual(app.title[0].value, "LeakProbe")
            self.assertTrue(any(x.value == "AI-Assisted Water Leak Monitoring & Investigation" for x in app.caption))
            self.assertEqual(sum(x.value == "Net3 simulation feed" for x in app.caption), 1)
            captions = [x.value for x in app.caption]
            self.assertEqual(captions[captions.index("Net3 simulation feed") + 1].split(":", 1)[0], "Latest sensor timestamp")
            self.assertTrue(any("stale" in x.value for x in app.caption))
            self.assertTrue(any("evidence and competing candidates" in x.label for x in app.expander))

    def test_entry_point_and_review_submission(self):
        from streamlit.testing.v1 import AppTest
        with tempfile.TemporaryDirectory() as tmp:
            store = AlertStore(Path(tmp) / "review.db")
            with patch("leakprobe.ui.employee_dashboard.AlertStore", return_value=store), \
                 patch("leakprobe.ui.employee_dashboard.availability", return_value=(False, "Offline")), \
                 patch("leakprobe.ui.employee_dashboard.run_investigation") as paid:
                app = AppTest.from_file(str(ROOT / "streamlit_app.py")).run(timeout=40)
                self.assertFalse(app.exception, str(app.exception))
                next(field for field in app.text_input if field.label == "Reviewer name").set_value("Demo reviewer")
                app.text_area[0].set_value("Check the pressure sensor before a field visit.")
                next(b for b in app.button if b.label == "Save review").click().run(timeout=40)
                self.assertFalse(app.exception, str(app.exception))
                events = store.events(store.alerts()[0]["alert_id"])
                self.assertEqual(events[-1]["status"], "Acknowledged")
                self.assertEqual(events[-1]["reviewer"], "Demo reviewer")
                paid.assert_not_called()

    def test_existing_admin_pages_still_render(self):
        from streamlit.testing.v1 import AppTest
        pages = (("pages", "render_benchmarks"), ("pages", "render_about"),
                 ("pages", "render_llm_run_history"), ("monitoring", "render_evaluation_replay"),
                 ("outcomes", "render_reference_outcomes"))
        for module, function in pages:
            with self.subTest(page=function):
                app = AppTest.from_string(f"from leakprobe.ui.{module} import {function}\n{function}()").run(timeout=40)
                self.assertFalse(app.exception, str(app.exception))
                self.assertEqual(app.title[0].value, "LeakProbe")
                subtitle = ("Water Leak Detection & Investigation" if function == "render_about"
                            else "AI-Assisted Water Leak Monitoring & Investigation")
                self.assertTrue(any(x.value == subtitle for x in app.caption))
                prominent = [element.value for kind in ("title", "header", "subheader", "info", "warning", "success", "error")
                             for element in getattr(app, kind)]
                self.assertFalse(any(word in text.lower() for text in prominent
                                     for word in ("synthetic", "simulated", "archived", "demo")))
                if function == "render_evaluation_replay":
                    self.assertEqual(sum(x.value == "Net3 simulation feed" for x in app.caption), 1)
                if function == "render_about":
                    body = " ".join(element.value for element in app.markdown)
                    self.assertEqual([heading.value for heading in app.header], ["About LeakProbe"])
                    for heading in ("What LeakProbe Does", "How LeakProbe Works", "Understanding Alerts", "Product Scope"):
                        self.assertIn(heading, [element.value for element in app.subheader])
                    for feature in ("Network Monitoring", "Leak Detection", "Intelligent Investigation", "Alert Management"):
                        self.assertIn(f"**{feature}**", body)
                    for status in ("Suspected leak", "No alert", "Review required"):
                        self.assertIn(f"**{status}:**", body)
                    for term in ("python", "streamlit", "nebius", "nemotron", "hackathon", "sqlite", "api "):
                        self.assertNotIn(term, body.lower())
                    scope_notes = [element.value for element in app.caption if "Net3" in element.value]
                    self.assertEqual(len(scope_notes), 1)
                    self.assertIn("Net3 demonstration data", scope_notes[0])
                    self.assertIn("[technical documentation]", scope_notes[0])
                    self.assertFalse(app.info or app.warning or app.error)

    def test_previous_alert_list_preserves_automatic_current_feed(self):
        from streamlit.testing.v1 import AppTest
        from leakprobe.ui.data_access import load_monitoring_snapshot
        current = load_monitoring_snapshot()
        previous_session = Net3Investigation("case_402")
        previous = build_alert({"case_id": previous_session.case_id,
                                "observations": previous_session.observations,
                                "comparison": previous_session.compare_hypotheses()})
        with tempfile.TemporaryDirectory() as tmp:
            store = AlertStore(Path(tmp) / "alerts.db")
            store.register(previous)
            store.review(previous["alert_id"], "Under review", "Test reviewer")
            with patch("leakprobe.ui.employee_dashboard.AlertStore", return_value=store), \
                 patch("leakprobe.ui.employee_dashboard.load_monitoring_snapshot", return_value=current) as feed, \
                 patch("leakprobe.ui.employee_dashboard.availability", return_value=(False, "Offline")), \
                 patch("leakprobe.ui.employee_dashboard.run_investigation") as paid:
                app = AppTest.from_string("from leakprobe.ui.employee_dashboard import render_monitoring_dashboard\nrender_monitoring_dashboard()").run(timeout=40)
                self.assertFalse(app.exception, str(app.exception))
                feed.assert_called_once_with("case_405")
                paid.assert_not_called()
                self.assertTrue(any(x.label == "Previously recorded alerts · 1" for x in app.expander))
                tables = [table.value for table in app.dataframe]
                history = next(table for table in tables if "Alert" in table.columns)
                self.assertEqual(history["Alert"].tolist(), [previous["alert_id"]])
                self.assertEqual(history["Review"].tolist(), ["Under review"])
                self.assertEqual(len(store.alerts()), 2)

    def test_opening_queue_record_updates_details_without_paid_inference(self):
        from streamlit.testing.v1 import AppTest
        from leakprobe.ui.alert_queue import assess_window
        with tempfile.TemporaryDirectory() as tmp, \
             patch("leakprobe.ui.employee_dashboard.AlertStore", return_value=AlertStore(Path(tmp) / "reviews.db")), \
             patch("leakprobe.ui.employee_dashboard.load_monitoring_queue", return_value=[assess_window("case_405"), assess_window("case_402"), assess_window("case_004")]), \
             patch("leakprobe.ui.employee_dashboard.availability", return_value=(False, "Offline")), \
             patch("leakprobe.ui.employee_dashboard.run_investigation") as paid:
            app = AppTest.from_string("from leakprobe.ui.employee_dashboard import render_monitoring_dashboard\nrender_monitoring_dashboard()").run(timeout=40)
            app.selectbox[0].set_value("case_402").run(timeout=40)
            self.assertFalse(app.exception, str(app.exception))
            self.assertTrue(any("LP-0402" in heading.value for heading in app.subheader))
            app.radio[0].set_value("No alert").run(timeout=40)
            self.assertFalse(app.exception, str(app.exception))
            self.assertTrue(any("LP-0004" in heading.value for heading in app.subheader))
            self.assertEqual([x.label for x in app.selectbox], ["Open monitoring record"])
            paid.assert_not_called()

    def test_ai_button_is_explicit_and_failure_is_visible(self):
        from streamlit.testing.v1 import AppTest
        alert = {"case_id": "x", "alert_id": "a", "feed_fingerprint": "f"}
        with patch("leakprobe.ui.employee_dashboard.availability", return_value=(True, "Ready")), \
             patch("leakprobe.ui.employee_dashboard.load_llm_trace_history", return_value=[]), \
             patch("leakprobe.ui.employee_dashboard.run_investigation", return_value={"status": "failed", "error": "No automatic retry"}) as paid:
            app = AppTest.from_string("from leakprobe.ui.employee_dashboard import render_ai\n"
                                     f"render_ai({alert!r}, object())").run(timeout=20)
            paid.assert_not_called()
            app.button[0].click().run(timeout=20)
            self.assertFalse(app.exception, str(app.exception))
            paid.assert_called_once()
            self.assertTrue(any("failed" in w.value for w in app.warning))

    def test_presentation_does_not_rewrite_saved_investigation_text(self):
        from streamlit.testing.v1 import AppTest
        answer = "## Investigation summary\nSimulated observations from an archived synthetic demo.\n## Evidence\nSaved factual content."
        saved = {"case_id": "x", "alert_id": "a", "status": "completed", "model": "nemotron", "answer": answer}
        alert = {"case_id": "x", "alert_id": "a", "feed_fingerprint": "f"}
        with patch("leakprobe.ui.employee_dashboard.availability", return_value=(False, "Offline")), \
             patch("leakprobe.ui.employee_dashboard.load_llm_trace_history", return_value=[saved]), \
             patch("leakprobe.ui.employee_dashboard.run_investigation") as paid:
            app = AppTest.from_string("from leakprobe.ui.employee_dashboard import render_ai\n"
                                     f"render_ai({alert!r}, None)").run(timeout=20)
            self.assertFalse(app.exception, str(app.exception))
            self.assertIn(answer, [element.value for element in app.markdown])
            self.assertEqual(saved["answer"], answer)
            paid.assert_not_called()

    def test_case005_shows_factual_failure_usage_and_collapsed_original(self):
        from streamlit.testing.v1 import AppTest
        session = Net3Investigation("case_005")
        alert = build_alert({"case_id": session.case_id, "observations": session.observations,
                             "comparison": session.compare_hypotheses()})
        saved = json.loads((Path(__file__).parent / "fixtures/case_005_report_regression.json").read_text(encoding="utf-8"))
        saved["alert_id"] = alert["alert_id"]
        with patch("leakprobe.ui.employee_dashboard.availability", return_value=(False, "Offline")), \
             patch("leakprobe.ui.employee_dashboard.load_llm_trace_history", return_value=[saved]), \
             patch("leakprobe.ui.employee_dashboard.run_investigation") as paid:
            app = AppTest.from_string("from leakprobe.ui.employee_dashboard import render_ai\n"
                "from leakprobe.net3_tools import Net3Investigation\n"
                f"render_ai({alert!r}, None, Net3Investigation('case_005').observations)").run(timeout=40)
            self.assertFalse(app.exception, str(app.exception))
            self.assertFalse(app.success)
            captions = " ".join(element.value for element in app.caption)
            self.assertIn("only positive", captions)
            self.assertIn("All six content sections", captions)
            self.assertIn("295,342", captions)
            self.assertIn("cost not reported", captions)
            self.assertIn(saved["answer"].strip(), [element.value.strip() for element in app.markdown])
            self.assertFalse(next(element for element in app.expander if element.label == "Technical tool trace").proto.expanded)
            paid.assert_not_called()

    def test_checked_report_shows_short_employee_sections(self):
        from streamlit.testing.v1 import AppTest
        from test_nemotron_evidence import validated_result
        session = Net3Investigation("case_005")
        saved = validated_result(session)
        saved.update(case_id="case_005", alert_id="test-alert")
        alert = {"case_id": "case_005", "alert_id": "test-alert", "feed_fingerprint": "test"}
        with patch("leakprobe.ui.employee_dashboard.availability", return_value=(False, "Offline")), \
             patch("leakprobe.ui.employee_dashboard.load_llm_trace_history", return_value=[saved]):
            app = AppTest.from_string("from leakprobe.ui.employee_dashboard import render_ai\n"
                                     f"render_ai({alert!r}, None)").run(timeout=40)
            self.assertFalse(app.exception, str(app.exception))
            self.assertTrue(any("cited facts checked" in element.value for element in app.success))
            body = " ".join(element.value for element in app.markdown)
            for section in ("Sensor evidence", "Alternatives to consider", "Uncertainty", "Recommended field actions"):
                self.assertIn(section, body)
            self.assertEqual(len(app.dataframe[0].value), 2)


if __name__ == "__main__":
    unittest.main()
