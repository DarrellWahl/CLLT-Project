# Engineering Progress Reports

## Milestone 1 - Reference Map Builder Foundation

Date: 2026-07-07

Objective:

- Start implementation of the Reference Map Builder without modifying stable production components.
- Establish deterministic, auditable baseline artifacts for manual edition and page registry.

Work completed:

- Added external configuration for Reference Map Builder.
- Added reusable reference_map package utilities and models.
- Implemented deterministic builder entrypoint for:
  - Manual Edition registry generation
  - Page registry generation with image hashes and dimensions
  - Initial reference_positions scaffold creation
  - Run manifest output
- Implemented contract validation script for reference map artifacts.

Files created:

- assets/config/reference_map_config.json
- scripts/reference_map/__init__.py
- scripts/reference_map/common.py
- scripts/reference_map/models.py
- scripts/reference_map/validate_reference_map.py
- scripts/build_reference_map.py
- metadata/reference_map/manual_editions.json
- metadata/reference_map/pages.json
- metadata/reference_map/reference_positions.json
- logs/reference_map_run_manifest.json

Files modified:

- None of the protected stable production files were modified.

Validation performed:

- Executed builder script successfully.
- Executed reference map validator successfully.
- Verified protected stable file hashes remained unchanged.

Tests executed:

- python3 scripts/build_reference_map.py
- python3 scripts/reference_map/validate_reference_map.py

Known issues:

- reference_positions is intentionally empty pending authoritative grid annotation.
- No assignment or label transfer logic is implemented yet by design.

Remaining work:

- Implement authoritative reference position annotation workflow.
- Implement deterministic geometric matcher against reference positions.
- Implement confidence scoring, validation outputs, and manual review queue.
- Integrate published assignments into website and quiz projections.

Recommended next task:

- Milestone 2: Implement reference position authoring and validation module to populate metadata/reference_map/reference_positions.json with authoritative page/grid/code/description entries.

## Milestone 2 - Reference Position Authoring System

Date: 2026-07-07

Objective:

- Implement reusable reference position authoring infrastructure with immutable IDs, Reference Cell abstraction, provenance, lifecycle workflow, and strict validation.
- Preserve protected production baseline and backwards compatibility.

Architecture compliance:

- Conforms to docs/DATA_MODEL.md entity expectations for Manual Edition, Page, Reference Position, provenance fields, and lifecycle states.
- Conforms to docs/REFERENCE_MAP_DESIGN.md by introducing durable authoring workflow and validation-first infrastructure.
- Conforms to docs/LABEL_PROVENANCE_ANALYSIS.md by avoiding OCR-driven or heuristic label assignment.
- No extraction or assignment-matching redesign introduced.

Work completed:

- Added reusable authoring core under scripts/reference_map:
  - immutable ID allocation (RC- and RP- sequences)
  - Reference Cell creation with geometry model (bounds, centroid, rotation, margin, padding)
  - Reference Position creation linked to Reference Cell
  - lifecycle transitions: create, edit, review, approve, deprecate, archive
  - version snapshots per transition
  - append-only history per position and provenance on cells
- Added authoring CLI for deterministic workflow operations.
- Extended builder initialization to create authoring metadata files from config.
- Expanded validator to enforce:
  - unique IDs
  - duplicate grid and geometry checks
  - page-boundary validation
  - orphan detection
  - lifecycle enum validity
  - version/history integrity
  - cross-reference integrity between editions/pages/cells/positions
- Added dedicated schema validator and contract validator.
- Seeded deterministic representative sample (12 positions) across categories.

Files created:

- scripts/reference_map/authoring.py
- scripts/reference_map_authoring.py
- scripts/reference_map/validate_reference_map_schema.py
- scripts/reference_map/validate_reference_map_contract.py
- metadata/reference_map/id_registry.json
- metadata/reference_map/reference_cells.json

Files modified:

- assets/config/reference_map_config.json
- scripts/build_reference_map.py
- scripts/reference_map/validate_reference_map.py
- metadata/reference_map/reference_positions.json
- logs/reference_map_run_manifest.json

