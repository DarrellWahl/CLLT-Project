import hashlib
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Tuple

from scripts.reference_map.common import read_json, utc_now_iso, write_json


def _run_timestamp() -> str:
    fixed = os.environ.get('CLLT_FIXED_TIMESTAMP', '').strip()
    if fixed:
        return fixed
    return utc_now_iso()


def _load_config(root: Path) -> Dict[str, Any]:
    cfg_path = root / 'assets' / 'config' / 'reference_map_config.json'
    with cfg_path.open('r', encoding='utf-8') as f:
        return json.load(f)


def _load_pages(root: Path) -> Dict[int, Dict[str, Any]]:
    pages = read_json(root / 'metadata' / 'reference_map' / 'pages.json', [])
    return {int(p['page_number']): p for p in pages}


def _load_approved_reference_positions(root: Path, approved_states: List[str]) -> List[Dict[str, Any]]:
    doc = read_json(root / 'metadata' / 'reference_map' / 'reference_positions.json', {})
    positions = doc.get('positions', [])
    approved = [
        p for p in positions
        if p.get('approval_state') in approved_states and p.get('reference_status') == 'verified'
    ]
    approved.sort(key=lambda x: (x['page_number'], x['grid_row'], x['grid_col'], x['reference_position_id']))
    return approved


def _to_norm_bbox(row: Dict[str, Any], page_meta: Dict[str, Any]) -> Tuple[float, float, float, float]:
    w = float(page_meta['image_width'])
    h = float(page_meta['image_height'])
    x = float(row['x']) / w
    y = float(row['y']) / h
    bw = float(row['w']) / w
    bh = float(row['h']) / h
    return (round(x, 6), round(y, 6), round(bw, 6), round(bh, 6))


def _build_extracted_instances(root: Path, files: List[str], pages: Dict[int, Dict[str, Any]], sample_limit: int) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for rel in files:
        rows = read_json(root / rel, [])
        for r in rows:
            page_number = int(r['page'])
            page_meta = pages.get(page_number)
            if not page_meta:
                continue
            nx, ny, nw, nh = _to_norm_bbox(r, page_meta)
            filename = r['filename']
            extracted_sign_id = f"ES-{filename.replace('.png', '')}"
            items.append({
                'extracted_sign_id': extracted_sign_id,
                'filename': filename,
                'page_number': page_number,
                'norm_x': nx,
                'norm_y': ny,
                'norm_w': nw,
                'norm_h': nh,
                'raw_x': int(r['x']),
                'raw_y': int(r['y']),
                'raw_w': int(r['w']),
                'raw_h': int(r['h']),
                'extraction_status': r.get('status', ''),
                'extraction_confidence': float(r.get('confidence', 0.0)) / 100.0,
                'ocr_code': str(r.get('code', '')).strip(),
            })

    items.sort(key=lambda x: (x['page_number'], x['raw_y'], x['raw_x'], x['filename']))
    return items[:sample_limit]


def _iou(a: Tuple[float, float, float, float], b: Tuple[float, float, float, float]) -> float:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    ax2, ay2 = ax + aw, ay + ah
    bx2, by2 = bx + bw, by + bh
    ix1, iy1 = max(ax, bx), max(ay, by)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    if ix2 <= ix1 or iy2 <= iy1:
        return 0.0
    inter = (ix2 - ix1) * (iy2 - iy1)
    union = aw * ah + bw * bh - inter
    if union <= 0:
        return 0.0
    return inter / union


def _center_distance(a: Tuple[float, float, float, float], b: Tuple[float, float, float, float]) -> float:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    acx, acy = ax + aw / 2.0, ay + ah / 2.0
    bcx, bcy = bx + bw / 2.0, by + bh / 2.0
    dx, dy = acx - bcx, acy - bcy
    return (dx * dx + dy * dy) ** 0.5


def _area_ratio(a: Tuple[float, float, float, float], b: Tuple[float, float, float, float]) -> float:
    aa = a[2] * a[3]
    ba = b[2] * b[3]
    if aa <= 0 or ba <= 0:
        return 0.0
    return min(aa, ba) / max(aa, ba)


def _score_geometry(extracted: Tuple[float, float, float, float], reference: Tuple[float, float, float, float], weights: Dict[str, float]) -> Dict[str, float]:
    iou = _iou(extracted, reference)
    dist = _center_distance(extracted, reference)
    dist_score = max(0.0, 1.0 - min(1.0, dist / 1.4142135623730951))
    area = _area_ratio(extracted, reference)
    score = (iou * weights['iou']) + (dist_score * weights['center']) + (area * weights['area'])
    return {
        'iou': round(iou, 6),
        'center_distance': round(dist, 6),
        'center_score': round(dist_score, 6),
        'area_ratio': round(area, 6),
        'geometry_score': round(score, 6),
    }


def _ocr_agreement(extracted_code: str, official_code: str) -> Dict[str, Any]:
    if not extracted_code:
        return {'available': False, 'agreement': 'unavailable', 'score': None}
    if extracted_code == official_code:
        return {'available': True, 'agreement': 'consistent', 'score': 1.0}
    return {'available': True, 'agreement': 'inconsistent', 'score': 0.0}


def _candidate_id(reference_position_id: str, extracted_sign_id: str) -> str:
    raw = f'{reference_position_id}|{extracted_sign_id}'.encode('utf-8')
    return 'CA-' + hashlib.sha256(raw).hexdigest()[:16]


