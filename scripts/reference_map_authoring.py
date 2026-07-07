import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.reference_map.authoring import ReferenceAuthoringStore, deterministic_sample_payloads
from scripts.reference_map.common import read_json


def _pages_by_number(root: Path, edition_id: str) -> Dict[int, Dict[str, Any]]:
    pages = read_json(root / 'metadata' / 'reference_map' / 'pages.json', [])
    return {p['page_number']: p for p in pages if p.get('edition_id') == edition_id}


def _build_sample_cell_geometry(index: int) -> Dict[str, float]:
    # Deterministic synthetic geometry for workflow validation only.
    base_x = 0.06 + (index % 4) * 0.20
    base_y = 0.08 + (index // 4) * 0.22
    return {
        'norm_x': round(base_x, 6),
        'norm_y': round(base_y, 6),
        'norm_w': 0.14,
        'norm_h': 0.16,
        'rotation_deg': 0.0,
        'margin_top': 0.002,
        'margin_right': 0.002,
        'margin_bottom': 0.002,
        'margin_left': 0.002,
        'padding_top': 0.003,
        'padding_right': 0.003,
        'padding_bottom': 0.003,
        'padding_left': 0.003,
    }


def cmd_seed_sample(args: argparse.Namespace) -> None:
    store = ReferenceAuthoringStore(ROOT)
    page_map = _pages_by_number(ROOT, args.edition_id)
    if not page_map:
        raise RuntimeError(f'No pages found for edition_id={args.edition_id}. Run scripts/build_reference_map.py first.')

    sample = deterministic_sample_payloads()
    page_sequence = [1, 2, 3, 4, 5]

    created_positions: List[str] = []
    for i, payload in enumerate(sample):
        page_number = page_sequence[i % len(page_sequence)]
        if page_number not in page_map:
            continue
        page = page_map[page_number]

        grid_row = (i // 4) + 1
        grid_col = (i % 4) + 1

        cell = store.create_reference_cell(
            edition_id=args.edition_id,
            page=page,
            grid_row=grid_row,
            grid_col=grid_col,
            geometry=_build_sample_cell_geometry(i),
            actor=args.actor,
            notes='Seed sample cell for workflow validation',
        )

        position = store.create_reference_position(
            edition_id=args.edition_id,
            page=page,
            cell=cell,
            payload=payload,
            actor=args.actor,
            notes='Seed sample position for workflow validation',
        )

        # push sample through review + approval lifecycle to test workflows
        store.transition_position(position['reference_position_id'], 'review', args.actor, 'Sample review transition')
        store.transition_position(position['reference_position_id'], 'approve', args.actor, 'Sample approval transition')
        created_positions.append(position['reference_position_id'])

    print('seed_sample_ok', True)
    print('edition_id', args.edition_id)
    print('created_positions', len(created_positions))


def cmd_transition(args: argparse.Namespace) -> None:
    store = ReferenceAuthoringStore(ROOT)
    position = store.transition_position(args.reference_position_id, args.event, args.actor, args.notes)
    print('transition_ok', True)
    print('reference_position_id', position['reference_position_id'])
    print('event', args.event)
    print('approval_state', position.get('approval_state'))


def cmd_list(args: argparse.Namespace) -> None:
    store = ReferenceAuthoringStore(ROOT)
    positions = store.list_positions()
    print('positions', len(positions))
    for p in positions[: args.limit]:
        print(
            p['reference_position_id'],
            p['official_code'],
            p['category'],
            p['page_number'],
            p['grid_row'],
            p['grid_col'],
            p['approval_state'],
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Reference Position Authoring System')
    sub = parser.add_subparsers(dest='command', required=True)

    seed = sub.add_parser('seed-sample', help='Create deterministic sample reference cells and positions')
    seed.add_argument('--edition-id', default='za-rtl-2026-01')
    seed.add_argument('--actor', default='system')
    seed.set_defaults(func=cmd_seed_sample)

    tr = sub.add_parser('transition', help='Apply lifecycle transition to one reference position')
    tr.add_argument('reference_position_id')
    tr.add_argument('event', choices=['edit', 'review', 'approve', 'deprecate', 'archive'])
    tr.add_argument('--actor', default='system')
    tr.add_argument('--notes', default='manual transition')
    tr.set_defaults(func=cmd_transition)

    ls = sub.add_parser('list', help='List authored positions')
    ls.add_argument('--limit', type=int, default=20)
    ls.set_defaults(func=cmd_list)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
