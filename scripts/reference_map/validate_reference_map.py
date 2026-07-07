import json
import re
from pathlib import Path
from typing import Any, Dict, List

HEX64_RE = re.compile(r'^[0-9a-f]{64}$')
CODE_RE = re.compile(r'^[A-Z]{1,4}[0-9]{1,3}(\.[0-9]{1,2})?$')
RC_RE = re.compile(r'^RC-[0-9]{6}$')
RP_RE = re.compile(r'^RP-[0-9]{6}$')

ALLOWED_REFERENCE_STATUS = {'draft', 'verified', 'disputed', 'deprecated'}
ALLOWED_APPROVAL_STATE = {'draft', 'in_review', 'approved', 'deprecated', 'archived'}
ALLOWED_VALIDATION_STATUS = {'pending', 'reviewed', 'valid', 'invalid'}
ALLOWED_CATEGORY = {'regulatory', 'warning', 'guidance', 'information', 'temporary', 'miscellaneous'}


def _load(path: Path) -> Any:
    with path.open('r', encoding='utf-8') as f:
        return json.load(f)


def validate_reference_map(reference_map_dir: Path) -> List[str]:
    errors: List[str] = []
    editions_path = reference_map_dir / 'manual_editions.json'
    pages_path = reference_map_dir / 'pages.json'
    cells_path = reference_map_dir / 'reference_cells.json'
    positions_path = reference_map_dir / 'reference_positions.json'

    editions = _load(editions_path)
    pages = _load(pages_path)
    cells_doc = _load(cells_path)
    positions_doc = _load(positions_path)

    edition_ids = set()
    for e in editions:
        edition_id = e.get('edition_id', '')
        if not edition_id:
            errors.append('manual_editions: missing edition_id')
        if edition_id in edition_ids:
            errors.append(f'manual_editions: duplicate edition_id {edition_id}')
        edition_ids.add(edition_id)
        sha = e.get('source_pdf_sha256', '')
        if not HEX64_RE.match(sha):
            errors.append(f'manual_editions: invalid source_pdf_sha256 for {edition_id}')

    page_keys = set()
    page_id_set = set()
    for p in pages:
        page_id = p.get('page_id', '')
        edition_id = p.get('edition_id', '')
        page_number = p.get('page_number')
        page_id_set.add(page_id)
        if edition_id not in edition_ids:
            errors.append(f'pages: unknown edition_id {edition_id}')
        if not isinstance(page_number, int) or page_number < 1:
            errors.append(f'pages: invalid page_number for {page_id}')
        key = (edition_id, page_number)
        if key in page_keys:
            errors.append(f'pages: duplicate (edition_id,page_number) {key}')
        page_keys.add(key)
        sha = p.get('page_image_sha256', '')
        if not HEX64_RE.match(sha):
            errors.append(f'pages: invalid page_image_sha256 for {page_id}')

    cells = cells_doc.get('cells', [])
    cell_ids = set()
    cell_grid_keys = set()
    cell_geometry_keys = set()
    for c in cells:
        cell_id = c.get('reference_cell_id', '')
        edition_id = c.get('edition_id', '')
        page_id = c.get('page_id', '')
        page_number = c.get('page_number')
        grid_row = c.get('grid_row')
        grid_col = c.get('grid_col')

        if not RC_RE.match(cell_id):
            errors.append(f'reference_cells: invalid reference_cell_id {cell_id}')
        if cell_id in cell_ids:
            errors.append(f'reference_cells: duplicate reference_cell_id {cell_id}')
        cell_ids.add(cell_id)

        if edition_id not in edition_ids:
            errors.append(f'reference_cells: unknown edition_id {edition_id}')
        if page_id not in page_id_set:
            errors.append(f'reference_cells: unknown page_id {page_id}')
        if (edition_id, page_number) not in page_keys:
            errors.append(f'reference_cells: unknown page mapping {(edition_id, page_number)}')

        grid_key = (edition_id, page_number, grid_row, grid_col)
        if grid_key in cell_grid_keys:
            errors.append(f'reference_cells: duplicate grid key {grid_key}')
        cell_grid_keys.add(grid_key)

        geom = c.get('geometry', {})
        for f in ('norm_x', 'norm_y', 'norm_w', 'norm_h', 'norm_cx', 'norm_cy', 'rotation_deg'):
            val = geom.get(f)
            if not isinstance(val, (int, float)):
                errors.append(f'reference_cells: non-numeric geometry field {f} for {cell_id}')
        nx = geom.get('norm_x', -1)
        ny = geom.get('norm_y', -1)
        nw = geom.get('norm_w', -1)
        nh = geom.get('norm_h', -1)
        if not (0 <= nx <= 1 and 0 <= ny <= 1 and 0 <= nw <= 1 and 0 <= nh <= 1):
            errors.append(f'reference_cells: out-of-range bbox in {cell_id}')
        if nx + nw > 1 or ny + nh > 1:
            errors.append(f'reference_cells: bbox exceeds page bounds in {cell_id}')

        geom_key = (edition_id, page_number, round(nx, 6), round(ny, 6), round(nw, 6), round(nh, 6))
        if geom_key in cell_geometry_keys:
            errors.append(f'reference_cells: duplicate geometry on page for {cell_id}')
        cell_geometry_keys.add(geom_key)

        prov = c.get('provenance', {})
        for req in ('creation_timestamp', 'authoring_method', 'pipeline_version', 'manual_edition', 'source_page', 'validation_state', 'approval_state', 'history'):
            if req not in prov:
                errors.append(f'reference_cells: missing provenance.{req} for {cell_id}')
        if not isinstance(prov.get('history', []), list) or not prov.get('history', []):
            errors.append(f'reference_cells: empty provenance history for {cell_id}')

    positions = positions_doc.get('positions', [])
    position_ids = set()
    seen_position_keys = set()
    for r in positions:
        position_id = r.get('reference_position_id', '')
        if not RP_RE.match(position_id):
            errors.append(f'reference_positions: invalid reference_position_id {position_id}')
        if position_id in position_ids:
            errors.append(f'reference_positions: duplicate reference_position_id {position_id}')
        position_ids.add(position_id)

        edition_id = r.get('edition_id', '')
        page_id = r.get('page_id', '')
        page_number = r.get('page_number')
        grid_row = r.get('grid_row')
        grid_col = r.get('grid_col')
        code = r.get('official_code', '')
        desc = r.get('official_description', '')
        category = r.get('category', '')
        ref_cell_id = r.get('reference_cell_id', '')

        key = (edition_id, page_number, grid_row, grid_col)
        if key in seen_position_keys:
            errors.append(f'reference_positions: duplicate grid key {key}')
        seen_position_keys.add(key)

        if edition_id not in edition_ids:
            errors.append(f'reference_positions: unknown edition_id {edition_id}')
        if page_id not in page_id_set:
            errors.append(f'reference_positions: unknown page_id {page_id}')
        if (edition_id, page_number) not in page_keys:
            errors.append(f'reference_positions: unknown page mapping {(edition_id, page_number)}')
        if ref_cell_id not in cell_ids:
            errors.append(f'reference_positions: unknown reference_cell_id {ref_cell_id}')
        if code and not CODE_RE.match(code):
            errors.append(f'reference_positions: invalid official_code {code}')
        if code and not desc:
            errors.append(f'reference_positions: code without description for key {key}')
        if category not in ALLOWED_CATEGORY:
            errors.append(f'reference_positions: invalid category {category} for {position_id}')

        if r.get('reference_status') not in ALLOWED_REFERENCE_STATUS:
            errors.append(f'reference_positions: invalid reference_status for {position_id}')
        if r.get('approval_state') not in ALLOWED_APPROVAL_STATE:
            errors.append(f'reference_positions: invalid approval_state for {position_id}')
        if r.get('validation_status') not in ALLOWED_VALIDATION_STATUS:
            errors.append(f'reference_positions: invalid validation_status for {position_id}')

        versions = r.get('versions', [])
        current_version = r.get('current_version', 0)
        if not isinstance(versions, list) or not versions:
            errors.append(f'reference_positions: missing versions for {position_id}')
        else:
            if current_version != len(versions):
                errors.append(f'reference_positions: current_version mismatch for {position_id}')

        history = r.get('history', [])
        if not isinstance(history, list) or not history:
            errors.append(f'reference_positions: missing history for {position_id}')

        for f in ('norm_x', 'norm_y', 'norm_w', 'norm_h'):
            value = r.get(f)
            if not isinstance(value, (int, float)) or value < 0 or value > 1:
                errors.append(f'reference_positions: invalid {f} for key {key}')
        if (r.get('norm_x', 0) + r.get('norm_w', 0)) > 1 or (r.get('norm_y', 0) + r.get('norm_h', 0)) > 1:
            errors.append(f'reference_positions: bbox exceeds page bounds for {position_id}')

    # orphan detection: every cell should back at least one position in authored samples/workflows
    position_cell_ids = {p.get('reference_cell_id') for p in positions}
    for cell_id in cell_ids:
        if cell_id not in position_cell_ids:
            errors.append(f'reference_cells: orphan cell {cell_id} has no linked reference_position')

    return errors


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    reference_map_dir = root / 'metadata' / 'reference_map'
    errors = validate_reference_map(reference_map_dir)
    if errors:
        print('reference_map_valid', False)
        for e in errors:
            print('error', e)
        raise SystemExit(1)
    print('reference_map_valid', True)


if __name__ == '__main__':
    main()
