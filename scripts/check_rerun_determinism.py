import csv
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parent.parent
PYTHON = sys.executable
BASELINE_PATH = ROOT / "logs" / "determinism_baseline.json"
RESULT_PATH = ROOT / "logs" / "determinism_result.json"

TARGET_FILES = [
    ROOT / "metadata" / "page_1_signs.json",
    ROOT / "metadata" / "page_2_signs.json",
    ROOT / "metadata" / "page_3_signs.json",
    ROOT / "metadata" / "page_4_signs.json",
    ROOT / "logs" / "page_1_stats.json",
    ROOT / "logs" / "page_2_stats.json",
    ROOT / "logs" / "page_3_stats.json",
    ROOT / "logs" / "page_4_stats.json",
    ROOT / "logs" / "page_5_stats.json",
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalize_page_metadata(path: Path) -> List[Dict]:
    rows = json.load(path.open("r", encoding="utf-8"))
    normalized = []
    for r in rows:
        x = dict(r)
        x.pop("timestamp", None)
        normalized.append(x)
    normalized.sort(key=lambda r: (int(r.get("page", 0)), int(r.get("y", 0)), int(r.get("x", 0)), str(r.get("filename", ""))))
    return normalized


def collect_state() -> Dict:
    state = {
        "files": {},
        "metadata_normalized_hash": {},
        "counts": {},
    }

    for p in TARGET_FILES:
        if not p.exists():
            state["files"][str(p.relative_to(ROOT))] = None
            continue
        state["files"][str(p.relative_to(ROOT))] = sha256(p)

    for page in range(1, 5):
        path = ROOT / "metadata" / f"page_{page}_signs.json"
        if not path.exists():
            continue
        normalized = normalize_page_metadata(path)
        blob = json.dumps(normalized, sort_keys=True, ensure_ascii=False).encode("utf-8")
        state["metadata_normalized_hash"][f"page_{page}"] = hashlib.sha256(blob).hexdigest()
        state["counts"][f"page_{page}"] = len(normalized)

    consolidated = ROOT / "website" / "data" / "signs.json"
    if consolidated.exists():
        rows = json.load(consolidated.open("r", encoding="utf-8"))
        state["counts"]["website_rows"] = len(rows)

    return state


def write_json(path: Path, payload: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


def main() -> None:
    baseline = collect_state()
    write_json(BASELINE_PATH, baseline)

    cmd = [PYTHON, str(ROOT / "scripts" / "extract_pipeline.py")]
    env = dict(os.environ)
    env["CLLT_FIXED_TIMESTAMP"] = "1970-01-01T00:00:00Z"
    run = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, env=env)

    after = collect_state()

    result = {
        "command": " ".join(cmd),
        "exit_code": run.returncode,
        "stdout_tail": run.stdout.splitlines()[-60:],
        "stderr_tail": run.stderr.splitlines()[-60:],
        "baseline": baseline,
        "after": after,
        "deterministic_files": baseline["files"] == after["files"],
        "deterministic_metadata_normalized": baseline["metadata_normalized_hash"] == after["metadata_normalized_hash"],
        "deterministic_counts": baseline["counts"] == after["counts"],
    }

    write_json(RESULT_PATH, result)

    print("determinism_result", str(RESULT_PATH))
    print("exit_code", result["exit_code"])
    print("deterministic_files", result["deterministic_files"])
    print("deterministic_metadata_normalized", result["deterministic_metadata_normalized"])
    print("deterministic_counts", result["deterministic_counts"])


if __name__ == "__main__":
    main()
