# Nemotron investigation review: case_005

Scope: the Monitoring page's explicit AI Investigation action. No paid requests,
deployment, dataset generation, benchmark changes or detector modifications were
performed during this review. The original saved investigation is retained byte for byte.

## Confirmed causes

The saved case_005 report has all six nonempty employee sections. They are written
as `**bold headings**`, while the old parser only recognized Markdown `#` headings.
It therefore reported zero sections and rejected substantial content for formatting.
This is separate from factual validity: simply accepting those headings would have
incorrectly promoted a flawed report.

The report describes `flow_229_lps` as negative, although all 24 available readings
are positive, from 320.76888067461846 to 377.5858530218106 L/s. It cites a reading at
00:30 when that channel is missing. It also mentions pressure sensor 245, which is
not a configured pressure channel. A flow sign describes the network model's link
orientation; it does not by itself establish leak outflow. Claimed hydraulic causes
and the relative adequacy of untested explanations were also stronger than the tools
could establish. No intervention or field outcome was observed.

Reported usage was three requests and 295,342 tokens: prompt counts 803, 145,311,
147,582 and completion counts 39, 26, 1,581. The bulk observations tool serialized
179,070 bytes. The conversation retained this payload for later requests. No cost or
currency was recorded, so a billed amount cannot be reconstructed from this trace.
Cached-token counts are preserved, but are not converted into a guessed price.

## Changes

- Monitoring opts into a compact investigation adapter through the existing agent
  entry point. The original low-level legacy agent mode remains available for
  compatibility; the CLI has not been changed by this Monitoring-focused update.
- The physics comparator still uses all 209 channels and the same candidate rankings.
  Compact context summarizes all-channel coverage, six automatically shortlisted
  channels, and the leading candidates plus normal operation. Shortlist departures
  are supporting cues, not a replacement detector or an explanation of which channel
  caused a ranking.
- Tools provide exact sensor summaries and paginated time series for any configured
  channel, up to four channels and twelve timestamps per request. Missing values
  remain null. Candidate scores come directly from the unchanged comparator.
  The complete readings can also be downloaded from the collapsed technical view.
- The initial compact case_005 context is 4,727 bytes, 97.4% smaller than the former
  bulk observations response. This is a byte-size comparison, not measured live
  token savings or a price estimate. Schemas and conversation overhead also consume tokens.
- A typed `submit_employee_report` tool replaces a brittle six-heading contract.
  The same JSON contract is accepted as response content. The server checks required
  fields, exposed evidence IDs, finite values, channel identifiers, units, numerical
  signs, pipe identifiers, candidate ranks, normal-operation comparison and uncertainty.
  The UI service independently reconstructs cited facts from the recorded tool requests.
- Numeric and sensor assertions are confined to structured citations. The short model
  summary rejects numeric/directional/causal-confirmation claims; possible causes,
  limitations and field actions are selected from bounded, explicitly hypothetical
  or prospective choices. Evidence values and their statistical/time contexts are
  rendered from checked tool facts, rather than rewritten by the model.
- New reports complete only after validation and a successful provider finish state.
  Invalid submissions get at most one correction opportunity within the authorized
  request budget. Persistent invalidity, missing structured evidence, budget exhaustion,
  truncation and provider/storage failures remain incomplete or failed. No automatic
  provider retries occur.
- Legacy headings are recognized across bold, numbered and Markdown formats. A
  conservative read-only legacy audit detects explicit sign/value/missing-time
  contradictions. It does not claim comprehensive validation of arbitrary prose,
  and cannot upgrade old responses to completed fact-validated reports.
- The employee view presents a short summary, sensor evidence, leading/alternative
  candidates, possible explanations, uncertainty and recommended actions. Original
  legacy responses and detailed tool traces stay collapsed and unchanged. Old successful
  API responses are distinguished from new evidence-checked completion.
- Request receipts count actual attempts, including failed calls and absent usage.
  Token usage and any provider-reported cost/currency fields are retained verbatim.
  Missing pricing information is displayed as unavailable, never zero.

## Bounds and practical limits

The Monitoring adapter permits at most four requests, eight executed tool calls,
2,048 output tokens per request, 24,000 serialized input bytes per request and
72,000 serialized input bytes across the attempt. An observed-token guard prevents
further requests once 32,000 reported tokens have accumulated. These are conservative
context/request controls, not a guaranteed currency cap or an exact token pre-estimate.
Provider-specific reasoning blobs are not copied back into subsequent prompts.
The existing two-attempt-per-alert reservation remains in place, including failures.

Validation checks cited evidence and the report contract. It does not establish a
hydraulic cause, proof of a physical leak, field accuracy, or the truth of every possible
free-language implication. Legacy prose is always identified as not fully validated.
Model tool/schema compliance, latency and actual cost savings on a live Nebius request
remain unverified because no paid inference was authorized for this implementation.
Historical results are not retuned or rewritten.

## Verification

The regression fixture preserves the actual case_005 answer, usage and original trace
hash without duplicating its full observations payload. Offline tests cover heading
recognition versus missing content; positive flow, null readings, invalid sensors,
units, values, ranks and pipes; concise validated completion; incomplete legacy prose;
bounded retrieval/context; failed requests with retained usage/cost; correction limits;
and UI visibility/collapsed traces. Mock provider cost values in tests are test data,
not a claim about Nebius prices.

Run the complete offline suite with optional chart rendering dependencies installed:

```powershell
python -m unittest discover -s tests -v
python scripts/product_integrity.py verify outputs/product_verification/nemotron_case005_before.json
```

The pre-change manifest includes all 1,536 original protected files, including the
case_005 trace. It excludes new additive verification artifacts and local operations
state. Use `requirements-test.txt` for JavaScript chart-runtime checks.

Final offline verification: **70 tests passed** in 43.251 seconds, including the
case_005 and UI regressions. All **1,536 protected original file hashes** are
unchanged. Compilation and whitespace/diff checks passed. No paid request was made;
new live-provider behavior and billed savings have not been verified.
