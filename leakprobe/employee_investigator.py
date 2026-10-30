"""Bounded Nemotron investigation with compact tools and validated report submission."""
import json

from .investigation_evidence import InvestigationEvidence
from .investigation_report import (audit_legacy_report, parse_legacy_sections,
                                  render_report_markdown, report_tool, validate_report)
from .net3_tools import Net3Investigation

MAX_REQUEST_BYTES = 24000
MAX_TOTAL_REQUEST_BYTES = 72000
MAX_OBSERVED_TOKENS = 32000


def strict_json(text):
    def reject(value):
        raise ValueError("Non-finite JSON numbers are not allowed.")
    return json.loads(text, parse_constant=reject)

SYSTEM = """You are LeakProbe's employee investigation assistant. Use only supplied tool evidence.
The physics detector uses all 209 channels; you receive a compact shortlist and can retrieve
any configured channel with get_sensor_summary or paginated get_sensor_series. Missing is
not zero. Flow sign is relative to model link orientation and does not prove outflow or leakage.
Candidate ranks are fixed detector results. Do not invent sensor IDs, values, causal explanations,
topology, operations records or field results. No ground truth is available.
Finish by calling submit_employee_report. Copy exact fact IDs, values, units, signs, ranks and
pipe IDs from returned facts. Include normal operation among alternatives when a pipe leads.
Write a short non-numerical employee summary; put all sensor/numerical/directional claims in
the structured cited fields, never the summary. Pick possible explanations as hypotheses,
not established causes, and select practical actions and uncertainty codes from the schema.
The report renders six sections: summary, evidence, leading candidate, alternatives,
uncertainty and field actions. No long technical essay. Repair validation errors at most once."""


def usage_summary(result):
    usage = result.get("usage", [])
    return {"requests": result.get("request_count", len(usage)),
            "prompt_tokens": sum(row.get("prompt_tokens", 0) or 0 for row in usage),
            "completion_tokens": sum(row.get("completion_tokens", 0) or 0 for row in usage),
            "total_tokens": sum(row.get("total_tokens", 0) or 0 for row in usage),
            "provider_cost_info": result.get("provider_cost_info", []),
            "usage_reported_for_requests": len(usage)}


