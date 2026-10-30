"""Read-only adapters for saved investigations. No scoring or provider requests."""
from datetime import datetime, timezone
import math

from leakprobe.ui.operations import matching_investigation


def is_validated_report(run):
    """Keep the existing cited-facts completion contract; legacy prose never qualifies."""
    return (isinstance(run, dict) and run.get("status") == "completed"
            and run.get("validation_version") == "cited-facts-v1"
            and isinstance(run.get("validation"), dict)
            and run["validation"].get("valid") is True
            and isinstance(run.get("report"), dict))


def saved_comparison(run):
    """Normalize recorded legacy rows or compact fit facts without changing their scores."""
    comparisons = [step["result"] for step in run.get("trace", [])
                   if isinstance(step, dict) and step.get("tool") == "compare_hypotheses"
                   and isinstance(step.get("result"), dict)
                   and isinstance(step["result"].get("ranking"), list)]
    if not comparisons:
        return None
    comparison = comparisons[-1]
    rows, skipped = [], 0
    for index, row in enumerate(comparison["ranking"], 1):
        if not isinstance(row, dict):
            skipped += 1
            continue
        scenario = row.get("scenario")
        if scenario == "normal" or isinstance(scenario, str) and scenario.startswith("leak_pipe:"):
            pipe = None if scenario == "normal" else scenario.split(":", 1)[1]
            score, rank = row.get("normalized_rmse"), row.get("rank", index)
        elif "pipe" in row and isinstance(row.get("fit"), dict):
            pipe = row["pipe"]
            scenario = "normal" if pipe is None else f"leak_pipe:{pipe}"
            score, rank = row["fit"].get("value"), row.get("rank")
        else:
            skipped += 1
            continue
        if (isinstance(score, bool) or not isinstance(score, (int, float))
                or not math.isfinite(score) or score < 0
                or isinstance(rank, bool) or not isinstance(rank, int) or rank < 1
                or pipe is not None and (not isinstance(pipe, str) or not pipe)):
            skipped += 1
            continue
        rows.append({"scenario": scenario, "leak_pipe": pipe, "normalized_rmse": score, "rank": rank})
    return {"ranking": rows, "skipped_rows": skipped,
            "score_meaning": comparison.get("score_meaning") or comparison.get("fit_meaning")
            or "Recorded fit error, not a probability. Lower is closer."}


def _current_signature_matches(run, alert):
    """An ID match cannot override an explicitly contradictory feed or recorded fit."""
    if run.get("feed_fingerprint") and run["feed_fingerprint"] != alert.get("feed_fingerprint"):
        return False
    signature = alert.get("comparison_signature", [])
    comparison = saved_comparison(run)
    if signature and comparison:
        expected = {row["scenario"]: (rank, row["score"]) for rank, row in enumerate(signature, 1)}
        if comparison["skipped_rows"]:
            return False
        for row in comparison["ranking"]:
            current = expected.get(row["scenario"])
            if current is None or current[0] != row["rank"] or not math.isclose(
                    current[1], row["normalized_rmse"], rel_tol=1e-12, abs_tol=1e-10):
                return False
    return True


def _saved_time(run):
    try:
        value = datetime.fromisoformat(run.get("saved_at_utc", "").replace(" UTC", "+00:00").replace("Z", "+00:00"))
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)
    except (TypeError, ValueError, AttributeError):
        return datetime.min.replace(tzinfo=timezone.utc)


def select_investigations(runs, alert, observations=None):
    matches = [run for run in runs if isinstance(run, dict)
               and _current_signature_matches(run, alert)
               and matching_investigation([run], alert, observations) is not None]
    matches.sort(key=_saved_time, reverse=True)
    return {"latest": matches[0] if matches else None,
            "validated": next((run for run in matches if is_validated_report(run)), None)}