def generate_candidate_assignments(root: Path, sample_limit: int = None) -> Dict[str, Any]:
    config = _load_config(root)
    matcher_cfg = config['matcher']
    if sample_limit is None:
        sample_limit = int(matcher_cfg['sample_limit'])

    pages = _load_pages(root)
    approved = _load_approved_reference_positions(root, matcher_cfg['approved_reference_states'])
    extracted = _build_extracted_instances(
        root,
        matcher_cfg['input_metadata_files'],
        pages,
        sample_limit=sample_limit,
    )

    by_page: Dict[int, List[Dict[str, Any]]] = {}
    for r in approved:
        by_page.setdefault(int(r['page_number']), []).append(r)

    weights = matcher_cfg['weights']
    top_k = int(matcher_cfg['top_k'])

    candidates: List[Dict[str, Any]] = []
    for ex in extracted:
        refs = by_page.get(ex['page_number'], [])
        scored: List[Dict[str, Any]] = []
        ex_bbox = (ex['norm_x'], ex['norm_y'], ex['norm_w'], ex['norm_h'])

        for ref in refs:
            ref_bbox = (float(ref['norm_x']), float(ref['norm_y']), float(ref['norm_w']), float(ref['norm_h']))
            geo = _score_geometry(ex_bbox, ref_bbox, weights)
            ocr = _ocr_agreement(ex['ocr_code'], ref['official_code'])
            confidence = geo['geometry_score']
            if ocr['available'] and ocr['score'] is not None:
                confidence = min(1.0, confidence + (weights['ocr_bonus'] * float(ocr['score'])))

            scored.append({
                'reference_position_id': ref['reference_position_id'],
                'official_code': ref['official_code'],
                'official_description': ref['official_description'],
                'category': ref['category'],
                'grid_row': ref['grid_row'],
                'grid_col': ref['grid_col'],
                'geometry_agreement': geo,
                'ocr_agreement': ocr,
                'confidence': round(confidence, 6),
            })

        scored.sort(
            key=lambda x: (
                -x['confidence'],
                -x['geometry_agreement']['iou'],
                x['geometry_agreement']['center_distance'],
                x['reference_position_id'],
            )
        )

        for rank, best in enumerate(scored[:top_k], start=1):
            candidate_id = _candidate_id(best['reference_position_id'], ex['extracted_sign_id'])
            candidates.append({
                'candidate_assignment_id': candidate_id,
                'reference_position_id': best['reference_position_id'],
                'extracted_sign_id': ex['extracted_sign_id'],
                'extracted_filename': ex['filename'],
                'page_number': ex['page_number'],
                'rank': rank,
                'match_score': best['confidence'],
                'geometry_agreement': best['geometry_agreement'],
                'ocr_agreement': best['ocr_agreement'],
                'validation_status': 'candidate_valid',
                'review_status': 'unreviewed',
                'confidence': best['confidence'],
                'provenance': {
                    'authoritative_source': 'metadata/reference_map/reference_positions.json',
                    'manual_edition': config['edition']['edition_id'],
                    'source_page': ex['page_number'],
                    'assignment_method': 'deterministic_geometry_match_v1',
                    'pipeline_version': config['matcher'].get('enabled') and 'reference-matcher-v1' or 'reference-matcher-disabled',
                    'timestamp': _run_timestamp(),
                },
                'audit': {
                    'algorithm_version': 'reference-matcher-v1',
                    'threshold_profile': 'candidate-strict-v1',
                    'weights': weights,
                    'top_k': top_k,
                },
            })

    candidates.sort(key=lambda x: (x['extracted_sign_id'], x['rank'], x['reference_position_id']))

    run_at = _run_timestamp()
    output = {
        'contract_version': config['contract_version'],
        'matcher_version': '1.0.0',
        'run_type': 'candidate_assignment_only',
        'edition_id': config['edition']['edition_id'],
        'run_at': run_at,
        'sample_limit': sample_limit,
        'top_k': top_k,
        'inputs': {
            'reference_positions': 'metadata/reference_map/reference_positions.json',
            'reference_cells': 'metadata/reference_map/reference_cells.json',
            'manual_editions': 'metadata/reference_map/manual_editions.json',
            'pages': 'metadata/reference_map/pages.json',
            'extracted_metadata_files': matcher_cfg['input_metadata_files'],
        },
        'summary': {
            'approved_reference_positions': len(approved),
            'extracted_sample_size': len(extracted),
            'candidate_count': len(candidates),
        },
        'candidates': candidates,
    }
    return output


def write_candidate_outputs(root: Path, output: Dict[str, Any]) -> Dict[str, str]:
    config = _load_config(root)
    out_cfg = config['matcher']['outputs']
    candidate_path = root / out_cfg['candidate_assignments_file']
    manifest_path = root / out_cfg['matcher_manifest_file']

    write_json(candidate_path, output)

    manifest = {
        'run_type': 'reference_matcher',
        'matcher_version': output['matcher_version'],
        'contract_version': output['contract_version'],
        'run_at': output['run_at'],
        'edition_id': output['edition_id'],
        'sample_limit': output['sample_limit'],
        'top_k': output['top_k'],
        'inputs': output['inputs'],
        'summary': output['summary'],
        'output_file': str(candidate_path.relative_to(root)),
    }
    write_json(manifest_path, manifest)

    return {
        'candidate_file': str(candidate_path),
        'manifest_file': str(manifest_path),
    }
