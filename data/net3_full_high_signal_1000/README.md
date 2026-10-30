# 1,000-case full-channel high-signal benchmark

This separate benchmark contains 800 development cases and 200 held-out cases. Each observation file has all 92 pressure and 117 flow channels.

| Split | Leak cases | Normal cases | Total |
|---|---:|---:|---:|
| Development | 640 | 160 | 800 |
| Held out | 160 | 40 | 200 |

The measurements were freshly simulated with seed `20261028` using the same high-signal ranges as the 500-case benchmark: leak openings of 28–35 mm, durations of 4–4.5 hours, and demand scales of 0.85–1.15. The existing case assignments (split, outcome, and leak pipe) were each used twice; measurements, leak parameters, demand variation, and sensor noise were generated anew. This makes a larger within-simulator comparison, but does not add new network types or independent leak-pipe assignments.

Classifier results and held-out predictions are in [`../net3_full_high_signal_1000_benchmark/report.md`](../net3_full_high_signal_1000_benchmark/report.md). Results measure performance on this benchmark distribution; they do not establish field performance.
