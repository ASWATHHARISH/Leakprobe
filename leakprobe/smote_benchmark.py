"""Experimental SMOTE benchmark, isolated from the physics-based Net3 detector.

Run with ``python -m leakprobe.smote_benchmark`` after installing requirements.
Features and reports are written to ``data/net3_full_high_signal_benchmark``.
"""
import json
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from .coverage import validate_full_channel_coverage
from .paths import DATA, NET3_DATA

SOURCE = NET3_DATA
OUT = DATA / "net3_full_high_signal_benchmark"
SEED = 2026
POSITIVE = "single_leak"
DEFAULT_TARGET_RECALL = 0.90


def extract_case_features(case_row, source=SOURCE):
    """Create one fixed-width feature row from the observed sensor time series."""
    observations = pd.read_csv(source / case_row["observations_file"])
    features = {}
    for column in observations.columns:
        if column == "timestamp_utc":
            continue
        values = pd.to_numeric(observations[column], errors="coerce")
        valid = values.dropna()
        features[f"{column}__missing_fraction"] = float(values.isna().mean())
        for name, value in (("mean", valid.mean()), ("std", valid.std(ddof=0)),
                             ("min", valid.min()), ("max", valid.max()),
                             ("first", valid.iloc[0] if len(valid) else np.nan),
                             ("last", valid.iloc[-1] if len(valid) else np.nan),
                             ("delta", valid.iloc[-1] - valid.iloc[0] if len(valid) else np.nan)):
            features[f"{column}__{name}"] = float(value) if pd.notna(value) else np.nan
    return features


def load_dataset(source=SOURCE):
    metadata = json.loads((source / "metadata.json").read_text(encoding="utf-8"))
    cases = json.loads((source / "cases.json").read_text(encoding="utf-8"))
    labels = json.loads((source / "truth_labels.json").read_text(encoding="utf-8"))
    rows = []
    for case in cases:
        observations = pd.read_csv(source / case["observations_file"])
        validate_full_channel_coverage(metadata, observations.columns,
                                       f"{case['case_id']} observations")
        row = extract_case_features(case, source)
        row.update(case_id=case["case_id"], split=case["split"],
                   label=labels[case["case_id"]]["incident"])
        rows.append(row)
    frame = pd.DataFrame(rows)
    if set(frame["split"]) != {"train", "test"}:
        raise ValueError("Expected existing train and test splits in cases.json.")
    return frame


def metrics(y_true, y_pred):
    from sklearn.metrics import (accuracy_score, balanced_accuracy_score,
                                 confusion_matrix, f1_score, precision_score,
                                 recall_score)

    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    return {
        "confusion_matrix": {"tp_leak": int(tp), "fn_leak": int(fn),
                             "fp_false_alarm": int(fp), "tn_normal": int(tn)},
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "balanced_accuracy": float(balanced_accuracy_score(y_true, y_pred)),
        "leak_precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "leak_recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "leak_f1": float(f1_score(y_true, y_pred, zero_division=0)),
    }


def _recall_led_threshold(y_true, probabilities, target_recall):
    """Meet target leak recall on OOF development data, maximizing precision."""
    y_true = np.asarray(y_true, dtype=int)
    probabilities = np.asarray(probabilities, dtype=float)
    positives = int(y_true.sum())
    if not positives:
        raise ValueError("Threshold selection requires positive leak examples.")
    thresholds = np.unique(np.r_[0.0, probabilities, 1.0])
    eligible = []
    for threshold in thresholds:
        predicted = probabilities >= threshold
        tp = int(np.sum(predicted & (y_true == 1)))
        fp = int(np.sum(predicted & (y_true == 0)))
        recall = tp / positives
        if recall >= target_recall:
            precision = tp / (tp + fp) if tp + fp else 0.0
            eligible.append((precision, float(threshold), float(recall)))
    if not eligible:
        # Predict every case as a leak to attain the highest possible recall.
        return 0.0, False
    # Highest precision; break ties by choosing the higher threshold.
    precision, threshold, _ = max(eligible, key=lambda item: (item[0], item[1]))
    return threshold, True


