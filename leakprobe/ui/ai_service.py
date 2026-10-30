"""Explicit, bounded adapter to the existing Nemotron tool loop; no calls on import."""
import importlib.util
import json
import os
import sqlite3
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
from leakprobe.ui.live_policy import LiveDenied, authority
from leakprobe.ui.protected_client import ProtectedClient, provider

EMPLOYEE_INSTRUCTIONS = SYSTEM
INSPECTION_MODE_ENV = "LEAKPROBE_INSPECTION_MODE"
INFERENCE_DISABLED_MESSAGE = (
    "New AI investigations are disabled in this inspection session. "
    "Saved reports, sensor analysis and employee review remain available.")


class InferenceUnavailableError(RuntimeError):
    """A local policy prohibits provider execution; this is not a model failure."""


def inference_disabled():
    return os.getenv(INSPECTION_MODE_ENV, "").strip().lower() in ("1", "true", "yes")


def availability(authorization=None, browser_session=None):
    if inference_disabled():
        return False, INFERENCE_DISABLED_MESSAGE
    try:
        control = authority()
        control.ready(authorization, browser_session)
    except LiveDenied as exc:
        return False, str(exc)
    if importlib.util.find_spec("openai") is None:
        return False, "Unavailable: deploy the restricted live entrypoint with its live runtime requirements."
    return True, "Restricted live Nemotron is ready on request. Paid requests require current operator and spending authorization."


def provider_client(lease=None):
    if inference_disabled():
        raise InferenceUnavailableError(INFERENCE_DISABLED_MESSAGE)
    try:
        control = authority()
        if lease is None or control.active is not lease:
            raise LiveDenied("A current server-side investigation authorization is required.")
        return provider(control, lease)
    except LiveDenied as exc:
        raise InferenceUnavailableError(str(exc)) from None


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


def run_investigation(alert, store, client_factory=None, output=None, authorization=None, browser_session=None):
    """Only call from an employee's explicit button action. Failures never retry."""
    # Enforce inspection policy even for direct calls or an injected client factory.
    # No attempt is reserved, trace written or provider constructed for a blocked action.
    if inference_disabled():
        return {"status": "unavailable", "answer": "", "error": INFERENCE_DISABLED_MESSAGE,
                "request_count": 0, "trace": []}
    # Both direct calls and injected test clients must pass the same server authority.
    # The offline entrypoint never obtains this authority, even with a key/live flag.
    try:
        control = authority()
        lease = control.begin(authorization, browser_session, alert.get("alert_id"))
    except LiveDenied as exc:
        return {"status": "unavailable", "answer": "", "error": str(exc), "request_count": 0, "trace": []}
    model = control.policy.model
    result, client, request_id = None, None, None
    try:
        session = Net3Investigation(alert["case_id"])
        validate_feed(session.observations, session.metadata, session.hypotheses["normal"])
        current = build_alert({"case_id": session.case_id, "observations": session.observations,
                               "comparison": session.compare_hypotheses()})
        if current["alert_id"] != alert["alert_id"]:
            raise ValueError("Feed comparison changed; refresh before investigating.")
        request_id = store.reserve_ai(alert["alert_id"])
        client = ProtectedClient(control, lease, client_factory() if client_factory else provider_client(lease))
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
            result = {"status": "failed", "answer": "", "trace": [], "usage": [], "request_count": lease['requests'],
                      "error": "Provider request failed. Check host credentials, quota and model access. No automatic retry."}
    finally:
        try:
            if client is not None:
                client.close()
        except Exception:
            pass  # Never expose provider cleanup exception text.
        control.end(lease)
    if lease['stop'] and result.get('status') != 'completed':
        result['error'] = lease['stop']
    if control.poisoned:
        result.update(status='incomplete', error=lease['stop'] or 'Live usage verification failed. Requests locked.')
    result.update(case_id=alert["case_id"], alert_id=alert["alert_id"],
                  feed_fingerprint=alert["feed_fingerprint"], model=model,
                  saved_at_utc=datetime.now(timezone.utc).isoformat())
    result['origin'] = 'live_nebius'
    result['live_budget'] = control.audit(lease)
    result['tool_loop_attempt_count'] = result.get('request_count', 0)
    result['request_count'] = lease['requests']
    for index, receipt in enumerate(result.get('requests', [])):
        if index >= lease['requests']:
            receipt['status'] = 'blocked_before_provider_call'
    result.setdefault("budget", {"max_requests": 4, "max_tool_calls": 8, "max_output_tokens_per_request": 2048})
    result["usage_summary"] = usage_summary(result)
    if request_id is None:
        return {**result, 'status': 'failed', 'error': 'Investigation could not start. No automatic retry.'}
    try:
        target = Path(output) if output is not None else OUTPUTS / 'restricted_live' / 'traces'
        if target.resolve().is_relative_to((ROOT / 'demo_assets').resolve()):
            raise ValueError('Historical saved reports are read-only.')
        path = save_trace(result, target)
        store.finish_ai(alert["alert_id"], request_id, result["status"], path.name)
    except (OSError, ValueError, sqlite3.Error):
        try:
            store.finish_ai(alert["alert_id"], request_id, "storage_failed")
        except (OSError, ValueError, sqlite3.Error):
            pass
        return {**result, "status": "storage_failed", "error": "Investigation could not be saved. No automatic retry."}
    return {**result, "trace_file": path.name}
