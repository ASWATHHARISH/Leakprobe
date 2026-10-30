# Recall led SMOTE Net3 benchmark

Experimental case-level classifier; the existing detector remains physics based.
Positive class: leak. Target development recall: 90%. Synthetic source data only.

All three variants use Random Forests. `baseline` uses global balanced class weights; `class_weight` recalculates balanced weights per tree; `smote` adds synthetic examples of the minority class inside training folds and also uses per-tree weights.
The development set has 640 leak cases and 160 normal cases. With SMOTE's default balancing, the minority class here is normal, so SMOTE creates normal-like training examples; it does not add leak cases or modify held-out sensor data.

Thresholds maximize precision among those meeting target recall on out-of-fold development predictions.

| Variant | Threshold | Dev target met | Test leak precision | Test leak recall | Test leak F1 | Test balanced accuracy | TP / FN / FP / TN |
|---|---:|:---:|---:|---:|---:|---:|---:|
| baseline | 0.761 | yes | 1.000 | 0.781 | 0.877 | 0.891 | 125 / 35 / 0 / 40 |
| class_weight | 0.760 | yes | 1.000 | 0.781 | 0.877 | 0.891 | 125 / 35 / 0 / 40 |
| smote | 0.694 | yes | 1.000 | 0.787 | 0.881 | 0.894 | 126 / 34 / 0 / 40 |

A target marked ‘no’ could not be met by the selected thresholding procedure on development data. Test results are held out once and should not be used to tune the model.

## 800-case development set (in-sample diagnostic)

Each model below was fitted on all 800 development cases and scored on those same cases. These figures are expected to be optimistic and are not a generalization estimate.

| Variant | Leak precision | Leak recall | Leak F1 | Balanced accuracy | TP / FN / FP / TN |
|---|---:|---:|---:|---:|---:|
| baseline | 1.000 | 0.986 | 0.993 | 0.993 | 631 / 9 / 0 / 160 |
| class_weight | 1.000 | 0.986 | 0.993 | 0.993 | 631 / 9 / 0 / 160 |
| smote | 1.000 | 0.995 | 0.998 | 0.998 | 637 / 3 / 0 / 160 |
