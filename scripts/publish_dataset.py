import hashlib
import json
import shutil
from pathlib import Path
from typing import Dict, List, Tuple

ROOT = Path(__file__).resolve().parent.parent
METADATA_DIR = ROOT / "metadata"
ASSET_SIGNS_DIR = ROOT / "assets" / "png" / "signs"
WEBSITE_DATA = ROOT / "website" / "data" / "signs.json"
WEBSITE_SIGNS_DIR = ROOT / "website" / "signs"
MAPPINGS_PATH = ROOT / "output" / "sign_mappings_complete.json"
MAPPINGS_CLEAN_PATH = ROOT / "output" / "sign_mappings_clean.json"
MAPPINGS_ALL_PATH = ROOT / "output" / "sign_mappings_all.json"
LEGEND_PATH = ROOT / "output" / "sign_legend_clean.json"
CONSOLIDATED_METADATA = METADATA_DIR / "signs_consolidated.json"


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_page_metadata() -> List[Dict]:
    rows: List[Dict] = []
    for page in range(1, 5):
        page_path = METADATA_DIR / f"page_{page}_signs.json"
        page_rows = load_json(page_path)
        rows.extend(page_rows)
    rows.sort(key=lambda r: (int(r.get("page", 0)), int(r.get("y", 0)), int(r.get("x", 0)), str(r.get("filename", ""))))
    return rows


def _usable_code(code: str) -> bool:
    code = str(code or "").strip()
    return bool(code) and not code.upper().startswith("UNKNOWN")


def _merge_mapping(target: Dict[str, Dict], source_rows: List[Dict], source_name: str) -> None:
    for row in source_rows:
        filename = row.get("filename")
        if not filename:
            continue
        code = str(row.get("code", "") or "").strip()
        description = str(row.get("description", "") or "").strip()
        if not _usable_code(code) and not description:
            continue

        prev = target.get(filename, {})
        prev_code = str(prev.get("code", "") or "").strip()
        prev_desc = str(prev.get("description", "") or "").strip()

        # Prefer first usable code source by priority order, then fill missing description.
        next_code = prev_code if _usable_code(prev_code) else (code if _usable_code(code) else prev_code)
        next_desc = prev_desc or description

        merged = dict(prev)
        merged.update(row)
        merged["code"] = next_code
        merged["description"] = next_desc
        merged["label_source"] = source_name
        target[filename] = merged


def load_mapping_by_filename() -> Dict[str, Dict]:
    merged: Dict[str, Dict] = {}

    # Priority order: clean (verified) -> complete -> all (non-UNKNOWN only)
    if MAPPINGS_CLEAN_PATH.exists():
        _merge_mapping(merged, load_json(MAPPINGS_CLEAN_PATH), "sign_mappings_clean")
    if MAPPINGS_PATH.exists():
        _merge_mapping(merged, load_json(MAPPINGS_PATH), "sign_mappings_complete")
    if MAPPINGS_ALL_PATH.exists():
        _merge_mapping(merged, load_json(MAPPINGS_ALL_PATH), "sign_mappings_all")

    return merged


def load_legend_descriptions() -> Dict[str, str]:
    data = load_json(LEGEND_PATH)
    return {str(row.get("code", "")).strip(): str(row.get("description", "")).strip() for row in data}


def image_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_dataset() -> Tuple[List[Dict], Dict]:
    page_rows = load_page_metadata()
    mapping = load_mapping_by_filename()
    legend = load_legend_descriptions()

    records: List[Dict] = []
    hash_to_filenames: Dict[str, List[str]] = {}

    for row in page_rows:
        filename = str(row["filename"])
        image_path = ASSET_SIGNS_DIR / filename
        if not image_path.exists():
            raise FileNotFoundError(f"Missing source sign image: {image_path}")

        mapped = mapping.get(filename, {})
        code = str(mapped.get("code", row.get("code", "")) or "").strip()

        # For mapped official codes, prefer clean legend description as canonical wording.
        description = ""
        if code and code in legend:
            description = legend[code]
        else:
            description = str(mapped.get("description", "") or "").strip()

        status = str(mapped.get("status", row.get("status", "warning")) or "warning").strip()
        confidence = float(mapped.get("confidence", row.get("confidence", 0.0)) or 0.0)
        sha = image_sha256(image_path)
        hash_to_filenames.setdefault(sha, []).append(filename)

        record = {
            "filename": filename,
            "page": int(row.get("page", 0)),
            "code": code,
            "description": description,
            "status": status,
            "confidence": confidence,
            "validation_status": status,
            "confidence_score": confidence,
            "source_image": f"assets/png/pages/page_{int(row.get('page', 0))}.png",
            "x": int(row.get("x", 0)),
            "y": int(row.get("y", 0)),
            "w": int(row.get("w", 0)),
            "h": int(row.get("h", 0)),
            "padded_x": int(row.get("padded_x", row.get("x", 0))),
            "padded_y": int(row.get("padded_y", row.get("y", 0))),
            "padded_w": int(row.get("padded_w", row.get("w", 0))),
            "padded_h": int(row.get("padded_h", row.get("h", 0))),
            "warnings": row.get("warnings", []),
            "retries": int(row.get("retries", 0)),
            "timestamp": row.get("timestamp", ""),
            "sha256": sha,
            "duplicate_group_size": 0,
            "duplicate_of": "",
            "label_source": mapped.get("label_source", ""),
        }
        records.append(record)

    # Fill duplicate linkage metadata deterministically.
    canonical_for_hash: Dict[str, str] = {}
    for sha, files in hash_to_filenames.items():
        canonical_for_hash[sha] = sorted(files)[0]

    for rec in records:
        files = hash_to_filenames[rec["sha256"]]
        rec["duplicate_group_size"] = len(files)
        canonical = canonical_for_hash[rec["sha256"]]
        rec["duplicate_of"] = "" if rec["filename"] == canonical else canonical

    records.sort(key=lambda r: (r["page"], r["y"], r["x"], r["filename"]))

    summary = {
        "rows": len(records),
        "coded_rows": sum(1 for r in records if r["code"]),
        "described_rows": sum(1 for r in records if r["description"]),
        "needs_label_rows": sum(1 for r in records if not r["code"] or not r["description"]),
        "duplicate_rows": sum(1 for r in records if r["duplicate_of"]),
        "duplicate_groups": len({r["sha256"] for r in records if r["duplicate_group_size"] > 1}),
    }
    return records, summary


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


def sync_website_signs(records: List[Dict]) -> Dict[str, int]:
    WEBSITE_SIGNS_DIR.mkdir(parents=True, exist_ok=True)
    keep = {r["filename"] for r in records}

    removed = 0
    for p in list(WEBSITE_SIGNS_DIR.glob("*.png")):
        if p.name not in keep:
            p.unlink()
            removed += 1

    copied = 0
    for filename in sorted(keep):
        src = ASSET_SIGNS_DIR / filename
        dst = WEBSITE_SIGNS_DIR / filename
        if not dst.exists():
            shutil.copy2(src, dst)
            copied += 1

    return {"copied": copied, "removed": removed, "final": len(list(WEBSITE_SIGNS_DIR.glob('*.png')))}


def main() -> None:
    records, summary = build_dataset()
    write_json(WEBSITE_DATA, records)
    write_json(CONSOLIDATED_METADATA, records)
    sync_stats = sync_website_signs(records)

    print("publish_summary", summary)
    print("website_signs_sync", sync_stats)
    print("dataset_paths", {"website": str(WEBSITE_DATA), "metadata": str(CONSOLIDATED_METADATA)})


if __name__ == "__main__":
    main()
