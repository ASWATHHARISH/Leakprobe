# Recall led SMOTE Net3 benchmark

Experimental case-level classifier; the existing detector remains physics based.
Positive class: leak. Target development recall: 90%. Synthetic source data only.

Thresholds maximize precision among those meeting target recall on out-of-fold development predictions.

| Variant | Threshold | Dev target met | Test leak precision | Test leak recall | Test leak F1 | Test balanced accuracy | TP / FN / FP / TN |
|---|---:|:---:|---:|---:|---:|---:|---:|
| baseline | 0.712 | yes | 0.972 | 0.875 | 0.921 | 0.887 | 70 / 10 / 2 / 18 |
| class_weight | 0.729 | yes | 0.971 | 0.850 | 0.907 | 0.875 | 68 / 12 / 2 / 18 |
| smote | 0.672 | yes | 1.000 | 0.800 | 0.889 | 0.900 | 64 / 16 / 0 / 20 |

A target marked ‘no’ could not be met by the selected thresholding procedure on development data. Test results are held out once and should not be used to tune the model.

## 400-case development set (in-sample diagnostic)

Each model below was fitted on all 400 development cases and scored on those same cases. These figures are expected to be optimistic and are not a generalization estimate.

| Variant | Leak precision | Leak recall | Leak F1 | Balanced accuracy | TP / FN / FP / TN |
|---|---:|---:|---:|---:|---:|
| baseline | 1.000 | 1.000 | 1.000 | 1.000 | 320 / 0 / 0 / 80 |
| class_weight | 1.000 | 0.997 | 0.998 | 0.998 | 319 / 1 / 0 / 80 |
| smote | 1.000 | 1.000 | 1.000 | 1.000 | 320 / 0 / 0 / 80 |
