import copy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

from scripts.reference_map.common import read_json, utc_now_iso, write_json


@dataclass
class AuthoringPaths:
    root: Path

    @property
    def reference_map_dir(self) -> Path:
        return self.root / 'metadata' / 'reference_map'

    @property
    def id_registry(self) -> Path:
        return self.reference_map_dir / 'id_registry.json'

    @property
    def reference_cells(self) -> Path:
        return self.reference_map_dir / 'reference_cells.json'

    @property
    def reference_positions(self) -> Path:
        return self.reference_map_dir / 'reference_positions.json'


class IdAllocator:
    def __init__(self, paths: AuthoringPaths):
        self.paths = paths

    def _default_doc(self) -> Dict[str, Any]:
        return {
            'contract_version': '1.0.0',
            'created_at': utc_now_iso(),
            'updated_at': utc_now_iso(),
            'counters': {
                'reference_cell': 1,
                'reference_position': 1,
            },
        }

    def _load(self) -> Dict[str, Any]:
        return read_json(self.paths.id_registry, self._default_doc())

    def _save(self, doc: Dict[str, Any]) -> None:
        doc['updated_at'] = utc_now_iso()
        write_json(self.paths.id_registry, doc)

    def next_id(self, key: str, prefix: str) -> str:
        doc = self._load()
        counter = int(doc['counters'][key])
        value = f'{prefix}-{counter:06d}'
        doc['counters'][key] = counter + 1
        self._save(doc)
        return value


