"""Employee report contract, cited-fact validation and read-only legacy diagnostics."""
import math
import re
import unicodedata

import pandas as pd
from jsonschema import Draft202012Validator

from .tool_schemas import tool
from .ui.operations import REPORT_SECTIONS

EXPLANATIONS = {"demand_change": "A change in demand could also affect the readings.",
                "sensor_error": "Sensor bias or drift is an alternative to investigate.",
                "operating_state": "An unrecorded operating change could affect the pattern."}
LIMITATIONS = {"fit_not_probability": "Fit errors are comparison measures, not leak probabilities.",
               "not_field_verified": "The candidate has not been verified in the field.",
               "model_mismatch": "Unmodeled conditions could affect the ranking.",
               "missing_readings": "Some sensor readings are missing.",
               "no_operations_records": "No operating records are available for this window."}
ACTIONS = {"check_sensor_health": "Check affected sensors for faults, calibration issues or missing readings.",
           "review_operating_changes": "Review recent demand, pump and valve changes with the operations team.",
           "verify_candidate_in_field": "Verify the candidate location using approved field procedures before confirming a leak."}


def object_schema(properties):
    return {"type": "object", "properties": properties, "required": list(properties), "additionalProperties": False}


CANDIDATE = object_schema({"pipe": {"type": ["string", "null"]}, "rank": {"type": "integer", "minimum": 1},
                           "fit_score": {"type": "number", "minimum": 0}, "fact_id": {"type": "string"}})
CLAIM = object_schema({"fact_id": {"type": "string"}, "value": {"type": "number"},
                      "unit": {"enum": ["m", "L/s"]}, "channel": {"type": "string"},
                      "sign": {"enum": ["positive", "negative", "zero"]}})
REPORT_SCHEMA = object_schema({
    "summary": {"type": "string", "minLength": 20, "maxLength": 280},
    "evidence": {"type": "array", "items": CLAIM, "minItems": 2, "maxItems": 4},
    "leading_candidate": CANDIDATE,
    "alternatives": {"type": "array", "items": CANDIDATE, "minItems": 1, "maxItems": 3},
    "possible_explanations": {"type": "array", "items": {"enum": list(EXPLANATIONS)}, "minItems": 1, "maxItems": 3, "uniqueItems": True},
    "uncertainty": {"type": "array", "items": {"enum": list(LIMITATIONS)}, "minItems": 2, "maxItems": 5, "uniqueItems": True},
    "actions": {"type": "array", "items": {"enum": list(ACTIONS)}, "minItems": 1, "maxItems": 3, "uniqueItems": True},
})


def report_tool():
    return tool("submit_employee_report", "Submit a concise report with exact cited facts. Content is validated before completion.",
                REPORT_SCHEMA["properties"], REPORT_SCHEMA["required"])


def validate_report(report, evidence):
    errors = ["schema: " + "/".join(map(str, error.path)) + " " + error.message
              for error in Draft202012Validator(REPORT_SCHEMA).iter_errors(report)]
    if errors:
        return {"valid": False, "errors": errors[:8], "scope": "Schema and exposed numerical evidence only; no field or causal verification."}
    summary = report["summary"]
    if re.search(r"\d|\b(?:negative|positive|zero|hundred|thousand|percent|reverse|reversal|outflow|inflow|upstream|downstream|confirmed|proves?|guarantees?|caused|causes|depression|drop|increase|decrease|bar|psi|lps|litres?|liters?|metres?|meters?)\b", summary, re.I):
        errors.append("summary: put numerical, directional and sensor claims only in cited evidence; no causal or field-confirmation claims.")
    def check(item, candidate=False):
        fact = evidence.facts.get(item["fact_id"])
        if fact is None:
            errors.append(f"Unexposed or unknown evidence: {item['fact_id']}")
            return
        key = "fit_score" if candidate else "value"
        if not math.isfinite(item[key]) or not math.isclose(item[key], fact["value"], rel_tol=1e-6, abs_tol=5e-4):
            errors.append(f"Numerical contradiction: {item['fact_id']}")
        if candidate:
            if fact["unit"] != "normalized_rmse" or item["pipe"] != fact.get("pipe") or item["rank"] != fact.get("rank"):
                errors.append(f"Candidate/rank contradiction: {item['fact_id']}")
        elif item["channel"] != fact["channel"] or item["unit"] != fact["unit"] or item["sign"] != fact["sign"]:
            errors.append(f"Sensor/unit/sign contradiction: {item['fact_id']}")
        if not candidate:
            value_sign = "positive" if item["value"] > 0 else "negative" if item["value"] < 0 else "zero"
            if value_sign != fact["sign"]:
                errors.append(f"Claimed value has the wrong sign: {item['fact_id']}")
    for claim in report["evidence"]:
        check(claim)
    check(report["leading_candidate"], candidate=True)
    winner = evidence.comparison["ranking"][0]
    if report["leading_candidate"]["pipe"] != winner["leak_pipe"] or report["leading_candidate"]["rank"] != 1:
        errors.append("Leading candidate must match the unchanged detector ranking.")
    seen = {report["leading_candidate"]["pipe"]}
    for alternative in report["alternatives"]:
        check(alternative, candidate=True)
        if alternative["pipe"] in seen:
            errors.append("Duplicate candidate or winner repeated as an alternative.")
        seen.add(alternative["pipe"])
    if winner["leak_pipe"] is not None and None not in seen:
        errors.append("Include the normal-operation hypothesis as an alternative.")
    if not {"fit_not_probability", "not_field_verified"}.issubset(report["uncertainty"]):
        errors.append("Required uncertainty: fit_not_probability and not_field_verified.")
    if "missing_readings" in report["uncertainty"] and not evidence.observations[evidence.channels].isna().any().any():
        errors.append("Missing-readings claim is not supported.")
    if len({item["channel"] for item in report["evidence"]}) != len(report["evidence"]):
        errors.append("Use distinct sensor channels in the short evidence list.")
    return {"valid": not errors, "errors": errors,
            "scope": "Schema, exposed values, identifiers, units, signs and ranks checked. Causes remain hypotheses; no field verification."}


