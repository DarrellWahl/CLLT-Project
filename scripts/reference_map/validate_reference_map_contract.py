import sys
from pathlib import Path
from typing import List

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.reference_map.common import read_json

REF_DIR = ROOT / 'metadata' / 'reference_map'


def validate_contract() -> List[str]:
    errors: List[str] = []

    editions = read_json(REF_DIR / 'manual_editions.json', [])
    pages = read_json(REF_DIR / 'pages.json', [])
    cells_doc = read_json(REF_DIR / 'reference_cells.json', {})
    positions_doc = read_json(REF_DIR / 'reference_positions.json', {})

    page_by_id = {p['page_id']: p for p in pages}
    edition_ids = {e['edition_id'] for e in editions}

    cells = cells_doc.get('cells', [])
    positions = positions_doc.get('positions', [])

    # Contract-driven relationship checks.
    for c in cells:
        if c.get('edition_id') not in edition_ids:
            errors.append(f"contract: cell {c.get('reference_cell_id')} references unknown edition")
        page = page_by_id.get(c.get('page_id'))
        if not page:
            errors.append(f"contract: cell {c.get('reference_cell_id')} references unknown page")
        else:
            if c.get('page_number') != page.get('page_number'):
                errors.append(f"contract: cell {c.get('reference_cell_id')} page_number mismatch")

    cell_ids = {c.get('reference_cell_id') for c in cells}
    for p in positions:
        if p.get('edition_id') not in edition_ids:
            errors.append(f"contract: position {p.get('reference_position_id')} references unknown edition")
        if p.get('page_id') not in page_by_id:
            errors.append(f"contract: position {p.get('reference_position_id')} references unknown page")
        if p.get('reference_cell_id') not in cell_ids:
            errors.append(f"contract: position {p.get('reference_position_id')} references unknown cell")

        # Reference Position abstraction should mirror cell grid and geometry.
        cell = next((c for c in cells if c.get('reference_cell_id') == p.get('reference_cell_id')), None)
        if cell:
            if p.get('grid_row') != cell.get('grid_row') or p.get('grid_col') != cell.get('grid_col'):
                errors.append(f"contract: grid mismatch between position and cell for {p.get('reference_position_id')}")
            geom = cell.get('geometry', {})
            for field in ('norm_x', 'norm_y', 'norm_w', 'norm_h'):
                if round(float(p.get(field, 0.0)), 6) != round(float(geom.get(field, 0.0)), 6):
                    errors.append(f"contract: geometry mismatch {field} for {p.get('reference_position_id')}")

    return errors


def main() -> None:
    errors = validate_contract()
    if errors:
        print('reference_map_contract_valid', False)
        for e in errors:
            print('error', e)
        raise SystemExit(1)
    print('reference_map_contract_valid', True)


if __name__ == '__main__':
    main()
