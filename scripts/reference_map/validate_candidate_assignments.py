import json
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[2]


def _load(path: Path) -> Any:
    with path.open('r', encoding='utf-8') as f:
        return json.load(f)


def validate_candidates(root: Path) -> List[str]:
    errors: List[str] = []
    candidate_path = root / 'metadata' / 'reference_map' / 'candidate_assignments_sample.json'
    positions_path = root / 'metadata' / 'reference_map' / 'reference_positions.json'

    doc = _load(candidate_path)
    pos_doc = _load(positions_path)

    required_doc = ['contract_version', 'matcher_version', 'run_type', 'edition_id', 'run_at', 'sample_limit', 'top_k', 'inputs', 'summary', 'candidates']
    for k in required_doc:
        if k not in doc:
            errors.append(f'candidate_doc: missing {k}')

    approved_positions = {
        p['reference_position_id']
        for p in pos_doc.get('positions', [])
        if p.get('approval_state') == 'approved' and p.get('reference_status') == 'verified'
    }

    seen_ids = set()
    for idx, c in enumerate(doc.get('candidates', [])):
        for k in ['candidate_assignment_id', 'reference_position_id', 'extracted_sign_id', 'match_score', 'geometry_agreement', 'ocr_agreement', 'provenance', 'validation_status', 'review_status', 'confidence', 'audit']:
            if k not in c:
                errors.append(f'candidate[{idx}]: missing {k}')

        cid = c.get('candidate_assignment_id')
        if cid in seen_ids:
            errors.append(f'candidate[{idx}]: duplicate candidate_assignment_id {cid}')
        seen_ids.add(cid)

        rp = c.get('reference_position_id')
        if rp not in approved_positions:
            errors.append(f'candidate[{idx}]: reference_position_id not approved {rp}')

        conf = c.get('confidence')
        score = c.get('match_score')
        if not isinstance(conf, (int, float)) or conf < 0 or conf > 1:
            errors.append(f'candidate[{idx}]: invalid confidence')
        if not isinstance(score, (int, float)) or score < 0 or score > 1:
            errors.append(f'candidate[{idx}]: invalid match_score')

        ga = c.get('geometry_agreement', {})
        for gk in ['iou', 'center_distance', 'center_score', 'area_ratio', 'geometry_score']:
            if gk not in ga:
                errors.append(f'candidate[{idx}]: missing geometry_agreement.{gk}')

        iou = ga.get('iou')
        center_score = ga.get('center_score')
        area_ratio = ga.get('area_ratio')
        if not isinstance(iou, (int, float)) or iou < 0 or iou > 1:
            errors.append(f'candidate[{idx}]: invalid iou')
        if not isinstance(center_score, (int, float)) or center_score < 0 or center_score > 1:
            errors.append(f'candidate[{idx}]: invalid center_score')
        if not isinstance(area_ratio, (int, float)) or area_ratio < 0 or area_ratio > 1:
            errors.append(f'candidate[{idx}]: invalid area_ratio')

        oa = c.get('ocr_agreement', {})
        if oa.get('agreement') not in ['consistent', 'inconsistent', 'unavailable']:
            errors.append(f'candidate[{idx}]: invalid ocr_agreement.agreement')

        prov = c.get('provenance', {})
        for pk in ['authoritative_source', 'manual_edition', 'source_page', 'assignment_method', 'pipeline_version', 'timestamp']:
            if pk not in prov:
                errors.append(f'candidate[{idx}]: missing provenance.{pk}')

        if c.get('validation_status') != 'candidate_valid':
            errors.append(f'candidate[{idx}]: unexpected validation_status')
        if c.get('review_status') != 'unreviewed':
            errors.append(f'candidate[{idx}]: unexpected review_status')

    # deterministic ordering check
    candidates = doc.get('candidates', [])
    expected = sorted(candidates, key=lambda x: (x['extracted_sign_id'], x['rank'], x['reference_position_id']))
    if candidates != expected:
        errors.append('candidate_doc: candidates are not deterministically sorted')

    return errors


def main() -> None:
    errors = validate_candidates(ROOT)
    if errors:
        print('candidate_assignments_valid', False)
        for e in errors:
            print('error', e)
        raise SystemExit(1)
    print('candidate_assignments_valid', True)


if __name__ == '__main__':
    main()
