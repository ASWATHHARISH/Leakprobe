"""Explicit, bounded adapter to the existing Nemotron tool loop; no calls on import."""
import importlib.util
import json
import os
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

from leakprobe.agent import investigate
from leakprobe.employee_investigator import SYSTEM, usage_summary
from leakprobe.investigation_evidence import InvestigationEvidence
from leakprobe.investigation_report import audit_legacy_report, parse_legacy_sections, validate_report
from leakprobe.net3_tools import Net3Investigation
from leakprobe.paths import OUTPUTS, ROOT
from leakprobe.ui.operations import build_alert, validate_feed
from leakprobe.ui.runtime_settings import live_ai_enabled, demo_mode

EMPLOYEE_INSTRUCTIONS = SYSTEM
INSPECTION_MODE_ENV = "LEAKPROBE_INSPECTION_MODE"
INFERENCE_DISABLED_MESSAGE = (
    "New AI investigations are disabled in this inspection session. "
    "Saved reports, sensor analysis and employee review remain available.")


class InferenceUnavailableError(RuntimeError):
    """A local policy prohibits provider execution; this is not a model failure."""


def inference_disabled():
    return os.getenv(INSPECTION_MODE_ENV, "").strip().lower() in ("1", "true", "yes")


def availability():
    if inference_disabled():
        return False, INFERENCE_DISABLED_MESSAGE
    if not live_ai_enabled():
        return False, "New AI requests are disabled. Saved investigations remain available."
    if importlib.util.find_spec("dotenv"):
        from dotenv import load_dotenv
        load_dotenv(ROOT / ".env", override=False)
    if not os.getenv("NEBIUS_API_KEY", "").strip() or os.getenv("NEBIUS_API_KEY") == "replace_with_your_key":
        return False, "Unavailable: configure NEBIUS_API_KEY on the host to enable Nemotron. Monitoring works offline."
    if importlib.util.find_spec("openai") is None:
        return False, "Unavailable: install requirements-llm.txt to enable the optional provider adapter."
    return True, "Ready on request. This sends this demo window to Nebius and can incur API charges."


def provider_client():
    if inference_disabled():
        raise InferenceUnavailableError(INFERENCE_DISABLED_MESSAGE)
    if not live_ai_enabled():
        raise InferenceUnavailableError("Live AI requests require explicit host configuration outside public demo mode.")
    from openai import OpenAI
    base = os.getenv("NEBIUS_BASE_URL", "https://api.tokenfactory.us-central1.nebius.com/v1/")
    if not base.startswith("https://"):
        raise ValueError("An HTTPS provider endpoint is required.")
    return OpenAI(api_key=os.environ["NEBIUS_API_KEY"], base_url=base, timeout=30, max_retries=0)


def save_trace(result, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    path = output / f"net3_full_high_signal_{result['case_id']}_{uuid.uuid4().hex}_llm_trace.json"
    payload = json.dumps(result, indent=2, allow_nan=False)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=output, suffix=".tmp", delete=False) as stream:
        temporary = Path(stream.name)
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    try:
        # Hard-link publication is atomic and fails if the destination already exists.
        os.link(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
    return path


def run_investigation(alert, store, client_factory=None, output=None):
    """Only call from an employee's explicit button action. Failures never retry."""
    # Enforce inspection policy even for direct calls or an injected client factory.
    # No attempt is reserved, trace written or provider constructed for a blocked action.
    if inference_disabled():
        return {"status": "unavailable", "answer": "", "error": INFERENCE_DISABLED_MESSAGE,
                "request_count": 0, "trace": []}
    if demo_mode():
        return {"status": "unavailable", "answer": "", "error": "New AI requests are disabled in the public demo. Saved investigations remain available.",
                "request_count": 0, "trace": []}
    if client_factory is None:
        ready, reason = availability()
        if not ready:
            return {"status": "unavailable", "answer": "", "error": reason, "request_count": 0, "trace": []}
    session = Net3Investigation(alert["case_id"])
    validate_feed(session.observations, session.metadata, session.hypotheses["normal"])
    current = build_alert({"case_id": session.case_id, "observations": session.observations,
                           "comparison": session.compare_hypotheses()})
    if current["alert_id"] != alert["alert_id"]:
        raise ValueError("Feed or reference comparison changed. Refresh the alert before starting AI.")
    request_id = store.reserve_ai(alert["alert_id"])
    model = os.getenv("NEBIUS_MODEL", "nvidia/nemotron-3-super-120b-a12b")
    result = None
    try:
        client = (client_factory or provider_client)()
        result = investigate(client, model, max_rounds=4, max_tool_calls=8,
                             case_id=alert["case_id"], instructions=EMPLOYEE_INSTRUCTIONS, compact=True)
        if result.get("status") == "completed":
            # Reconstruct cited facts locally from the exposed tool requests, not model prose.
            verifier = InvestigationEvidence(session)
            for step in result.get("trace", []):
                arguments = step.get("arguments", {})
                if isinstance(arguments, str):
                    arguments = json.loads(arguments)
                if isinstance(arguments, dict) and step.get("tool") != "submit_employee_report":
                    verifier.dispatch(step.get("tool"), arguments)
            result["validation"] = validate_report(result.get("report"), verifier)
            if result.get("validation_version") != "cited-facts-v1" or not result["validation"]["valid"]:
                result["status"] = "incomplete"
                result["error"] = "No complete, evidence-validated employee report was submitted. Raw output is retained."
        result["report_sections"] = parse_legacy_sections(result.get("answer", ""))
        if result.get("status") != "completed" and not result.get("validation_version"):
            result["validation"] = audit_legacy_report(result.get("answer", ""), session.observations, session.compare_hypotheses()["ranking"])
    except Exception:
        # Provider exception text may contain credentials or request content.
        if isinstance(result, dict):
            result.update(status="failed", error="Investigation post-processing failed; recorded usage and evidence are retained. No automatic retry.")
        else:
            result = {"status": "failed", "answer": "", "trace": [], "usage": [], "request_count": 0,
                      "error": "Provider request failed. Check host credentials, quota and model access. No automatic retry."}
    result.update(case_id=alert["case_id"], alert_id=alert["alert_id"],
                  feed_fingerprint=alert["feed_fingerprint"], model=model,
                  saved_at_utc=datetime.now(timezone.utc).isoformat())
    result.setdefault("budget", {"max_requests": 4, "max_tool_calls": 8, "max_output_tokens_per_request": 2048})
    result["usage_summary"] = usage_summary(result)
    try:
        path = save_trace(result, output or OUTPUTS / "traces")
    except OSError:
        store.finish_ai(alert["alert_id"], request_id, "storage_failed")
        return {**result, "status": "storage_failed", "error": "Investigation could not be saved. No automatic retry."}
    store.finish_ai(alert["alert_id"], request_id, result["status"], path.name)
    return {**result, "trace_file": path.name}