class ReferenceAuthoringStore:
    def __init__(self, root: Path):
        self.paths = AuthoringPaths(root=root)
        self.alloc = IdAllocator(self.paths)

    def _default_cells(self, edition_id: str) -> Dict[str, Any]:
        now = utc_now_iso()
        return {
            'contract_version': '1.0.0',
            'edition_id': edition_id,
            'status': 'draft',
            'created_at': now,
            'updated_at': now,
            'cells': [],
        }

    def _default_positions(self, edition_id: str) -> Dict[str, Any]:
        now = utc_now_iso()
        return {
            'contract_version': '1.0.0',
            'builder_version': '1.0.0',
            'edition_id': edition_id,
            'status': 'draft',
            'created_at': now,
            'updated_at': now,
            'notes': 'Reference positions authored through Reference Position Authoring System.',
            'page_numbers': [],
            'positions': [],
        }

    def _load_positions_doc(self, edition_id: str) -> Dict[str, Any]:
        current = read_json(self.paths.reference_positions, None)
        if not current:
            current = self._default_positions(edition_id)
        if 'positions' not in current:
            current['positions'] = []
        return current

    def _save_positions_doc(self, doc: Dict[str, Any]) -> None:
        doc['updated_at'] = utc_now_iso()
        doc['positions'].sort(key=lambda x: x['reference_position_id'])
        write_json(self.paths.reference_positions, doc)

    def _load_cells_doc(self, edition_id: str) -> Dict[str, Any]:
        current = read_json(self.paths.reference_cells, None)
        if not current:
            current = self._default_cells(edition_id)
        if 'cells' not in current:
            current['cells'] = []
        return current

    def _save_cells_doc(self, doc: Dict[str, Any]) -> None:
        doc['updated_at'] = utc_now_iso()
        doc['cells'].sort(key=lambda x: x['reference_cell_id'])
        write_json(self.paths.reference_cells, doc)

    def _append_history(self, record: Dict[str, Any], event_type: str, actor: str, notes: str) -> None:
        record.setdefault('history', []).append({
            'event_type': event_type,
            'timestamp': utc_now_iso(),
            'actor': actor,
            'notes': notes,
        })

    def _add_version_snapshot(self, record: Dict[str, Any], change_type: str, actor: str, notes: str) -> None:
        versions = record.setdefault('versions', [])
        next_version = len(versions) + 1
        snapshot = {
            'version': next_version,
            'changed_at': utc_now_iso(),
            'change_type': change_type,
            'actor': actor,
            'notes': notes,
            'state': {
                'reference_cell_id': record['reference_cell_id'],
                'edition_id': record['edition_id'],
                'page_id': record['page_id'],
                'page_number': record['page_number'],
                'grid_row': record['grid_row'],
                'grid_col': record['grid_col'],
                'official_code': record['official_code'],
                'official_description': record['official_description'],
                'category': record['category'],
                'category_detail': record.get('category_detail', ''),
                'validation_status': record['validation_status'],
                'approval_state': record['approval_state'],
            },
        }
        versions.append(snapshot)
        record['current_version'] = next_version

    def create_reference_cell(self, edition_id: str, page: Dict[str, Any], grid_row: int, grid_col: int, geometry: Dict[str, float], actor: str, notes: str) -> Dict[str, Any]:
        doc = self._load_cells_doc(edition_id)
        reference_cell_id = self.alloc.next_id('reference_cell', 'RC')
        now = utc_now_iso()

        cell = {
            'reference_cell_id': reference_cell_id,
            'edition_id': edition_id,
            'page_id': page['page_id'],
            'page_number': page['page_number'],
            'grid_row': grid_row,
            'grid_col': grid_col,
            'geometry': {
                'norm_x': geometry['norm_x'],
                'norm_y': geometry['norm_y'],
                'norm_w': geometry['norm_w'],
                'norm_h': geometry['norm_h'],
                'norm_cx': geometry['norm_x'] + geometry['norm_w'] / 2.0,
                'norm_cy': geometry['norm_y'] + geometry['norm_h'] / 2.0,
                'rotation_deg': geometry.get('rotation_deg', 0.0),
                'margin': {
                    'top': geometry.get('margin_top', 0.0),
                    'right': geometry.get('margin_right', 0.0),
                    'bottom': geometry.get('margin_bottom', 0.0),
                    'left': geometry.get('margin_left', 0.0),
                },
                'padding': {
                    'top': geometry.get('padding_top', 0.0),
                    'right': geometry.get('padding_right', 0.0),
                    'bottom': geometry.get('padding_bottom', 0.0),
                    'left': geometry.get('padding_left', 0.0),
                },
            },
            'cell_status': 'draft',
            'approval_state': 'draft',
            'created_at': now,
            'updated_at': now,
            'provenance': {
                'creation_timestamp': now,
                'authoring_method': 'reference_position_authoring_system',
                'pipeline_version': 'reference-map-authoring-v1',
                'manual_edition': edition_id,
                'source_page': page['page_number'],
                'validation_state': 'pending',
                'approval_state': 'draft',
                'history': [
                    {
                        'event_type': 'create',
                        'timestamp': now,
                        'actor': actor,
                        'notes': notes,
                    }
                ],
            },
            'archived': False,
        }

        doc['cells'].append(cell)
        self._save_cells_doc(doc)
        return cell

    def create_reference_position(self, edition_id: str, page: Dict[str, Any], cell: Dict[str, Any], payload: Dict[str, Any], actor: str, notes: str) -> Dict[str, Any]:
        doc = self._load_positions_doc(edition_id)
        reference_position_id = self.alloc.next_id('reference_position', 'RP')
        now = utc_now_iso()

        position = {
            'reference_position_id': reference_position_id,
            'edition_id': edition_id,
            'page_id': page['page_id'],
            'page_number': page['page_number'],
            'reference_cell_id': cell['reference_cell_id'],
            'grid_row': cell['grid_row'],
            'grid_col': cell['grid_col'],
            'norm_x': cell['geometry']['norm_x'],
            'norm_y': cell['geometry']['norm_y'],
            'norm_w': cell['geometry']['norm_w'],
            'norm_h': cell['geometry']['norm_h'],
            'official_code': payload['official_code'],
            'official_description': payload['official_description'],
            'category': payload['category'],
            'category_detail': payload.get('category_detail', ''),
            'extracted_image_filename': payload.get('extracted_image_filename', ''),
            'reference_status': 'draft',
            'validation_status': 'pending',
            'approval_state': 'draft',
            'authoring_method': 'reference_position_authoring_system',
            'pipeline_version': 'reference-map-authoring-v1',
            'manual_edition': edition_id,
            'source_page': page['page_number'],
            'confidence': None,
            'created_at': now,
            'updated_at': now,
            'current_version': 0,
            'versions': [],
            'history': [],
            'archived': False,
        }

        self._append_history(position, 'create', actor, notes)
        self._add_version_snapshot(position, 'create', actor, notes)

        doc['positions'].append(position)
        doc['page_numbers'] = sorted({*doc.get('page_numbers', []), page['page_number']})
        self._save_positions_doc(doc)
        return position

    def transition_position(self, reference_position_id: str, event: str, actor: str, notes: str) -> Dict[str, Any]:
        doc = read_json(self.paths.reference_positions, {})
        positions = doc.get('positions', [])
        found = None
        for p in positions:
            if p.get('reference_position_id') == reference_position_id:
                found = p
                break
        if not found:
            raise KeyError(f'Unknown reference_position_id: {reference_position_id}')

        # lifecycle transitions: create/edit/review/approve/deprecate/archive
        if event == 'edit':
            found['reference_status'] = 'draft'
            found['validation_status'] = 'pending'
            found['approval_state'] = 'draft'
        elif event == 'review':
            found['validation_status'] = 'reviewed'
            found['approval_state'] = 'in_review'
        elif event == 'approve':
            found['reference_status'] = 'verified'
            found['validation_status'] = 'valid'
            found['approval_state'] = 'approved'
        elif event == 'deprecate':
            found['reference_status'] = 'deprecated'
            found['approval_state'] = 'deprecated'
        elif event == 'archive':
            found['archived'] = True
            found['approval_state'] = 'archived'
        else:
            raise ValueError(f'Unsupported event: {event}')

        found['updated_at'] = utc_now_iso()
        self._append_history(found, event, actor, notes)
        self._add_version_snapshot(found, event, actor, notes)

        doc['positions'] = positions
        self._save_positions_doc(doc)
        return found

    def list_positions(self) -> List[Dict[str, Any]]:
        return read_json(self.paths.reference_positions, {}).get('positions', [])


def deterministic_sample_payloads() -> List[Dict[str, str]]:
    # Sample only, intentionally small and cross-category.
    return [
        {'official_code': 'R1', 'official_description': 'Stop sign', 'category': 'regulatory'},
        {'official_code': 'R2', 'official_description': 'Yield', 'category': 'regulatory'},
        {'official_code': 'R101', 'official_description': 'No entry', 'category': 'regulatory'},
        {'official_code': 'W201', 'official_description': 'Sharp bend ahead', 'category': 'warning'},
        {'official_code': 'W202', 'official_description': 'Pedestrian crossing ahead', 'category': 'warning'},
        {'official_code': 'GS1', 'official_description': 'Motorway ahead', 'category': 'guidance'},
        {'official_code': 'GS2', 'official_description': 'Route direction sign', 'category': 'guidance'},
        {'official_code': 'TR1', 'official_description': 'Roadworks ahead', 'category': 'temporary'},
        {'official_code': 'TR2', 'official_description': 'Temporary speed restriction', 'category': 'temporary'},
        {'official_code': 'INF1', 'official_description': 'Parking area', 'category': 'information'},
        {'official_code': 'INF2', 'official_description': 'Hospital', 'category': 'information'},
        {'official_code': 'M1', 'official_description': 'Tourism information', 'category': 'miscellaneous', 'category_detail': 'tourism'},
    ]
