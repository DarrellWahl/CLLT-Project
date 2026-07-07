import json
import sys
from pathlib import Path
from typing import Any, Dict, List

import cv2

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.reference_map.common import dataclasses_to_dicts, read_json, sha256_file, utc_now_iso, write_json
from scripts.reference_map.models import ManualEdition, PageRecord
from scripts.reference_map.validate_reference_map import validate_reference_map
CONFIG_PATH = ROOT / 'assets' / 'config' / 'reference_map_config.json'


def _load_config(path: Path) -> Dict[str, Any]:
    with path.open('r', encoding='utf-8') as f:
        return json.load(f)


def _manual_edition_from_config(config: Dict[str, Any], now_iso: str) -> ManualEdition:
    edition = config['edition']
    pdf_path = ROOT / edition['source_pdf_path']
    if not pdf_path.exists():
        raise FileNotFoundError(f'Missing source PDF: {pdf_path}')

    return ManualEdition(
        edition_id=edition['edition_id'],
        source_pdf_path=edition['source_pdf_path'],
        source_pdf_filename=pdf_path.name,
        source_pdf_sha256=sha256_file(pdf_path),
        publication_date=edition['publication_date'],
        status=edition['status'],
        created_at=now_iso,
        model_version=config['contract_version'],
    )


def _build_pages(config: Dict[str, Any], edition_id: str, now_iso: str) -> List[PageRecord]:
    pages_cfg = config['pages']
    pages_dir = ROOT / pages_cfg['pages_dir']
    pattern = pages_cfg['page_filename_pattern']

    records: List[PageRecord] = []
    for page_number in pages_cfg['include_pages']:
        filename = pattern.format(page=page_number)
        path = pages_dir / filename
        if not path.exists():
            continue
        image = cv2.imread(str(path))
        if image is None:
            raise RuntimeError(f'Unable to read page image: {path}')
        height, width = image.shape[:2]
        records.append(
            PageRecord(
                page_id=f'{edition_id}-p{page_number}',
                edition_id=edition_id,
                page_number=page_number,
                image_width=width,
                image_height=height,
                page_image_path=str(path.relative_to(ROOT)),
                page_image_sha256=sha256_file(path),
                render_dpi=pages_cfg['render_dpi'],
                normalization_profile=pages_cfg['normalization_profile'],
                created_at=now_iso,
            )
        )

    records.sort(key=lambda r: (r.page_number, r.page_id))
    return records


def _upsert_manual_edition(path: Path, edition: ManualEdition) -> List[Dict[str, Any]]:
    rows = read_json(path, default=[])
    by_id = {row['edition_id']: row for row in rows}
    by_id[edition.edition_id] = {
        **by_id.get(edition.edition_id, {}),
        **dataclasses_to_dicts([edition])[0],
    }
    merged = list(by_id.values())
    merged.sort(key=lambda x: x['edition_id'])
    return merged


def _upsert_pages(path: Path, edition_id: str, pages: List[PageRecord]) -> List[Dict[str, Any]]:
    rows = read_json(path, default=[])
    retained = [r for r in rows if r.get('edition_id') != edition_id]
    merged = retained + dataclasses_to_dicts(pages)
    merged.sort(key=lambda x: (x['edition_id'], x['page_number']))
    return merged


def _ensure_reference_positions(path: Path, config: Dict[str, Any], edition_id: str, page_numbers: List[int], now_iso: str) -> Dict[str, Any]:
    existing = read_json(path, default=None)
    if existing:
        return existing

    doc = {
        'contract_version': config['contract_version'],
        'builder_version': config['builder_version'],
        'edition_id': edition_id,
        'status': 'draft',
        'created_at': now_iso,
        'updated_at': now_iso,
        'notes': 'Reference positions are intentionally empty until authoritative grid annotation is completed.',
        'page_numbers': page_numbers,
        'positions': [],
    }
    return doc