def run(source=SOURCE, output=OUT, target_recall=DEFAULT_TARGET_RECALL):
    if not 0 < target_recall <= 1:
        raise ValueError("target_recall must be greater than 0 and at most 1.")
    try:
        from imblearn.over_sampling import SMOTE
        from imblearn.pipeline import Pipeline
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.impute import SimpleImputer
        from sklearn.model_selection import StratifiedKFold, cross_val_predict
        from sklearn.preprocessing import StandardScaler
    except ImportError as exc:
        raise SystemExit(
            "SMOTE benchmark dependencies are missing. Install with: "
            "python -m pip install -r requirements.txt"
        ) from exc

    output.mkdir(parents=True, exist_ok=True)
    frame = load_dataset(source)
    frame.to_csv(output / "case_features.csv", index=False)
    feature_columns = [name for name in frame.columns
                       if name not in {"case_id", "split", "label"}]
    train = frame[frame["split"] == "train"].reset_index(drop=True)
    test = frame[frame["split"] == "test"].reset_index(drop=True)
    x_train = train[feature_columns]
    y_train = (train["label"] == POSITIVE).astype(int)
    x_test = test[feature_columns]
    y_test = (test["label"] == POSITIVE).astype(int)
    counts = y_train.value_counts().to_dict()
    k_neighbors = min(3, int(counts.get(0, 0)) - 1)
    if k_neighbors < 1:
        raise ValueError("SMOTE needs at least two normal training cases.")

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED)
    variants = {
        "baseline": ("passthrough", "balanced"),
        "class_weight": ("passthrough", "balanced_subsample"),
        "smote": (SMOTE(random_state=SEED, k_neighbors=k_neighbors), "balanced_subsample"),
    }
    reports = {
        "benchmark": "experimental synthetic Net3 case-level leak classifier",
        "positive_class": POSITIVE,
        "source_data": str(source.relative_to(DATA) if source.is_relative_to(DATA) else source),
        "pressure_channel_count": 92,
        "flow_channel_count": 117,
        "training_counts": {"normal": int(counts.get(0, 0)), "leak": int(counts.get(1, 0))},
        "test_counts": {"normal": int((y_test == 0).sum()), "leak": int((y_test == 1).sum())},
        "smote_k_neighbors": k_neighbors,
        "target_leak_recall": target_recall,
        "feature_count": len(feature_columns),
        "variants": {},
        "notes": [
            "SMOTE is applied only within each training fold through imbalanced-learn Pipeline.",
            "Thresholds target the requested leak recall on out-of-fold development predictions, never test labels.",
            "All input cases are synthetic and this classifier does not replace the physics matcher.",
        ],
    }
    for name, (sampler, class_weight) in variants.items():
        pipeline = Pipeline([
            ("impute", SimpleImputer(strategy="median", add_indicator=True)),
            ("scale", StandardScaler()),
            ("sampler", sampler),
            ("classifier", RandomForestClassifier(
                n_estimators=300, min_samples_leaf=2, class_weight=class_weight,
                random_state=SEED, n_jobs=-1)),
        ])
        oof_probability = cross_val_predict(
            pipeline, x_train, y_train, cv=cv, method="predict_proba", n_jobs=1
        )[:, 1]
        threshold, target_met = _recall_led_threshold(
            y_train.to_numpy(), oof_probability, target_recall
        )
        pipeline.fit(x_train, y_train)
        test_probability = pipeline.predict_proba(x_test)[:, 1]
        prediction = (test_probability >= threshold).astype(int)
        reports["variants"][name] = {
            "threshold": threshold,
            "development_target_recall_met": target_met,
            "development_oof": metrics(y_train, oof_probability >= threshold),
            "held_out_test": metrics(y_test, prediction),
        }
        pd.DataFrame({"case_id": test["case_id"], "actual": y_test,
                      "probability_leak": test_probability, "predicted_leak": prediction
                      }).to_csv(output / f"{name}_test_predictions.csv", index=False)

    # Requested in-sample diagnostic on the development cases. Keep its
    # outputs distinct from the untouched 100-case held-out test results.
    training_reports = {}
    for name, (sampler, class_weight) in variants.items():
        pipeline = Pipeline([
            ("impute", SimpleImputer(strategy="median", add_indicator=True)),
            ("scale", StandardScaler()),
            ("sampler", sampler),
            ("classifier", RandomForestClassifier(
                n_estimators=300, min_samples_leaf=2, class_weight=class_weight,
                random_state=SEED, n_jobs=-1)),
        ])
        pipeline.fit(x_train, y_train)
        train_probability = pipeline.predict_proba(x_train)[:, 1]
        train_prediction = (train_probability >= reports["variants"][name]["threshold"]).astype(int)
        training_reports[name] = {
            "threshold_from_development_oof": reports["variants"][name]["threshold"],
            "in_sample": metrics(y_train, train_prediction),
        }
        pd.DataFrame({"case_id": train["case_id"], "actual": y_train,
                      "probability_leak": train_probability,
                      "predicted_leak": train_prediction
                      }).to_csv(output / f"{name}_train_in_sample_predictions.csv", index=False)
    reports["development_in_sample"] = training_reports

    (output / "report.json").write_text(json.dumps(reports, indent=2), encoding="utf-8")
    lines = ["# Recall led SMOTE Net3 benchmark", "",
             "Experimental case-level classifier; the existing detector remains physics based.",
             f"Positive class: leak. Target development recall: {target_recall:.0%}. Synthetic source data only.", "",
             "All three variants use Random Forests. `baseline` uses global balanced class weights; `class_weight` recalculates balanced weights per tree; `smote` adds synthetic examples of the minority class inside training folds and also uses per-tree weights.",
             f"The development set has {int((y_train == 1).sum())} leak cases and {int((y_train == 0).sum())} normal cases. With SMOTE's default balancing, the minority class here is normal, so SMOTE creates normal-like training examples; it does not add leak cases or modify held-out sensor data.", "",
             "Thresholds maximize precision among those meeting target recall on out-of-fold development predictions.", "",
             "| Variant | Threshold | Dev target met | Test leak precision | Test leak recall | Test leak F1 | Test balanced accuracy | TP / FN / FP / TN |",
             "|---|---:|:---:|---:|---:|---:|---:|---:|"]
    for name, result in reports["variants"].items():
        score = result["held_out_test"]
        matrix = score["confusion_matrix"]
        lines.append(
            f"| {name} | {result['threshold']:.3f} | "
            f"{'yes' if result['development_target_recall_met'] else 'no'} | {score['leak_precision']:.3f} "
            f"| {score['leak_recall']:.3f} | {score['leak_f1']:.3f} "
            f"| {score['balanced_accuracy']:.3f} | {matrix['tp_leak']} / "
            f"{matrix['fn_leak']} / {matrix['fp_false_alarm']} / {matrix['tn_normal']} |"
        )
    lines += ["", "A target marked ‘no’ could not be met by the selected thresholding procedure on development data. "
              "Test results are held out once and should not be used to tune the model.", ""]
    lines += [f"## {len(train)}-case development set (in-sample diagnostic)", "",
              f"Each model below was fitted on all {len(train)} development cases and scored on those same cases. "
              "These figures are expected to be optimistic and are not a generalization estimate.", "",
              "| Variant | Leak precision | Leak recall | Leak F1 | Balanced accuracy | TP / FN / FP / TN |",
              "|---|---:|---:|---:|---:|---:|"]
    for name, result in training_reports.items():
        score = result["in_sample"]
        matrix = score["confusion_matrix"]
        lines.append(
            f"| {name} | {score['leak_precision']:.3f} | {score['leak_recall']:.3f} "
            f"| {score['leak_f1']:.3f} | {score['balanced_accuracy']:.3f} "
            f"| {matrix['tp_leak']} / {matrix['fn_leak']} / "
            f"{matrix['fp_false_alarm']} / {matrix['tn_normal']} |"
        )
    lines.append("")
    (output / "report.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"Saved features and benchmark report to {output}")
    for name, result in reports["variants"].items():
        score = result["held_out_test"]
        print(f"{name}: leak precision={score['leak_precision']:.3f}, "
              f"recall={score['leak_recall']:.3f}, F1={score['leak_f1']:.3f}")
    print(f"{len(train)}-case in-sample diagnostic (optimistic; not held-out performance):")
    for name, result in training_reports.items():
        score = result["in_sample"]
        print(f"{name}: leak precision={score['leak_precision']:.3f}, "
              f"recall={score['leak_recall']:.3f}, F1={score['leak_f1']:.3f}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-recall", type=float, default=DEFAULT_TARGET_RECALL,
                        help="Target leak recall for threshold selection (default: 0.90).")
    parser.add_argument("--source", type=Path, default=SOURCE,
                        help="Source Net3 dataset directory.")
    parser.add_argument("--output", type=Path, default=OUT,
                        help="Separate output directory for this benchmark.")
    args = parser.parse_args()
    run(source=args.source, output=args.output, target_recall=args.target_recall)
