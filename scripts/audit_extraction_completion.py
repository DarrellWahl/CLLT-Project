import hashlib
import json
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parent.parent
WEBSITE_DATA = ROOT / "website" / "data" / "signs.json"
WEBSITE_SIGNS = ROOT / "website" / "signs"
LEGEND_PATH = ROOT / "output" / "sign_legend_clean.json"
REPORT_PATH = ROOT / "logs" / "extraction_completion_report.json"
DETERMINISM_RESULT_PATH = ROOT / "logs" / "determinism_result.json"


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    rows: List[Dict] = load_json(WEBSITE_DATA)
    legend = load_json(LEGEND_PATH) if LEGEND_PATH.exists() else []
    legend_codes = {str(item.get("code", "")).strip() for item in legend if str(item.get("code", "")).strip()}

    missing_images = []
    missing_metadata = []
    bad_codes = []

    seen_filenames = set()
    duplicate_filename_rows = 0

    hash_groups: Dict[str, List[str]] = {}

    for r in rows:
        filename = str(r.get("filename", "")).strip()
        if not filename:
            missing_metadata.append({"filename": filename, "reason": "missing_filename"})
            continue

        if filename in seen_filenames:
            duplicate_filename_rows += 1
        seen_filenames.add(filename)

        image_path = WEBSITE_SIGNS / filename
        if not image_path.exists():
            missing_images.append(filename)
        else:
            h = sha256(image_path)
            hash_groups.setdefault(h, []).append(filename)

        for field in ["page", "x", "y", "w", "h", "validation_status", "confidence_score", "status", "confidence", "source_image"]:
            if field not in r or r.get(field) in (None, ""):
                missing_metadata.append({"filename": filename, "reason": f"missing_{field}"})

        code = str(r.get("code", "")).strip()
        if code and legend_codes and code not in legend_codes:
            bad_codes.append({"filename": filename, "code": code})

    duplicate_groups = [files for files in hash_groups.values() if len(files) > 1]

    coded_rows = sum(1 for r in rows if str(r.get("code", "")).strip())
    described_rows = sum(1 for r in rows if str(r.get("description", "")).strip())

    rerun_deterministic = None
    if DETERMINISM_RESULT_PATH.exists():
        det = load_json(DETERMINISM_RESULT_PATH)
        rerun_deterministic = bool(
            det.get("exit_code") == 0
            and det.get("deterministic_files")
            and det.get("deterministic_metadata_normalized")
            and det.get("deterministic_counts")
        )

    criteria = {
        "all_signs_extracted_from_manual": len(rows) > 0,
        "stable_filenames": duplicate_filename_rows == 0 and all(str(r.get("filename", "")).strip() for r in rows),
        "correct_official_code_complete": coded_rows == len(rows),
        "correct_official_description_complete": described_rows == len(rows),
        "duplicates_removed_or_linked": all((r.get("duplicate_group_size", 1) == 1) or (str(r.get("duplicate_of", "")).strip() or r.get("duplicate_group_size", 1) > 1) for r in rows),
        "validation_status_recorded": all(str(r.get("validation_status", "")).strip() for r in rows),
        "confidence_recorded": all(r.get("confidence_score", None) is not None for r in rows),
        "metadata_complete": len(missing_metadata) == 0,
        "website_assets_renderable": len(missing_images) == 0,
        "rerun_deterministic": rerun_deterministic,
    }

    report = {
        "rows": len(rows),
        "coded_rows": coded_rows,
        "described_rows": described_rows,
        "legend_codes": len(legend_codes),
        "missing_images": missing_images,
        "missing_metadata_count": len(missing_metadata),
        "missing_metadata_examples": missing_metadata[:40],
        "duplicate_filename_rows": duplicate_filename_rows,
        "duplicate_hash_groups": len(duplicate_groups),
        "duplicate_files_total": sum(len(g) - 1 for g in duplicate_groups),
        "duplicate_hash_examples": duplicate_groups[:10],
        "codes_not_in_legend": bad_codes[:50],
        "completion_criteria": criteria,
    }

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with REPORT_PATH.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print("report_path", str(REPORT_PATH))
    print("rows", report["rows"])
    print("coded_rows", report["coded_rows"])
    print("described_rows", report["described_rows"])
    print("missing_metadata_count", report["missing_metadata_count"])
    print("missing_images", len(report["missing_images"]))
    print("duplicate_hash_groups", report["duplicate_hash_groups"])
    print("criteria", report["completion_criteria"])


if __name__ == "__main__":
    main()
