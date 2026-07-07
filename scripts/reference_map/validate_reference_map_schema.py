import json
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path(__file__).resolve().parents[2]
REF_DIR = ROOT / 'metadata' / 'reference_map'


def _load(path: Path) -> Any:
    with path.open('r', encoding='utf-8') as f:
        return json.load(f)


def _require_fields(record: Dict[str, Any], fields: List[str], label: str, errors: List[str]) -> None:
    for f in fields:
        if f not in record:
            errors.append(f'{label}: missing field {f}')


def validate_schema() -> List[str]:
    errors: List[str] = []

    editions = _load(REF_DIR / 'manual_editions.json')
    pages = _load(REF_DIR / 'pages.json')
    cells_doc = _load(REF_DIR / 'reference_cells.json')
    positions_doc = _load(REF_DIR / 'reference_positions.json')

    if not isinstance(editions, list):
        errors.append('manual_editions.json: expected list')
    if not isinstance(pages, list):
        errors.append('pages.json: expected list')
    if not isinstance(cells_doc, dict):
        errors.append('reference_cells.json: expected object')
    if not isinstance(positions_doc, dict):
        errors.append('reference_positions.json: expected object')

    for i, row in enumerate(editions if isinstance(editions, list) else []):
        _require_fields(
            row,
            [
                'edition_id',
                'source_pdf_path',
                'source_pdf_filename',
                'source_pdf_sha256',
                'publication_date',
                'status',
                'created_at',
                'model_version',
            ],
            f'manual_editions[{i}]',
            errors,
        )

    for i, row in enumerate(pages if isinstance(pages, list) else []):
        _require_fields(
            row,
            [
                'page_id',
                'edition_id',
                'page_number',
                'image_width',
                'image_height',
                'page_image_path',
                'page_image_sha256',
                'render_dpi',
                'normalization_profile',
                'created_at',
            ],
            f'pages[{i}]',
            errors,
        )

    cells = cells_doc.get('cells', []) if isinstance(cells_doc, dict) else []
    for i, row in enumerate(cells):
        _require_fields(
            row,
            [
                'reference_cell_id',
                'edition_id',
                'page_id',
                'page_number',
                'grid_row',
                'grid_col',
                'geometry',
                'cell_status',
                'approval_state',
                'created_at',
                'updated_at',
                'provenance',
                'archived',
            ],
            f'reference_cells.cells[{i}]',
            errors,
        )

    positions = positions_doc.get('positions', []) if isinstance(positions_doc, dict) else []
    for i, row in enumerate(positions):
        _require_fields(
            row,
            [
                'reference_position_id',
                'edition_id',
                'page_id',
                'page_number',
                'reference_cell_id',
                'grid_row',
                'grid_col',
                'norm_x',
                'norm_y',
                'norm_w',
                'norm_h',
                'official_code',
                'official_description',
                'category',
                'reference_status',
                'validation_status',
                'approval_state',
                'authoring_method',
                'pipeline_version',
                'manual_edition',
                'source_page',
                'created_at',
                'updated_at',
                'current_version',
                'versions',
                'history',
                'archived',
            ],
            f'reference_positions.positions[{i}]',
            errors,
        )

    return errors


def main() -> None:
    errors = validate_schema()
    if errors:
        print('reference_map_schema_valid', False)
        for e in errors:
            print('error', e)
        raise SystemExit(1)
    print('reference_map_schema_valid', True)


if __name__ == '__main__':
    main()
