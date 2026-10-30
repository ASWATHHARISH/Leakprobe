"""CLI launch and trace-preservation regressions. Providers and dotenv are mocked."""
import contextlib
import io
import json
import os
import runpy
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace as S
from unittest.mock import Mock, patch

from leakprobe import agent, run_demo
from leakprobe.net3_tools import Net3Investigation
from leakprobe.paths import ROOT
from test_agent import FakeClient, Message


class CLISafetyTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.output = self.root / "outputs"
        self.traces = self.output / "traces"
        self.traces.mkdir(parents=True)
        self.stdout = self.enterContext(contextlib.redirect_stdout(io.StringIO()))
        for module in (agent, run_demo):
            self.enterContext(patch.object(module, "ROOT", self.root))
            self.enterContext(patch.object(module, "OUTPUTS", self.output))
        self.enterContext(patch.dict(os.environ, {
            "NEBIUS_API_KEY": "test-only-not-a-credential", "NEBIUS_MODEL": "mock-model",
            "NEBIUS_BASE_URL": "https://example.invalid/v1/",
        }))
        self.clients = []

        def fake_provider(**kwargs):
            call = S(id="fit", function=S(name="compare_hypotheses", arguments="{}"))
            client = FakeClient([Message(calls=[call]), Message(content="Mocked CLI report.")])
            self.clients.append(client)
            return client

        self.provider = Mock(side_effect=fake_provider)
        self.dotenv = Mock()
        self.enterContext(patch.dict(sys.modules, {
            "dotenv": S(load_dotenv=self.dotenv),
            "openai": S(OpenAI=self.provider, APIError=RuntimeError),
        }))

    def seed(self, filename):
        path = self.traces / filename
        content = b"Existing investigation must remain byte-for-byte unchanged.\n"
        path.write_bytes(content)
        return path, content

    def launch(self, program, args):
        with patch.object(sys, "argv", [str(program), *args]):
            runpy.run_path(str(program), run_name="__main__")

    def test_default_vscode_launch_runs_offline_without_provider_calls(self):
        config = json.loads((ROOT / ".vscode/launch.json").read_text())["configurations"][0]
        self.assertEqual(config["name"], "LeakProbe local demo")
        self.assertIn("--scripted", config["args"])
        program = Path(config["program"].replace("${workspaceFolder}", str(ROOT)))
        with patch.object(agent, "run_live", side_effect=AssertionError("Live mode must not start")):
            self.launch(program, config["args"])
        self.provider.assert_not_called()
        self.dotenv.assert_not_called()
        saved = list(self.traces.glob("*_scripted_trace.json"))
        self.assertEqual(len(saved), 1)
        trace = json.loads(saved[0].read_text())
        self.assertEqual([row["tool"] for row in trace], [
            "get_observations", "get_network", "get_operation_records", "compare_hypotheses"])

    def test_generic_demo_defaults_offline_and_requires_explicit_live_flag(self):
        with patch.object(run_demo, "run_scripted_demo") as offline, patch.object(agent, "run_live") as live:
            self.launch(ROOT / "run_demo.py", [])
            offline.assert_called_once_with(None)
            live.assert_not_called()
            offline.reset_mock()
            self.launch(ROOT / "run_demo.py", ["--live", "--case", "case_405"])
            live.assert_called_once_with(case_id="case_405")
            offline.assert_not_called()
        self.provider.assert_not_called()

    def test_conflicting_modes_fail_before_any_investigation(self):
        with contextlib.redirect_stderr(io.StringIO()), patch.object(agent, "run_live") as live, \
             patch.object(run_demo, "run_scripted_demo") as offline:
            with self.assertRaises(SystemExit) as error:
                self.launch(ROOT / "run_demo.py", ["--live", "--scripted"])
            self.assertEqual(error.exception.code, 2)
            live.assert_not_called()
            offline.assert_not_called()
        self.provider.assert_not_called()

    def test_scripted_repeated_runs_preserve_old_and_new_reports(self):
        old, payload = self.seed("net3_full_high_signal_case_405_scripted_trace.json")
        run_demo.run_scripted_demo("case_405")
        first = {p.name: p.read_bytes() for p in self.traces.iterdir()}
        run_demo.run_scripted_demo("case_405")
        self.assertEqual(old.read_bytes(), payload)
        self.assertEqual(len(list(self.traces.iterdir())), 3)
        for name, content in first.items():
            self.assertEqual((self.traces / name).read_bytes(), content)
        for path in self.traces.iterdir():
            if path != old:
                self.assertEqual(json.loads(path.read_text())[-1]["tool"], "compare_hypotheses")
        self.provider.assert_not_called()

    def test_scripted_uuid_collision_refuses_overwrite(self):
        old, payload = self.seed("net3_full_high_signal_case_405_collision_scripted_trace.json")
        with patch.object(run_demo.uuid, "uuid4", return_value=S(hex="collision")):
            with self.assertRaises(FileExistsError):
                run_demo.run_scripted_demo("case_405")
        self.assertEqual(old.read_bytes(), payload)
        self.assertEqual(len(list(self.traces.iterdir())), 1)
        self.provider.assert_not_called()

    def test_explicit_agent_live_command_runs_and_preserves_reports(self):
        old, payload = self.seed("net3_full_high_signal_case_405_llm_trace.json")
        expected_ranking = Net3Investigation("case_405").compare_hypotheses()["ranking"]
        self.launch(ROOT / "agent.py", ["--case", "case_405"])
        first = {p.name: p.read_bytes() for p in self.traces.iterdir()}
        self.launch(ROOT / "agent.py", ["--case", "case_405"])
        self.assertEqual(old.read_bytes(), payload)
        self.assertEqual(len(list(self.traces.iterdir())), 3)
        self.assertEqual(self.provider.call_count, 2)
        self.assertEqual(self.dotenv.call_count, 2)
        for name, content in first.items():
            self.assertEqual((self.traces / name).read_bytes(), content)
        for path in self.traces.iterdir():
            if path != old:
                report = json.loads(path.read_text())
                self.assertEqual(report["case_id"], "case_405")
                self.assertEqual(report["status"], "completed")
                self.assertEqual(report["trace"][0]["tool"], "compare_hypotheses")
                self.assertEqual(report["trace"][0]["result"]["ranking"], expected_ranking)
                self.assertTrue(report["saved_at_utc"])
        for client in self.clients:
            self.assertEqual(len(client.requests), 2)
            self.assertTrue(any(m["role"] == "tool" for m in client.requests[-1]["messages"]))
        self.assertEqual(self.provider.call_args.kwargs["max_retries"], 0)

    def test_live_uuid_collision_refuses_overwrite_without_retry(self):
        old, payload = self.seed("net3_full_high_signal_case_405_collision_llm_trace.json")
        with patch.object(agent.uuid, "uuid4", return_value=S(hex="collision")):
            with self.assertRaises(FileExistsError):
                self.launch(ROOT / "agent.py", ["--case", "case_405"])
        self.assertEqual(old.read_bytes(), payload)
        self.assertEqual(len(list(self.traces.iterdir())), 1)
        self.provider.assert_called_once()
        self.assertEqual(len(self.clients[0].requests), 2)


if __name__ == "__main__":
    unittest.main()
