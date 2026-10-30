# Full-channel high-signal Net3 evaluation

The active dataset contains 500 cases. Every observation has **92 pressure columns and 117 flow columns**. The held-out split has 80 leak cases and 20 normal cases. Leak openings are 28–35 mm and last 4–4.5 hours; leak and normal demand ranges match across train and test.

## Physics-based reference-pattern matcher

The detector compares the complete sensor feed with normal and candidate-pipe simulations. It does not use a calibrated rejection cutoff for this high-signal dataset.

| Held-out metric | Result |
|---|---:|
| Confusion matrix (TP / FN / FP / TN) | 76 / 4 / 1 / 19 |
| Accuracy | 95.0% |
| Leak precision | 98.7% (76/77) |
| Leak recall | 95.0% (76/80) |
| Specificity | 95.0% (19/20) |
| Balanced accuracy | 95.0% |
| F1 | 96.8% |
| Exact pipe across actual leak cases | 93.8% (75/80) |

The ranking score is a fit error, not a probability. One detected leak was assigned to the wrong candidate pipe.

## Descriptive result across all 500 cases

This includes the 400 development cases as well as the 100 held-out cases, so it is descriptive rather than an independent estimate.

| Metric | All 500 cases |
|---|---:|
| Confusion matrix (TP / FN / FP / TN) | 389 / 11 / 28 / 72 |
| Leak precision | 93.3% (389/417) |
| Leak recall | 97.2% (389/400) |
| Accuracy | 92.2% |
| Specificity | 72.0% |
| Balanced accuracy | 84.6% |
| F1 | 95.2% |
| Exact pipe across actual leak cases | 89.2% (357/400) |

## Recall-led classifier benchmark

The classifier threshold targets at least 90% recall on out-of-fold development predictions. The held-out set is evaluated separately and can fall below that target.

| Variant | Precision | Recall | F1 | Balanced accuracy | TP / FN / FP / TN |
|---|---:|---:|---:|---:|---:|
| Baseline | 97.2% | 87.5% | 92.1% | 88.8% | 70 / 10 / 2 / 18 |
| Class weight | 97.1% | 85.0% | 90.7% | 87.5% | 68 / 12 / 2 / 18 |
| SMOTE | 100.0% | 80.0% | 88.9% | 90.0% | 64 / 16 / 0 / 20 |

SMOTE had no false alarms in this held-out split, while missing 16 of 80 leaks. The baseline caught more leaks (70) with two false alarms. The recall target is selected on development data, not guaranteed on held-out cases.

## Why an earlier run flagged every test case

The old 80 TP / 0 FN / 20 FP / 0 TN result came from the retired **standard-range classifier on 12 pressure and 8 flow channels**, not the high-signal dataset. Its development threshold was selected to reach at least 90% recall. On the held-out split, all 20 normal cases also had predicted leak scores above that cutoff, so the classifier labeled every case as a leak. That gives 100% recall, 80% precision, and 0% specificity.

The old standard-range data also shifted demand between splits: training demand was 0.85–1.0, while test demand was 1.0–1.15. Its normal test cases therefore differed from the normal examples available during training. The sparse dataset and its reports have been removed from active use.

## Reproduce

```bash
python evaluate_net3.py --split test
python -m leakprobe.smote_benchmark
```

The benchmark is intentionally high-signal. Its results do not show how the detector performs on smaller or shorter leaks, unmodeled demand changes, sensor faults, or real utility feeds. Regenerated data needs new evaluations.
