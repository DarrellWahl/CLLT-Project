# Changelog

## Documentation Version 1.1.0 - 2026-07-07

### Added

- Added [TRACEABILITY_MATRIX.md](TRACEABILITY_MATRIX.md) mapping all reported metrics to source files and derivations.
- Added [CHANGELOG.md](CHANGELOG.md) as the authoritative documentation version log.
- Restored/added missing [DECISION_LOG.md](DECISION_LOG.md) in `docs/` root.

### Updated

- Updated [README.md](README.md) to:
  - use explicit internal links for all core docs,
  - include [TRACEABILITY_MATRIX.md](TRACEABILITY_MATRIX.md) and [CHANGELOG.md](CHANGELOG.md) in reading order,
  - codify Documentation Policy.
- Updated [PROJECT_STATUS.md](PROJECT_STATUS.md) to version 1.1.0 and documented integrity-pass completion.
- Updated [PROJECT_PROGRESS.md](PROJECT_PROGRESS.md) to version 1.1.0 and added integrity milestone.

### Validation Performed

- Verified internal documentation links.
- Verified referenced source files used by reported metrics.
- Verified metric consistency against source artifacts:
  - Website rows: 1,090
  - Coded rows: 258
  - Uncoded rows: 832
  - Legend entries: 168
  - Legacy clean mappings: 89
  - Exported totals pages 1-4: 1,090
- Validated [PROJECT_STATE.json](PROJECT_STATE.json) as syntactically valid JSON.
- Verified no duplicate/conflicting documentation files between `docs/` and `docs/archive/`.

### Policy

- `docs/` is authoritative for active project documentation.
- `docs/archive/` is historical snapshot storage only.
- Never move active docs into archive.
- Never overwrite archived versions.
- On every documentation change:
  1. Update [CHANGELOG.md](CHANGELOG.md).
  2. Update [PROJECT_STATUS.md](PROJECT_STATUS.md) if metrics change.
  3. Update [PROJECT_PROGRESS.md](PROJECT_PROGRESS.md) if milestones change.
  4. Validate [PROJECT_STATE.json](PROJECT_STATE.json).
  5. Verify all documentation links.
  6. Record documentation version.
