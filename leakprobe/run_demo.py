"""Run offline by default; use --live to request an optional LLM investigation."""
import argparse
import json
import uuid

from .paths import OUTPUTS, ROOT


def run_scripted_demo(case_id=None):
    from .net3_tools import Net3Investigation, dispatch_net3
    from .paths import NET3_DATA

    if not (NET3_DATA / "metadata.json").exists():
        raise FileNotFoundError("The full high-signal Net3 feed is missing. Restore it before running an investigation.")
    session = Net3Investigation(case_id)
    trace = []
    results = {}
    for name in ("get_observations", "get_network", "get_operation_records", "compare_hypotheses"):
        result = dispatch_net3(session, name, {})
        trace.append({"tool": name, "arguments": {}, "result": result})
        results[name] = result

    output = OUTPUTS / "traces"
    output.mkdir(parents=True, exist_ok=True)
    path = output / f"net3_full_high_signal_{session.case_id}_{uuid.uuid4().hex}_scripted_trace.json"
    payload = json.dumps(trace, indent=2)
    with path.open("x", encoding="utf-8") as stream:
        stream.write(payload)
    comparison = results["compare_hypotheses"]
    print(f"\nSCRIPTED NET3 INVESTIGATION — no LLM/API calls — {session.case_id}")
    print("Sensor feed: 92 pressure + 117 flow channels")
    print("Top-ranked fits:")
    visible = comparison["ranking"][:5]
    normal = next((row for row in comparison["ranking"] if row["scenario"] == "normal"), None)
    if normal and normal not in visible:
        visible.append(normal)
    for row in visible:
        label = "normal" if row["scenario"] == "normal" else f"pipe {row['leak_pipe']}"
        print(f"  {label}: normalized RMSE {row['normalized_rmse']:.3f}")
    print(f"\nAlert outcome: {comparison['decision']['prediction']}")
    if comparison["leading_scenarios_are_close"]:
        print("  Leading fits are close; review the result as ambiguous.")
    print("Fit scores rank candidate scenarios; they are not probabilities or field confirmation.")
    print(f"Open {path.relative_to(ROOT)} for the full evidence and ranking.")
    return trace


def run_scripted_net3(case_id=None):
    return run_scripted_demo(case_id)


def main():
    parser = argparse.ArgumentParser(description="Investigate a complete Net3 sensor feed with LeakProbe.")
    parser.add_argument("--case", help="Net3 case id; defaults to the first held-out case.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--scripted", action="store_true", help="Run offline without an LLM API call (default).")
    mode.add_argument("--live", action="store_true", help="Explicitly request live inference; API charges may apply.")
    args = parser.parse_args()
    if args.live:
        from .agent import run_live
        run_live(case_id=args.case)
    else:
        run_scripted_demo(args.case)


if __name__ == "__main__":
    main()