Files unchanged (protected baseline):

- scripts/extract_pipeline.py
- scripts/publish_dataset.py
- scripts/audit_extraction_completion.py
- scripts/check_rerun_determinism.py
- metadata/signs_consolidated.json
- website/data/signs.json

Validation performed:

- Builder run completed successfully.
- Authoring sample seed completed successfully.
- Schema validation passed.
- Contract validation passed.
- Integrity validator passed.
- Cross-reference and lifecycle/version checks passed.
- Protected file hashes verified unchanged.
- Website dataset compatibility smoke checks passed.

Tests executed:

- python3 scripts/build_reference_map.py
- python3 scripts/reference_map_authoring.py seed-sample --edition-id za-rtl-2026-01 --actor system
- python3 scripts/reference_map/validate_reference_map_schema.py
- python3 scripts/reference_map/validate_reference_map_contract.py
- python3 scripts/reference_map/validate_reference_map.py
- python3 inline integrity checks for sample coverage, categories, provenance completeness, and version alignment

Schema validation results:

- reference_map_schema_valid True

Contract validation:

- reference_map_contract_valid True

Known issues:

- Sample records are workflow validation records, not final authoritative full-manual map.
- Approval actor identity is currently a generic actor string; stronger reviewer identity policy can be added later.

Risks:

- If sample seeding is repeatedly run without operator intent, dataset volume will grow; future guardrails may require explicit run IDs or idempotency keys.

Technical debt introduced:

- Minimal. Validators are custom-code based rather than external JSON Schema engine; acceptable for current deterministic control but may later benefit from shared schema registry.

Remaining work:

- Implement Reference Position authoring update commands with selective edits and conflict-prevention policies.
- Implement review tooling for manual curation at scale.
- Prepare Milestone 3 deterministic matcher scaffolding (no assignment publication yet).

Recommended next milestone:

- Milestone 3: Implement deterministic geometry matcher scaffolding that consumes approved reference positions and produces candidate assignment artifacts only, with no final label publication yet.

## Milestone 3 - Deterministic Matcher Foundation

Date: 2026-07-07

Objective:

- Implement reusable deterministic matcher subsystem that reads approved Reference Positions and extracted sign instances and produces candidate assignments only.
- Do not publish final labels and do not modify production website dataset.

Work completed:

- Added deterministic matcher engine with page-identity-first matching and geometry scoring.
- Added matcher CLI entrypoint for sample runs.
- Added candidate assignment validator for schema and contract-level integrity checks.
- Extended reference_map config with matcher settings and output paths.
- Produced sample candidate assignment artifact (18 extracted signs, top-3 candidates each).
- Produced matcher run manifest for audit trail.

Files created:

- scripts/reference_map/matcher.py
- scripts/reference_map_match.py
- scripts/reference_map/validate_candidate_assignments.py
- metadata/reference_map/candidate_assignments_sample.json
- logs/reference_matcher_run_manifest.json

Files modified:

- assets/config/reference_map_config.json

Validation performed:

- Candidate assignment schema and integrity validation passed.
- Deterministic rerun validated using fixed timestamp and stable output hashes.
- Protected production component hashes verified unchanged.
- Website dataset compatibility smoke checks passed.

Tests executed:

- CLLT_FIXED_TIMESTAMP=2026-07-07T16:00:00Z python3 scripts/reference_map_match.py --sample-limit 18
- python3 scripts/reference_map/validate_candidate_assignments.py
- Determinism rerun with hash comparison of candidate and manifest outputs
- Python lint/error checks on new matcher modules

Remaining work:

- Implement assignment confidence model expansion using additional independent evidence layers.
- Implement validation enrichment and review-queue routing (without publishing).
- Implement full-run matcher execution controls and artifact partitioning by run id.

Recommended next milestone:

- Milestone 4: Candidate validation and review queue subsystem (still pre-publication), including conflict detection policies and auditable approval workflow integration.
