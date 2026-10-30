"""Cloud configuration and original button workflow; never contact a provider."""
import copy
import socket
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from streamlit.testing.v1 import AppTest

from leakprobe.net3_tools import Net3Investigation
from leakprobe.ui import ai_service
from leakprobe.ui.alert_store import AlertStore
from leakprobe.ui.data_access import load_llm_trace_history
from leakprobe.ui.operations import build_alert, matching_investigation
from test_agent import FakeClient, Message
from test_nemotron_evidence import report_call, sample_report, summary_call
from leakprobe.investigation_evidence import InvestigationEvidence


class CloudRecoveryTests(unittest.TestCase):
    def setUp(self):
        original_connect = socket.socket.connect
        def local_only(sock, address):
            if address[0] not in ("127.0.0.1", "::1", "localhost"):
                raise AssertionError("External network disabled in tests")
            return original_connect(sock, address)
        self.no_network = patch.object(socket.socket, "connect", local_only)
        self.no_network.start()
        self.addCleanup(self.no_network.stop)

    def test_cloud_secrets_only_and_no_key_export(self):
        import os
        before = dict(os.environ)
        with patch.object(ai_service.st, "secrets", {"NEBIUS_API_KEY": "test-only-not-a-credential",
                  "NEBIUS_MODEL": "mock-model", "NEBIUS_BASE_URL": "https://example.invalid/v1/"}), \
             patch.object(ai_service.importlib.util, "find_spec", return_value=object()):
            self.assertTrue(ai_service.availability()[0])
            constructor = Mock()
            with patch.dict(sys.modules, {"openai": SimpleNamespace(OpenAI=constructor)}):
                ai_service.provider_client()
            self.assertEqual(constructor.call_args.kwargs["max_retries"], 0)
            self.assertEqual(constructor.call_args.kwargs["timeout"], 30)
            self.assertEqual(constructor.call_args.kwargs["base_url"], "https://example.invalid/v1/")
            self.assertEqual(dict(os.environ), before)

    def test_missing_credentials_or_unsafe_endpoint_disable_provider(self):
        for settings in ({}, {"NEBIUS_API_KEY": "test-only", "NEBIUS_BASE_URL": "http://example.invalid"}):
            with patch.object(ai_service.st, "secrets", settings), patch.object(ai_service, "provider_client") as provider:
                self.assertFalse(ai_service.availability()[0])
                self.assertEqual(ai_service.run_investigation({}, None)["status"], "unavailable")
                provider.assert_not_called()

    def test_actual_button_runs_original_tool_loop_and_validates_case405(self):
        session = Net3Investigation("case_405")
        alert = build_alert({"case_id": session.case_id, "observations": session.observations,
                             "comparison": session.compare_hypotheses()})
        report = sample_report(InvestigationEvidence(session))
        client = FakeClient([Message(calls=[summary_call()]), Message(calls=[report_call(report)])])
        with tempfile.TemporaryDirectory() as tmp:
            store = AlertStore(Path(tmp) / "review.db")
            store.register(alert)
            def invoke(selected, selected_store):
                return ai_service.run_investigation(selected, selected_store, client_factory=lambda: client,
                                                    output=Path(tmp) / "traces")
            with patch("leakprobe.ui.employee_dashboard.availability", return_value=(True, "Ready")), \
                 patch("leakprobe.ui.employee_dashboard.run_investigation", side_effect=invoke) as action, \
                 patch("leakprobe.ui.employee_dashboard.load_llm_trace_history", return_value=[]):
                script = ("from leakprobe.ui.employee_dashboard import render_ai\n"
                          "import streamlit as st\nrender_ai(st.session_state.alert, st.session_state.store)")
                app = AppTest.from_string(script)
                app.session_state["alert"], app.session_state["store"] = alert, store
                app.run(timeout=40)
                self.assertFalse(app.exception, str(app.exception))
                action.assert_not_called()
                button = next(b for b in app.button if b.label == "Run AI Investigation")
                self.assertFalse(button.disabled)
                button.click().run(timeout=40)
                self.assertFalse(app.exception, str(app.exception))
                action.assert_called_once()
                self.assertEqual(len(client.requests), 2)
                self.assertTrue(any("cited facts checked" in s.value for s in app.success))
                self.assertEqual(store.events(alert["alert_id"])[-1]["status"], "completed")

    def test_original_validated_report_is_not_hidden_by_later_invalid_attempt(self):
        session = Net3Investigation("case_405")
        alert = build_alert({"case_id": session.case_id, "observations": session.observations,
                             "comparison": session.compare_hypotheses()})
        runs = load_llm_trace_history()
        validated = [r for r in runs if r.get("validation_version") == "cited-facts-v1"
                     and r.get("validation", {}).get("valid")]
        self.assertTrue(validated)
        failed = copy.deepcopy(validated[0])
        failed.update(status="failed", validation={"valid": False})
        found = matching_investigation([failed, validated[0]], alert, session.observations)
        self.assertEqual(found["status"], "completed")

    def test_saved_modern_and_legacy_trace_history_renders(self):
        script = "from leakprobe.ui.pages import render_llm_run_history\nrender_llm_run_history()"
        app = AppTest.from_string(script).run(timeout=40)
        self.assertFalse(app.exception, str(app.exception))
        chooser = next(s for s in app.selectbox if s.label == "Open a saved run")
        self.assertEqual(len(chooser.options), 5)
        for i in range(5):
            chooser = next(s for s in app.selectbox if s.label == "Open a saved run")
            chooser.set_value(i).run(timeout=40)
            self.assertFalse(app.exception, str(app.exception))


if __name__ == "__main__":
    unittest.main()
