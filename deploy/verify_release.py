"""Read-only file, credential and preserved-science integrity checks. No AI calls."""
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SECRET_PATTERNS = (
    re.compile(rb"\b(?:sk-|nvapi-)[A-Za-z0-9_-]{20,}"),
    re.compile(rb"Bearer\s+[A-Za-z0-9._-]{24,}", re.I),
    re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
)


def release_files(root):
    return {p.relative_to(root).as_posix(): p for p in root.rglob("*")
            if p.is_file() and not any(part in {".git", ".venv", "__pycache__"} for part in p.relative_to(root).parts)
            and p.name != "release-manifest.json"}


def verify(root=ROOT):
    manifest = json.loads((root / "release-manifest.json").read_text(encoding="utf-8"))
    files = release_files(root)
    if set(files) != set(manifest["files"]):
        raise ValueError("Unexpected or missing release files.")
    for name, path in files.items():
        if path.is_symlink() or path.suffix.lower() in {".db", ".sqlite", ".sqlite3", ".pem", ".key"} or path.name in {".env", "secrets.toml"}:
            raise ValueError("Private or unsafe file: " + name)
        payload = path.read_bytes()
        if any(pattern.search(payload) for pattern in SECRET_PATTERNS):
            raise ValueError("Possible credential; contents withheld: " + name)
        if {"sha256": hashlib.sha256(payload).hexdigest(), "bytes": len(payload)} != manifest["files"][name]:
            raise ValueError("Release hash mismatch: " + name)
    if len(json.loads((root / "data/net3_full_high_signal/cases.json").read_text())) != 500:
        raise ValueError("Canonical monitoring case count changed.")
    if len(list((root / "outputs/traces").glob("*_llm_trace.json"))) != 5:
        raise ValueError("Original saved trace count changed.")
    return {"verified_files": len(files), "source_commit": manifest["source_commit"],
            "bytes": sum(row["bytes"] for row in manifest["files"].values()),
            "monitoring_records": 500, "original_traces": 5, "credentials_detected": False}


if __name__ == "__main__":
    print(json.dumps(verify(), indent=2))
