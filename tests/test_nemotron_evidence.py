import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace as S
from unittest.mock import patch

from leakprobe.employee_investigator import investigate_employee
from leakprobe.investigation_evidence import InvestigationEvidence
from leakprobe.investigation_report import (audit_legacy_report, parse_legacy_sections,
                                           render_report_markdown, validate_report)
from leakprobe.net3_tools import Net3Investigation
from test_agent import FakeClient, Message


CHANNELS = ["pressure_243_m", "flow_229_lps"]


def sample_report(evidence):
    evidence.get_observations()
    ranking = evidence.compare_hypotheses()["ranking"]
    sensors = evidence.get_sensor_summary(CHANNELS)["sensors"]
    def candidate(row):
        return {"pipe": row["pipe"], "rank": row["rank"], "fit_score": row["fit"]["value"], "fact_id": row["fit"]["fact_id"]}
    alternatives = [row for row in ranking[1:] if row["pipe"] is None or row["rank"] == 2]
    return {"summary": "Review the leading candidate and verify the sensor evidence before deciding on field action.",
            "evidence": [{key: sensor["facts"][2][key] for key in ("fact_id", "value", "unit", "channel", "sign")} for sensor in sensors],
            "leading_candidate": candidate(ranking[0]), "alternatives": [candidate(row) for row in alternatives],
            "possible_explanations": ["demand_change", "sensor_error"],
            "uncertainty": ["fit_not_probability", "not_field_verified", "model_mismatch"],
            "actions": ["check_sensor_health", "review_operating_changes", "verify_candidate_in_field"]}


def report_call(report, ident="report"):
    return S(id=ident, function=S(name="submit_employee_report", arguments=json.dumps(report)))


def summary_call():
    return S(id="sensors", function=S(name="get_sensor_summary", arguments=json.dumps({"channels": CHANNELS})))


def validated_result(session):
    evidence = InvestigationEvidence(session)
    report = sample_report(evidence)
    trace = [{"tool": name, "arguments": args, "result": evidence.dispatch(name, args)}
             for name, args in (("get_observations", {}), ("compare_hypotheses", {}),
                                ("get_sensor_summary", {"channels": CHANNELS}))]
    return {"status": "completed", "answer": render_report_markdown(report, evidence), "report": report,
            "validation": validate_report(report, evidence), "validation_version": "cited-facts-v1",
            "trace": trace, "evidence_facts": evidence.facts, "usage": [], "request_count": 1}