def render_report_markdown(report, evidence):
    lines = [f"## {REPORT_SECTIONS[0]}", report["summary"], f"## {REPORT_SECTIONS[1]}"]
    for claim in report["evidence"]:
        fact = evidence.facts[claim["fact_id"]]
        context = fact.get("timestamp_utc", fact.get("statistic", ""))
        lines.append(f"- {fact['channel']}: {fact['value']:.6g} {fact['unit']} ({context}; {fact['sign']}; evidence {fact['fact_id']}).")
    lead = report["leading_candidate"]
    name = f"Pipe {lead['pipe']}" if lead["pipe"] else "Normal operation"
    lines += [f"## {REPORT_SECTIONS[2]}", f"{name} ranks first with fit error {lead['fit_score']:.6g}; lower is closer across all 209 channels.",
              f"## {REPORT_SECTIONS[3]}"]
    for row in report["alternatives"]:
        name = f"Pipe {row['pipe']}" if row["pipe"] else "Normal operation"
        lines.append(f"- {name}: rank {row['rank']}, fit error {row['fit_score']:.6g}.")
    lines += [EXPLANATIONS[key] for key in report["possible_explanations"]]
    lines += [f"## {REPORT_SECTIONS[4]}", *[f"- {LIMITATIONS[key]}" for key in report["uncertainty"]],
              f"## {REPORT_SECTIONS[5]}", *[f"- {ACTIONS[key]}" for key in report["actions"]]]
    return "\n".join(lines)


def parse_legacy_sections(answer):
    """Recognize headings without changing saved text or relaxing content requirements."""
    canonical = {title.casefold(): title for title in REPORT_SECTIONS}
    aliases = {"summary": REPORT_SECTIONS[0], "sensor evidence": REPORT_SECTIONS[1],
               "alternatives": REPORT_SECTIONS[3], "uncertainty & limitations": REPORT_SECTIONS[4],
               "verification actions": REPORT_SECTIONS[5]}
    sections, current = {}, None
    for line in answer.splitlines():
        title = re.sub(r"^#{1,6}\s*", "", line.strip()).strip("* ")
        title = re.sub(r"^\d+[.)]\s*", "", title).strip("* :").casefold()
        heading = canonical.get(title) or aliases.get(title)
        if heading:
            current = heading
            sections.setdefault(current, [])
        elif current:
            sections[current].append(line)
    return {key: "\n".join(value).strip().strip("-\n ") for key, value in sections.items() if "\n".join(value).strip().strip("-\n ")}


def audit_legacy_report(answer, observations, ranking=None):
    """Partial conservative audit of old free text; never labels it fully validated."""
    text = unicodedata.normalize("NFKC", answer).replace("**", "")
    for dash in ("\u2212", "\u2011", "\u2010"):
        text = text.replace(dash, "-")
    errors = []
    if ranking and "all leak candidates improve" in text.lower():
        normal = next((row for row in ranking if row.get("scenario") == "normal"), None)
        if normal:
            normal_score = normal.get("normalized_rmse", normal.get("score"))
            if any(row.get("scenario") != "normal" and row.get("normalized_rmse", row.get("score")) >= normal_score
                   for row in ranking):
                errors.append("Ranking contradiction: not all leak candidates improve on normal operation.")
    for paragraph in text.splitlines():
        sensor = re.search(r"\b(pressure|flow)(?:\s+channel\s*|_)(\d+)(?:\s*|_)(m|lps)\b", paragraph, re.I)
        if not sensor:
            continue
        group, identifier, _ = sensor.groups()
        channel = f"{group.lower()}_{identifier}_{'m' if group.lower() == 'pressure' else 'lps'}"
        if channel not in observations:
            errors.append(f"Unknown sensor: {channel}")
            continue
        valid = observations[channel].dropna()
        if len(valid) and "negative" in paragraph.lower() and (valid > 0).all():
            errors.append(f"Flow-sign contradiction: {channel} has only positive observed readings.")
        if len(valid) and "positive" in paragraph.lower() and (valid < 0).all():
            errors.append(f"Flow-sign contradiction: {channel} has only negative observed readings.")
        for value, unit, time in re.findall(r"(-?\d+(?:\.\d+)?)\s*(lps|L/s|m)\s+at\s*(\d\d:\d\d)", paragraph, re.I):
            rows = observations.loc[pd.to_datetime(observations["timestamp_utc"], utc=True).dt.strftime("%H:%M") == time, channel]
            if len(rows) != 1 or pd.isna(rows.iloc[0]):
                errors.append(f"Unsupported reading: {channel} at {time} is missing or ambiguous.")
            elif not math.isclose(float(value), float(rows.iloc[0]), abs_tol=.051, rel_tol=1e-6):
                errors.append(f"Numerical contradiction: {channel} at {time}.")
    sections = parse_legacy_sections(answer)
    return {"valid": False, "errors": list(dict.fromkeys(errors)), "sections_found": list(sections),
            "missing_sections": [name for name in REPORT_SECTIONS if name not in sections],
            "scope": "Partial free-text audit only. Legacy prose is not fully fact-validated."}
