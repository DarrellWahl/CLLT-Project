# CLLT Project

CLLT is a deterministic extraction and verification platform for South African road traffic signs, with a static website for browsing extracted sign assets and metadata.

## Project Overview

The project ingests source pages, extracts sign crops and metadata, runs deterministic validation workflows, and publishes a website-facing dataset. It also includes a reference-map authoring and candidate-matching layer for provenance-first labeling.

## Purpose

The primary objective is to build a reproducible pipeline that supports full sign extraction, traceable identification, and verification workflows, while preserving auditability across datasets, logs, and engineering artifacts.

## Current Development Status

- Core extraction pipeline is operational.
- Website dataset and browser are operational.
- Reference-map platform milestones 1-3 are implemented (builder, authoring, deterministic candidate matcher).
- Full authoritative labeling and publication workflow is still in progress.

See [docs/PROJECT_STATUS.md](docs/PROJECT_STATUS.md) and [docs/ENGINEERING_PROGRESS.md](docs/ENGINEERING_PROGRESS.md) for current details.

## Major Features

- Deterministic extraction pipeline and rerun checks.
- Dataset publishing and completion auditing tools.
- Reference map builder and authoring system with immutable IDs and provenance history.
- Candidate assignment matcher (candidate-only, no direct publication).
- Static website with lazy-loaded sign browsing.
- Documentation dossier with architecture, decisions, traceability, and progress tracking.

## Repository Structure

- `assets/`: source PDFs, page images, configs, and visual assets.
- `scripts/`: extraction, validation, publishing, reference-map, and utility scripts.
- `metadata/`: consolidated metadata and reference-map outputs.
- `logs/`: run manifests and determinism/completion reports.
- `output/`: extraction and mapping outputs used by mapping/provenance workflows.
- `website/`: static site and website dataset artifacts.
- `docs/`: project dossier, architecture docs, plans, and engineering reports.

## Installation

1. Create and activate a Python 3.11 virtual environment.
2. Install required dependencies.
3. Ensure source assets are present under `assets/`.

Example:

```bash
python3.11 -m venv .venv311
source .venv311/bin/activate
pip install -r requirements.txt
```

If `requirements.txt` is not yet present in your local clone, install the packages required by the scripts you run (for example, OpenCV and related tooling) and consider contributing a pinned requirements file.

## Running Locally

Common workflows:

```bash
# Build/reference-map foundation artifacts
python scripts/build_reference_map.py

# Validate reference-map contracts and schema
python scripts/reference_map/validate_reference_map.py
python scripts/reference_map/validate_reference_map_schema.py
python scripts/reference_map/validate_reference_map_contract.py

# Determinism and extraction completion audits
python scripts/check_rerun_determinism.py
python scripts/audit_extraction_completion.py

# Serve the website locally
cd website
python -m http.server 8000
```

Then open `http://127.0.0.1:8000/` in a browser.

## Development Roadmap

1. Complete full reference-position authoring coverage.
2. Implement review queue and approval workflow for candidate assignments.
3. Promote validated assignments into authoritative datasets.
4. Add CI checks for determinism, schema, and dataset consistency.
5. Improve packaging and dependency pinning.

## License

No repository license file is currently present.

Before broader collaboration, add a standard license file (for example MIT, Apache-2.0, or a proprietary internal license policy) based on your intended distribution model.

## Future Goals

- Reach verified, end-to-end coverage for all extracted signs.
- Maintain deterministic reruns and auditable provenance.
- Support collaborative curation and quality gates at scale.

## Contributor Guidance

- Preserve deterministic behavior and provenance guarantees.
- Avoid direct edits to protected production artifacts unless explicitly planned.
- Prefer small, auditable commits with validation evidence.
- Keep documentation in `docs/` synchronized with architecture and data model changes.

For onboarding and system context, start at [docs/README.md](docs/README.md).