class Case005RegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.session = Net3Investigation("case_005")
        cls.fixture = json.loads((Path(__file__).parent / "fixtures/case_005_report_regression.json").read_text(encoding="utf-8"))

    def setUp(self):
        self.evidence = InvestigationEvidence(self.session)
        self.report = sample_report(self.evidence)

    def test_real_report_has_all_sections_despite_bold_headings(self):
        sections = parse_legacy_sections(self.fixture["answer"])
        self.assertEqual(len(sections), 6)
        self.assertTrue(all(sections.values()))
        for style in (lambda title: "## " + title, lambda title: "**" + title + "**", lambda title: "1. " + title + ":",
                      lambda title: "**1. " + title + ":**"):
            answer = "\n\n".join(style(title) + "\nContent." for title in sections)
            self.assertEqual(len(parse_legacy_sections(answer)), 6)

    def test_sign_error_and_fabricated_missing_reading_are_blocking(self):
        values = self.session.observations["flow_229_lps"].dropna()
        self.assertTrue((values > 0).all())
        audit = audit_legacy_report(self.fixture["answer"], self.session.observations)
        self.assertEqual(audit["missing_sections"], [])
        self.assertFalse(audit["valid"])
        self.assertTrue(any("Flow-sign contradiction" in error for error in audit["errors"]))
        self.assertTrue(any("00:30" in error and "missing" in error for error in audit["errors"]))
        row = self.evidence.get_sensor_series(["flow_229_lps"], offset=2, limit=1)
        self.assertIsNone(row["rows"][0]["readings"][0]["value"])

    def test_saved_trace_tokens_and_source_unchanged(self):
        self.assertEqual(sum(row["total_tokens"] for row in self.fixture["usage"]), 295342)
        path = Path("outputs/traces") / self.fixture["source_trace_name"]
        if path.exists():
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), self.fixture["source_trace_sha256"])

    def test_valid_report_passes_and_physics_ranking_is_identical(self):
        self.assertTrue(validate_report(self.report, self.evidence)["valid"])
        self.assertEqual(self.evidence.comparison, self.session.compare_hypotheses())
        self.assertEqual(len(self.evidence.channels), 209)
        self.assertEqual(self.report["leading_candidate"]["pipe"], "243")

    def test_wrong_sign_value_sensor_unit_rank_or_pipe_is_rejected(self):
        mutations = (
            lambda r: r["evidence"][1].update(sign="negative"),
            lambda r: r["evidence"][1].update(value=-r["evidence"][1]["value"]),
            lambda r: r["evidence"][0].update(channel="pressure_245_m"),
            lambda r: r["evidence"][1].update(unit="m"),
            lambda r: r["leading_candidate"].update(rank=2),
            lambda r: r["leading_candidate"].update(pipe="229"),
            lambda r: r["evidence"][1].update(fact_id="reading:flow_229_lps:2"),
            lambda r: r.update(summary="Flow is negative at sensor 229."),
            lambda r: r.update(actions=["Field leak was confirmed"]),
        )
        for mutate in mutations:
            report = copy.deepcopy(self.report)
            mutate(report)
            with self.subTest(report=report):
                self.assertFalse(validate_report(report, self.evidence)["valid"])

    def test_missing_content_not_accepted_as_formatting_variation(self):
        report = copy.deepcopy(self.report)
        del report["actions"]
        self.assertFalse(validate_report(report, self.evidence)["valid"])
        self.assertEqual(len(parse_legacy_sections("**Investigation summary**\nOnly one section.")), 1)

    def test_compact_payload_and_bounded_targeted_retrieval(self):
        full = json.dumps(self.session.get_observations(), separators=(",", ":"))
        compact = json.dumps(self.evidence.get_observations(), separators=(",", ":"))
        self.assertLess(len(compact), len(full) * .05)
        self.assertIn("positive", json.dumps(self.evidence.get_sensor_summary(["flow_229_lps"])))
        for arguments in ({"channels": ["flow_999_lps"]}, {"channels": self.evidence.channels},
                          {"channels": CHANNELS, "limit": 100}, {"channels": CHANNELS, "offset": -1}):
            self.assertIn("error", self.evidence.dispatch("get_sensor_series", arguments))
        self.assertIn("error", self.evidence.dispatch("read_truth_labels", {}))

    def test_new_agent_completes_real_tool_loop_without_bulk_observations(self):
        client = FakeClient([Message(calls=[summary_call()]), Message(calls=[report_call(self.report)])])
        result = investigate_employee(client, "mock-model", case_id="case_005")
        self.assertEqual(result["status"], "completed")
        self.assertTrue(result["validation"]["valid"])
        self.assertEqual(result["request_count"], 2)
        self.assertEqual(len(result["report_sections"]), 6)
        self.assertLess(max(row["input_json_bytes"] for row in result["requests"]), 24000)
        self.assertNotIn('"readings": [{"timestamp_utc"', json.dumps(client.requests))

    def test_unsupported_fact_gets_one_correction_not_silent_acceptance(self):
        bad = copy.deepcopy(self.report)
        bad["evidence"][1]["sign"] = "negative"
        client = FakeClient([Message(calls=[summary_call()]), Message(calls=[report_call(bad)]),
                             Message(calls=[report_call(self.report, "corrected")])])
        result = investigate_employee(client, "mock", case_id="case_005")
        self.assertEqual(result["status"], "completed")
        self.assertTrue(any(step["tool"] == "submit_employee_report" and not step["result"]["valid"]
                            for step in result["trace"]))

    def test_repeated_invalid_report_is_not_completed(self):
        bad = copy.deepcopy(self.report)
        bad["evidence"][1]["sign"] = "negative"
        client = FakeClient([Message(calls=[summary_call()]), Message(calls=[report_call(bad)]), Message(calls=[report_call(bad)])])
        result = investigate_employee(client, "mock", case_id="case_005")
        self.assertEqual(result["status"], "invalid_report")
        self.assertFalse(result["validation"]["valid"])

    def test_json_content_contract_also_passes_without_markdown_headings(self):
        client = FakeClient([Message(calls=[summary_call()]), Message(content=json.dumps(self.report))])
        self.assertEqual(investigate_employee(client, "mock", case_id="case_005")["status"], "completed")

    def test_old_prose_kept_but_not_promoted_to_fact_validated_completion(self):
        result = investigate_employee(FakeClient([Message(content=self.fixture["answer"])]), "mock", case_id="case_005")
        self.assertEqual(result["status"], "incomplete")
        self.assertEqual(result["validation"]["missing_sections"], [])
        self.assertTrue(result["validation"]["errors"])
        self.assertEqual(result["answer"], self.fixture["answer"])

    def test_payload_budget_stops_before_provider_call(self):
        client = FakeClient([])
        with patch("leakprobe.employee_investigator.MAX_REQUEST_BYTES", 10):
            result = investigate_employee(client, "mock", case_id="case_005")
        self.assertEqual(result["request_count"], 0)
        self.assertEqual(result["status"], "budget_exhausted")

    def test_failed_second_request_keeps_usage_request_count_and_cost_fields(self):
        class Client:
            def __init__(self):
                self.chat = S(completions=S(create=self.create))
                self.count = 0
            def create(self, **kwargs):
                self.count += 1
                if self.count == 2:
                    raise RuntimeError("credential secret must not be saved")
                return S(choices=[S(message=Message(calls=[summary_call()]), finish_reason="tool_calls")], id="response-1",
                         usage=S(model_dump=lambda: {"prompt_tokens": 100, "completion_tokens": 20, "total_tokens": 120}),
                         model_extra={"cost": .002, "currency": "USD"})
        result = investigate_employee(Client(), "mock", case_id="case_005")
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["request_count"], 2)
        self.assertEqual(result["usage_summary"]["total_tokens"], 120)
        self.assertEqual(result["provider_cost_info"][0]["provider_fields"], {"cost": .002, "currency": "USD"})
        self.assertNotIn("credential secret", json.dumps(result))

    def test_observed_token_budget_prevents_another_request(self):
        class Client:
            def __init__(self):
                self.chat = S(completions=S(create=self.create))
                self.count = 0
            def create(self, **kwargs):
                self.count += 1
                return S(choices=[S(message=Message(calls=[summary_call()]), finish_reason="tool_calls")],
                         usage=S(model_dump=lambda: {"total_tokens": 32000}))
        client = Client()
        result = investigate_employee(client, "mock", case_id="case_005")
        self.assertEqual(result["status"], "budget_exhausted")
        self.assertEqual(client.count, 1)
        self.assertEqual(result["usage_summary"]["total_tokens"], 32000)

    def test_malformed_provider_response_keeps_reported_usage(self):
        client = S(chat=S(completions=S(create=lambda **kwargs:
                   S(choices=[], usage={"total_tokens": 17}, model_extra={}))))
        result = investigate_employee(client, "mock", case_id="case_005")
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["request_count"], 1)
        self.assertEqual(result["usage_summary"]["total_tokens"], 17)

    def test_known_legacy_candidate_comparison_error_still_flagged(self):
        audit = audit_legacy_report("All leak candidates improve the fit relative to normal.",
            self.session.observations, [{"scenario": "normal", "score": 2.}, {"scenario": "leak_pipe:243", "score": 3.}])
        self.assertTrue(any("Ranking contradiction" in error for error in audit["errors"]))

    def test_nonfinite_model_numbers_are_rejected_and_trace_remains_serializable(self):
        bad = copy.deepcopy(self.report)
        bad["evidence"][0]["value"] = float("nan")
        client = FakeClient([Message(calls=[report_call(bad)]), Message(calls=[report_call(bad)])])
        result = investigate_employee(client, "mock", case_id="case_005")
        self.assertNotEqual(result["status"], "completed")
        self.assertFalse(result["validation"]["valid"])
        json.dumps(result, allow_nan=False)


if __name__ == "__main__":
    unittest.main()
