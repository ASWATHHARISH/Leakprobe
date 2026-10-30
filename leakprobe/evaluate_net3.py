"""Evaluate the full-channel Net3 scenario rankings against stored outcomes."""
import argparse
import json
from pathlib import Path

from .coverage import validate_full_channel_coverage
from .net3_tools import DATA, Net3Investigation


def classification_metrics(actual, predicted):
    """Summarize binary leak/normal predictions; leak is the positive class."""
    if len(actual) != len(predicted):
        raise ValueError("actual and predicted must contain the same number of cases.")
    allowed = {"leak", "normal"}
    if any(value not in allowed for value in (*actual, *predicted)):
        raise ValueError("Class labels must be 'leak' or 'normal'.")
    tp = sum(a == "leak" and p == "leak" for a, p in zip(actual, predicted))
    fn = sum(a == "leak" and p == "normal" for a, p in zip(actual, predicted))
    fp = sum(a == "normal" and p == "leak" for a, p in zip(actual, predicted))
    tn = sum(a == "normal" and p == "normal" for a, p in zip(actual, predicted))
    total = tp + fn + fp + tn
    recall = tp / (tp + fn) if tp + fn else None
    precision = tp / (tp + fp) if tp + fp else None
    specificity = tn / (tn + fp) if tn + fp else None
    balanced = (recall + specificity) / 2 if recall is not None and specificity is not None else None
    f1 = (2 * precision * recall / (precision + recall)
          if precision is not None and recall is not None and precision + recall else
          0.0 if precision is not None and recall == 0 else None)
    return {
        "confusion_matrix": {"tp": tp, "fn": fn, "fp": fp, "tn": tn},
        "total": total,
        "accuracy": (tp + tn) / total if total else None,
        "precision": precision,
        "recall": recall,
        "specificity": specificity,
        "false_alarm_rate": fp / (fp + tn) if fp + tn else None,
        "balanced_accuracy": balanced,
        "f1": f1,
    }


def select_cases(cases, split):
    if split not in {"train", "test", "all"}:
        raise ValueError("split must be 'train', 'test', or 'all'.")
    return [row["case_id"] for row in cases if split == "all" or row["split"] == split]


def _binary_prediction(decision):
    """Treat an abstention as no leak alarm in binary alarm metrics."""
    return "normal" if decision["prediction"] == "uncertain" else decision["prediction"]


def _print_classification_report(stage, actual, predicted):
    metrics = classification_metrics(actual, predicted)
    matrix = metrics["confusion_matrix"]
    actual_leaks = matrix["tp"] + matrix["fn"]
    actual_normals = matrix["tn"] + matrix["fp"]
    print(f"\n{stage} leak detection (positive = leak):")
    print("                 Predicted leak  Predicted normal")
    print(f"Actual leak      {matrix['tp']:>13}  {matrix['fn']:>16}  (n={actual_leaks})")
    print(f"Actual normal    {matrix['fp']:>13}  {matrix['tn']:>16}  (n={actual_normals})")
    print(f"  Accuracy: {metrics['accuracy']:.1%} ({matrix['tp'] + matrix['tn']}/{metrics['total']})")
    print(f"  Precision: {metrics['precision']:.1%}" if metrics["precision"] is not None else "  Precision: undefined")
    print(f"  Recall: {metrics['recall']:.1%}" if metrics["recall"] is not None else "  Recall: undefined")
    print(f"  Specificity: {metrics['specificity']:.1%}" if metrics["specificity"] is not None else "  Specificity: undefined")
    print(f"  False-alarm rate: {metrics['false_alarm_rate']:.1%}" if metrics["false_alarm_rate"] is not None else "  False-alarm rate: undefined")
    print(f"  Balanced accuracy: {metrics['balanced_accuracy']:.1%}" if metrics["balanced_accuracy"] is not None else "  Balanced accuracy: undefined")
    print(f"  F1: {metrics['f1']:.1%}" if metrics["f1"] is not None else "  F1: undefined")
    return metrics


def evaluate(split="test", data_dir=DATA):
    data_dir = Path(data_dir)
    metadata = json.loads((data_dir / "metadata.json").read_text(encoding="utf-8"))
    validate_full_channel_coverage(
        metadata,
        [*(f"pressure_{node}_m" for node in metadata.get("monitor_pressure_nodes", [])),
         *(f"flow_{pipe}_lps" for pipe in metadata.get("flow_sensors", []))],
        "Net3 metadata",
    )
    cases = json.loads((data_dir / "cases.json").read_text(encoding="utf-8"))
    labels = json.loads((data_dir / "truth_labels.json").read_text(encoding="utf-8"))
    selected = select_cases(cases, split)
    if not selected:
        raise ValueError(f"No cases in the {split} split. Generate the full Net3 dataset first.")

    actual, predicted = [], []
    rejected = 0
    leak_total = exact_pipe = detected_leaks = correctly_located_detected = 0
    for index, case_id in enumerate(selected, start=1):
        truth = labels[case_id]
        session = Net3Investigation(case_id, data_dir=data_dir)
        result = session.compare_hypotheses()
        best = result["ranking"][0]
        decision = result["decision"]
        is_normal = truth["incident"] == "normal"
        actual.append("normal" if is_normal else "leak")
        predicted.append(_binary_prediction(decision))
        rejected += int(decision["rejected"])
        if not is_normal:
            leak_total += 1
            exact_pipe += int(decision["prediction"] == "leak"
                              and best["leak_pipe"] == truth["leak_pipe"])
            if decision["prediction"] == "leak":
                detected_leaks += 1
                correctly_located_detected += int(best["leak_pipe"] == truth["leak_pipe"])
        if index % 25 == 0 or index == len(selected):
            print(f"Progress: {index}/{len(selected)} cases evaluated", flush=True)

    print(f"Net3 {split} split: {len(selected)} cases ({leak_total} leaks, {len(selected)-leak_total} normal)")
    _print_classification_report("Full 92-pressure / 117-flow sensor feed", actual, predicted)
    if rejected:
        print(f"  Rejected as uncertain: {rejected}/{len(selected)} cases; counted as no leak alarm above.")
    threshold = metadata.get("rejection_threshold")
    if threshold is not None:
        print(f"Rejection threshold: best leak fit score > {threshold:.4f} becomes uncertain.")
    if leak_total:
        print("\nPipe location, conditional on the case being an actual leak:")
        if detected_leaks:
            print(f"  Exact pipe among detected leak alarms: {correctly_located_detected}/{detected_leaks}")
        else:
            print("  No leak alarms were raised")
        print(f"  Exact pipe across all actual leak cases: {exact_pipe}/{leak_total} ({exact_pipe/leak_total:.1%})")
    print("These are results on generated benchmark cases, not field performance.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split", choices=("train", "test", "all"), default="test",
                        help="Evaluate the held-out split, development split, or all cases.")
    parser.add_argument("--data-dir", type=Path, default=DATA,
                        help="Full Net3 data directory. Datasets with fewer channels are rejected.")
    args = parser.parse_args()
    evaluate(args.split, args.data_dir)


if __name__ == "__main__":
    main()
