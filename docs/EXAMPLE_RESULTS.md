# Current full-channel high-signal results

The active benchmark has 500 cases, each with 92 pressure channels and 117 flow channels. The held-out test set contains 80 leak cases and 20 normal cases.

## Physics-based detector

The reference-pattern matcher uses the complete feed for each case. On the held-out split it produced:

| Metric | Result |
|---|---:|
| Confusion matrix (TP / FN / FP / TN) | 76 / 4 / 1 / 19 |
| Precision | 98.7% (76/77) |
| Recall | 95.0% (76/80) |
| Accuracy | 95.0% |
| Specificity | 95.0% |
| Exact pipe across actual leaks | 93.8% (75/80) |

These cases use intentionally large leaks (28–35 mm) lasting 4–4.5 hours. Demand ranges also match across the two splits. This controlled setup makes the task easier than detecting small leaks under changing real-world conditions. Fit scores are not probabilities, and these figures do not establish field performance.

## Recall-led classifiers

The classifier threshold is selected from out-of-fold development predictions to target at least 90% leak recall. Held-out results can differ from the target:

| Variant | Precision | Recall | TP / FN / FP / TN |
|---|---:|---:|---:|
| Baseline | 97.2% | 87.5% | 70 / 10 / 2 / 18 |
| Class weight | 97.1% | 85.0% | 68 / 12 / 2 / 18 |
| SMOTE | 100.0% | 80.0% | 64 / 16 / 0 / 20 |

SMOTE made no false alarms in these 20 normal cases, but missed 16 of the 80 leaks. The baseline caught six more leaks with two false alarms. Precision and recall should be read alongside the counts.

## 1,000-case sample-size experiment

The companion experiment trains on 800 cases and evaluates on 200 held-out cases (160 leaks and 40 normal cases). It uses the same full 92/117 channel layout and high-signal ranges. Existing split, outcome, and leak-pipe assignments were each used twice, with fresh simulated readings. It adds more measurement variations but no new candidate-pipe assignments.

| Variant | Precision | Recall | TP / FN / FP / TN |
|---|---:|---:|---:|
| Baseline | 100.0% | 78.1% | 125 / 35 / 0 / 40 |
| Class weight | 100.0% | 78.1% | 125 / 35 / 0 / 40 |
| SMOTE | 100.0% | 78.8% | 126 / 34 / 0 / 40 |

There were no false alarms among the 40 held-out normal cases, but each variant missed about one in five leaks. In the 640-leak/160-normal development split, default SMOTE oversamples normal examples because normal is the minority class. These results measure this controlled simulation setup, not field performance. See the [full report](../data/net3_full_high_signal_1000_benchmark/report.md).

## Where the “all leaks caught, all normal cases flagged” result came from

That result was from the retired standard-range classifier on a smaller 12-pressure/8-flow dataset. It predicted all 100 test cases as leaks: 80 true positives, 20 false alarms, no missed leaks, and no true negatives. That is 100% recall but 80% precision and 0% specificity.

The classifier threshold was chosen on development folds for a high-recall target. On the old held-out data, every normal case scored above the threshold. Training and test demand ranges also differed, which made normal test cases unlike the normal examples in training. The all-leak result was therefore an unsuitable alert operating point, and that dataset is no longer used.

The current saved classifier report is [here](../data/net3_full_high_signal_benchmark/report.md). Full-channel physics and classifier results are in the [evaluation report](../outputs/evaluations/net3_full_pipes_comparison.md).