def investigate_employee(client, model, case_id=None, max_rounds=4, max_tool_calls=8):
    evidence = InvestigationEvidence(Net3Investigation(case_id))
    tools = evidence.schemas() + [report_tool()]
    trace, usage, receipts, costs = [], [], [], []
    initial = {}
    for name in ("get_observations", "compare_hypotheses", "get_network"):
        value = evidence.dispatch(name, {})
        initial[name] = value
        trace.append({"tool": name, "arguments": {}, "result": value, "source": "initial_context"})
    messages = [{"role": "system", "content": SYSTEM},
                {"role": "user", "content": json.dumps(initial, separators=(",", ":"), allow_nan=False)}]
    request_bytes, tool_calls, validation_attempts = 0, 0, 0
    last_report, last_validation, last_answer = None, None, ""

    def finish(status, error=None):
        result = {"status": status, "answer": last_answer, "report": last_report,
                  "validation": last_validation or {"valid": False, "errors": [error or "No validated report submitted."]},
                  "validation_version": "cited-facts-v1", "trace": trace, "usage": usage,
                  "request_count": len(receipts), "requests": receipts, "provider_cost_info": costs,
                  "case_id": evidence.session.case_id, "evidence_facts": evidence.facts,
                  "report_sections": parse_legacy_sections(last_answer),
                  "budget": {"max_requests": min(max_rounds, 4), "max_tool_calls": min(max_tool_calls, 8),
                             "max_output_tokens_per_request": 2048, "max_request_bytes": MAX_REQUEST_BYTES,
                             "max_total_request_bytes": MAX_TOTAL_REQUEST_BYTES,
                             "observed_token_stop": MAX_OBSERVED_TOKENS}}
        if error:
            result["error"] = error
        result["usage_summary"] = usage_summary(result)
        return result

    def submit(report):
        nonlocal last_report, last_validation, last_answer, validation_attempts
        validation_attempts += 1
        last_report = report
        last_validation = validate_report(report, evidence)
        if last_validation["valid"]:
            last_answer = render_report_markdown(report, evidence)
        return last_validation

    for _ in range(min(max_rounds, 4)):
        payload = {"model": model, "messages": messages, "tools": tools, "tool_choice": "auto", "max_tokens": 2048}
        size = len(json.dumps(payload, separators=(",", ":"), allow_nan=False).encode())
        if (size > MAX_REQUEST_BYTES or request_bytes + size > MAX_TOTAL_REQUEST_BYTES
                or sum(row.get("total_tokens", 0) or 0 for row in usage) >= MAX_OBSERVED_TOKENS):
            return finish("budget_exhausted", "Stopped before another request: context or observed-token budget reached.")
        request_bytes += size
        receipt = {"request": len(receipts) + 1, "input_json_bytes": size, "status": "started"}
        receipts.append(receipt)
        try:
            response = client.chat.completions.create(**payload)
        except Exception:
            receipt["status"] = "failed"
            return finish("failed", "Provider request failed. No automatic retry; earlier usage and evidence are retained.")
        receipt.update(status="received", response_id=getattr(response, "id", None))
        raw_usage = getattr(response, "usage", None)
        raw_usage = raw_usage.model_dump() if hasattr(raw_usage, "model_dump") else raw_usage if isinstance(raw_usage, dict) else None
        if raw_usage is not None:
            usage.append(raw_usage)
        receipt["usage_reported"] = raw_usage is not None
        for origin, blob in (("usage", raw_usage or {}), ("response", getattr(response, "model_extra", None) or {})):
            if not isinstance(blob, dict):
                continue
            fields = {key: value for key, value in blob.items() if "cost" in key.lower() or key.lower() in ("currency", "billing")}
            if fields:
                costs.append({"request": receipt["request"], "origin": origin, "provider_fields": fields})
        if not getattr(response, "choices", None) or getattr(response.choices[0], "message", None) is None:
            receipt["status"] = "invalid_response"
            return finish("failed", "Provider returned no usable message; recorded usage is retained. No automatic retry.")
        choice = response.choices[0]
        receipt["finish_reason"] = choice.finish_reason
        message = choice.message
        if not message.tool_calls:
            last_answer = message.content or ""
            # Accept the same contract as JSON content, including a harmless code fence.
            text = last_answer.strip()
            if text.startswith("```"):
                text = "\n".join(text.splitlines()[1:-1])
            try:
                report = strict_json(text)
            except ValueError:
                last_validation = audit_legacy_report(last_answer, evidence.observations, evidence.comparison["ranking"])
                return finish("incomplete", "Structured cited report was not submitted; prose is retained but not fully fact-validated.")
            valid = submit(report)
            return finish("completed" if valid["valid"] and choice.finish_reason == "stop" else "incomplete",
                          None if valid["valid"] and choice.finish_reason == "stop" else "Report validation or provider completion failed.")
        # Retain standard tool conversation fields, not provider-specific reasoning blobs.
        messages.append({"role": "assistant", "content": message.content,
                         "tool_calls": [{"id": call.id, "type": "function", "function": {
                             "name": call.function.name, "arguments": call.function.arguments}}
                                        for call in message.tool_calls]})
        for call in message.tool_calls:
            tool_calls += 1
            if tool_calls > min(max_tool_calls, 8):
                return finish("budget_exhausted", "Tool-call budget reached; no extra tools executed.")
            try:
                arguments = strict_json(call.function.arguments)
            except ValueError:
                arguments = None
            if call.function.name == "submit_employee_report":
                outcome = submit(arguments)
                trace.append({"tool": call.function.name, "arguments": arguments, "result": outcome})
                if outcome["valid"] and choice.finish_reason in ("stop", "tool_calls"):
                    return finish("completed")
                if validation_attempts >= 2:
                    return finish("invalid_report", "Report still contradicts evidence or is incomplete after one correction opportunity.")
            elif not isinstance(arguments, dict):
                outcome = {"error": "Arguments must be a JSON object."}
            else:
                previous_facts = dict(evidence.facts)
                outcome = evidence.dispatch(call.function.name, arguments)
                if len(json.dumps(outcome, separators=(",", ":")).encode()) > 10000:
                    evidence.facts = previous_facts
                    outcome = {"error": "Response too large. Request fewer channels or fewer time points."}
                trace.append({"tool": call.function.name, "arguments": arguments, "result": outcome})
            messages.append({"role": "tool", "tool_call_id": call.id,
                             "content": json.dumps(outcome, separators=(",", ":"), allow_nan=False)})
    return finish("budget_exhausted", "No validated final report within the authorized request budget.")
