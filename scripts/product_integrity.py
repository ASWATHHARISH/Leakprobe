"""Capture/verify protected inputs without regenerating data or evaluations."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def hashes():
    paths = list((ROOT / "data").rglob("*"))
    paths += list((ROOT / "outputs").rglob("*"))
    paths += [ROOT / "leakprobe" / name for name in
              ("net3_tools.py", "coverage.py", "evaluate_net3.py", "smote_benchmark.py")]
    result = {}
    for path in sorted(paths):
        if not path.is_file() or any(p in ("operations", "product_verification") for p in path.parts):
            continue
        with path.open("rb") as stream:
            result[path.relative_to(ROOT).as_posix()] = hashlib.file_digest(stream, "sha256").hexdigest()
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("capture", "verify"))
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()
    current = hashes()
    if args.action == "capture":
        args.manifest.parent.mkdir(parents=True, exist_ok=True)
        with args.manifest.open("x", encoding="utf-8") as stream:
            json.dump(current, stream, indent=2)
        print(f"Captured {len(current)} protected file hashes.")
    else:
        original = json.loads(args.manifest.read_text(encoding="utf-8"))
        changed = [p for p, digest in original.items() if current.get(p) != digest]
        if changed:
            raise SystemExit("Protected files changed: " + ", ".join(changed))
        print(f"PASS: {len(original)} original datasets, reference banks, detector, benchmark and saved artifact hashes unchanged.")


if __name__ == "__main__":
    main()
