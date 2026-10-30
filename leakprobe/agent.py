"""Optional live Nemotron loop for the full-channel Net3 investigation."""
import argparse
import json
import os
import uuid
from datetime import datetime, timezone

from .paths import OUTPUTS, ROOT


def investigate(client, model, max_rounds=8, max_tool_calls=16, case_id=None, instructions=None, compact=False):
    if compact:
        from .employee_investigator import investigate_employee
        return investigate_employee(client, model, case_id=case_id, max_rounds=max_rounds, max_tool_calls=max_tool_calls)
    from .net3_tools import Net3Investigation, dispatch_net3, net3_tool_schemas

    session = Net3Investigation(case_id)
    available_tools = net3_tool_schemas()
    system = """You are LeakProbe, investigating one Net3 water-network case.
Use the tools to inspect timestamped observations, network information, and the
normal-operation/candidate-leak comparison. Every case provides all 92 pressure
and all 117 flow channels; use that full sensor feed. No additional sensor
selection or field collection is available in this workflow. Explain what the
ranked fit scores show, but do not call them probabilities or claim field
confirmation. State uncertainty and a practical review step."""
    if instructions:
        system += "\n" + instructions
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": f"Investigate Net3 case {session.case_id} using the full pressure and flow feed."},
    ]
    trace, usage = [], []
    count = 0
    for _ in range(max_rounds):
        response = client.chat.completions.create(
            model=model, messages=messages, tools=available_tools,
            tool_choice="auto", max_tokens=2048,
        )
        if response.usage:
            usage.append(response.usage.model_dump())
        message = response.choices[0].message
        if not message.tool_calls:
            answer = message.content or ""
            return {
                "status": "completed" if answer and response.choices[0].finish_reason == "stop" else "incomplete",
                "answer": answer, "trace": trace, "usage": usage,
                "case_id": session.case_id,
            }

        messages.append(message.model_dump(exclude_none=True))
        for call in message.tool_calls:
            count += 1
            if count > max_tool_calls:
                result = {"error": "Tool-call budget exhausted."}
            else:
                try:
                    args = json.loads(call.function.arguments)
                    result = dispatch_net3(session, call.function.name, args)
                except (json.JSONDecodeError, TypeError):
                    result = {"error": "Arguments must be valid JSON matching the schema."}
            trace.append({"tool": call.function.name,
                          "arguments": call.function.arguments, "result": result})
            messages.append({"role": "tool", "tool_call_id": call.id,
                             "content": json.dumps(result, allow_nan=False)})
            print(f"Tool: {call.function.name}")
        if count >= max_tool_calls:
            break
    return {
        "status": "budget_exhausted",
        "answer": "Stopped without a final interpretation: iteration/tool limit reached.",
        "trace": trace, "usage": usage, "case_id": session.case_id,
    }


def run_live(case_id=None):
    from dotenv import load_dotenv
    from openai import APIError, OpenAI

    load_dotenv(ROOT / ".env")
    key = os.getenv("NEBIUS_API_KEY", "")
    if not key or key == "replace_with_your_key":
        raise SystemExit("Set NEBIUS_API_KEY in .env. See README.md. No API call was made.")
    model = os.getenv("NEBIUS_MODEL", "nvidia/nemotron-3-super-120b-a12b")
    base = os.getenv("NEBIUS_BASE_URL", "https://api.tokenfactory.us-central1.nebius.com/v1/")
    if not base.startswith("https://"):
        raise SystemExit("Use an HTTPS provider endpoint.")
    print("Live API mode sends the full Net3 sensor feed to your configured provider. Calls may incur charges.")
    client = OpenAI(api_key=key, base_url=base, timeout=60, max_retries=0)
    try:
        result = investigate(client, model, case_id=case_id)
    except APIError as exc:
        raise SystemExit(
            f"Provider request failed ({type(exc).__name__}). Check key, endpoint, model access, quota and tool support. No automatic retry."
        ) from None
    output = OUTPUTS / "traces"
    output.mkdir(parents=True, exist_ok=True)
    result["saved_at_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    trace_name = f"net3_full_high_signal_{result.get('case_id') or case_id or 'test'}_{uuid.uuid4().hex}_llm_trace.json"
    payload = json.dumps(result, indent=2)
    with (output / trace_name).open("x", encoding="utf-8") as stream:
        stream.write(payload)
    print("\n" + result["answer"])
    print(f"\nSaved outputs/traces/{trace_name}. LLM conclusions are not independently verified.")


def main():
    parser = argparse.ArgumentParser(description="Run a full-channel Net3 investigation with Nemotron.")
    parser.add_argument("--case", help="Net3 case id; defaults to the first held-out case.")
    args = parser.parse_args()
    run_live(case_id=args.case)


if __name__ == "__main__":
    main()