def _ensure_reference_cells(path: Path, config: Dict[str, Any], edition_id: str, now_iso: str) -> Dict[str, Any]:
    existing = read_json(path, default=None)
    if existing:
        return existing

    return {
        'contract_version': config['contract_version'],
        'builder_version': config['builder_version'],
        'edition_id': edition_id,
        'status': 'draft',
        'created_at': now_iso,
        'updated_at': now_iso,
        'cells': [],
    }


def _ensure_id_registry(path: Path, config: Dict[str, Any], now_iso: str) -> Dict[str, Any]:
    existing = read_json(path, default=None)
    if existing:
        return existing

    return {
        'contract_version': config['contract_version'],
        'builder_version': config['builder_version'],
        'created_at': now_iso,
        'updated_at': now_iso,
        'counters': {
            'reference_cell': 1,
            'reference_position': 1,
        },
    }


def _build_manifest(config: Dict[str, Any], edition: ManualEdition, pages_count: int, positions_count: int, now_iso: str, ref_dir: Path) -> Dict[str, Any]:
    return {
        'run_type': 'reference_map_builder',
        'builder_version': config['builder_version'],
        'contract_version': config['contract_version'],
        'ran_at': now_iso,
        'edition_id': edition.edition_id,
        'source_pdf_path': edition.source_pdf_path,
        'source_pdf_sha256': edition.source_pdf_sha256,
        'pages_count': pages_count,
        'reference_positions_count': positions_count,
        'outputs': {
            'manual_editions': str((ref_dir / config['outputs']['manual_editions_file']).relative_to(ROOT)),
            'pages': str((ref_dir / config['outputs']['pages_file']).relative_to(ROOT)),
            'reference_cells': str((ref_dir / config['outputs']['reference_cells_file']).relative_to(ROOT)),
            'reference_positions': str((ref_dir / config['outputs']['reference_positions_file']).relative_to(ROOT)),
            'id_registry': str((ref_dir / config['outputs']['id_registry_file']).relative_to(ROOT)),
        },
    }


def main() -> None:
    config = _load_config(CONFIG_PATH)
    now_iso = utc_now_iso()

    outputs = config['outputs']
    ref_dir = ROOT / outputs['reference_map_dir']
    editions_path = ref_dir / outputs['manual_editions_file']
    pages_path = ref_dir / outputs['pages_file']
    cells_path = ref_dir / outputs['reference_cells_file']
    positions_path = ref_dir / outputs['reference_positions_file']
    id_registry_path = ref_dir / outputs['id_registry_file']
    manifest_path = ROOT / outputs['run_manifest_file']

    edition = _manual_edition_from_config(config, now_iso)
    pages = _build_pages(config, edition.edition_id, now_iso)

    editions_doc = _upsert_manual_edition(editions_path, edition)
    pages_doc = _upsert_pages(pages_path, edition.edition_id, pages)
    cells_doc = _ensure_reference_cells(cells_path, config, edition.edition_id, now_iso)
    positions_doc = _ensure_reference_positions(
        positions_path,
        config,
        edition.edition_id,
        [p.page_number for p in pages],
        now_iso,
    )
    id_registry_doc = _ensure_id_registry(id_registry_path, config, now_iso)

    write_json(editions_path, editions_doc)
    write_json(pages_path, pages_doc)
    write_json(cells_path, cells_doc)
    write_json(positions_path, positions_doc)
    write_json(id_registry_path, id_registry_doc)

    errors = validate_reference_map(ref_dir)
    if errors:
        for e in errors:
            print('validation_error', e)
        raise SystemExit(1)

    manifest = _build_manifest(
        config,
        edition,
        pages_count=len(pages),
        positions_count=len(positions_doc.get('positions', [])),
        now_iso=now_iso,
        ref_dir=ref_dir,
    )
    write_json(manifest_path, manifest)

    print('reference_map_builder_ok', True)
    print('edition_id', edition.edition_id)
    print('pages', len(pages))
    print('reference_positions', len(positions_doc.get('positions', [])))
    print('manifest', manifest_path)


if __name__ == '__main__':
    main()
