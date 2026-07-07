# CLLT Canonical Data Model

Document version: 1.0.0  
Snapshot at (UTC): 2026-07-07  
Prepared by: GitHub Copilot (GPT-5.3-Codex)

## Purpose

This document defines the single authoritative data contract for the CLLT platform.

All components must conform to this specification:

- extraction pipeline
- reference map builder
- validation pipeline
- website and quiz data publishers
- mobile and future API clients

## Scope

This contract covers the following entities:

- Manual Edition
- Page
- Reference Position
- Road Sign
- Image Asset
- Assignment
- Validation
- OCR Result
- Confidence
- Provenance
- Website Record
- Quiz Record

## Normative Rules

- MUST means mandatory.
- SHOULD means recommended unless a documented exception exists.
- MAY means optional.

## Global Conventions

### Field Naming

- Use snake_case for all field names.
- Use lowercase for enum values unless code standards require uppercase sign codes.
- IDs are stable strings, never numeric auto-increment exposed outside internal storage.

### Time and Date

- Use ISO 8601 UTC timestamps with trailing Z.
- Example: 2026-07-07T15:20:00Z

### Numeric Precision

- Normalized coordinates are floats in range [0, 1].
- Persist normalized coordinates with 6 decimal places.
- Confidence values are floats in range [0, 1] with 4 decimal places.

### Hashes

- Use sha256 for files and significant payload snapshots.
- Hex lowercase, 64 characters.

### Referential Integrity

- Foreign keys MUST refer to existing primary keys in the same dataset release.
- Orphan references are invalid.

## Entity Relationship Diagram (Text)

ASCII ER diagram:

ManualEdition (1) --- (N) Page
Page (1) --- (N) ReferencePosition
Page (1) --- (N) RoadSign
RoadSign (1) --- (1..N) ImageAsset
RoadSign (1) --- (N) Assignment
ReferencePosition (1) --- (N) Assignment
Assignment (1) --- (N) Validation
Assignment (1) --- (0..N) OCRResult
Assignment (1) --- (1) Confidence
Assignment (1) --- (1..N) Provenance
Assignment (1) --- (0..1) WebsiteRecord
Assignment (1) --- (0..1) QuizRecord

Key interpretation:

- One manual edition has many pages.
- Each page has many authoritative reference positions.
- Each extracted road sign belongs to one page.
- Assignment connects extracted signs to authoritative positions.

## Entity Specifications

## 1) Manual Edition

Purpose:

- Represents one official source manual edition used as the authoritative source of truth.

Primary key:

- edition_id

Required fields:

- edition_id
- source_pdf_path
- source_pdf_sha256
- source_pdf_filename
- publication_date
- status
- created_at
- model_version

Optional fields:

- supersedes_edition_id
- notes
- metadata

Foreign keys:

- supersedes_edition_id -> manual_edition.edition_id

Validation rules:

- edition_id MUST be globally unique.
- source_pdf_sha256 MUST be valid 64-char hex.
- status MUST be one of allowed values.

Allowed values:

- status: draft, active, deprecated, archived

Lifecycle:

- draft -> active -> deprecated -> archived

## 2) Page

Purpose:

- Represents one normalized page within a manual edition.

Primary key:

- page_id

Required fields:

- page_id
- edition_id
- page_number
- image_width
- image_height
- page_image_path
- page_image_sha256
- render_dpi
- normalization_profile
- created_at

Optional fields:

- page_label
- transform_matrix
- notes

Foreign keys:

- edition_id -> manual_edition.edition_id

Validation rules:

- page_number MUST be positive integer.
- image_width and image_height MUST be positive.
- page_number MUST be unique per edition_id.

Allowed values:

- normalization_profile: v1

Lifecycle:

- draft -> verified -> locked

## 3) Reference Position

Purpose:

- Defines one authoritative sign position on a page with official code and description.

Primary key:

- reference_position_id

Required fields:

- reference_position_id
- edition_id
- page_id
- page_number
- category
- grid_row
- grid_col
- norm_x
- norm_y
- norm_w
- norm_h
- official_code
- official_description
- reference_status
- created_at

Optional fields:

- source_region_fingerprint
- aliases
- notes

Foreign keys:

- edition_id -> manual_edition.edition_id
- page_id -> page.page_id

Validation rules:

- (edition_id, page_number, grid_row, grid_col) MUST be unique.
- official_code MUST match sign-code format rule.
- norm_x, norm_y, norm_w, norm_h MUST be in [0, 1].
- reference_status MUST be valid enum.

Allowed values:

- category: regulatory, warning, guidance, information, temporary, miscellaneous
- reference_status: draft, verified, disputed, deprecated

Lifecycle:

- draft -> verified -> deprecated
- disputed MAY transition back to verified after review.

## 4) Road Sign

Purpose:

- Represents one extracted sign candidate from pipeline output.

Primary key:

- road_sign_id

Required fields:

- road_sign_id
- extraction_run_id
- page_id
- page_number
- filename
- norm_x
- norm_y
- norm_w
- norm_h
- raw_x
- raw_y
- raw_w
- raw_h
- extraction_status
- extraction_confidence
- created_at

Optional fields:

- duplicate_group_id
- duplicate_of_road_sign_id
- warnings

Foreign keys:

- page_id -> page.page_id
- duplicate_of_road_sign_id -> road_sign.road_sign_id

Validation rules:

- filename MUST be unique within extraction_run_id.
- raw_w and raw_h MUST be positive integers.
- extraction_confidence MUST be in [0, 1].

Allowed values:

- extraction_status: ok, warning, rejected

Lifecycle:

- detected -> validated -> assigned

## 5) Image Asset

Purpose:

- Tracks image files used by signs, pages, website, and verification artifacts.

Primary key:

- image_asset_id

Required fields:

- image_asset_id
- road_sign_id
- asset_role
- file_path
- file_sha256
- width
- height
- format
- created_at

Optional fields:

- file_size_bytes
- source_file_path
- derivative_of_image_asset_id

Foreign keys:

- road_sign_id -> road_sign.road_sign_id
- derivative_of_image_asset_id -> image_asset.image_asset_id

Validation rules:

- file_sha256 MUST be valid hex sha256.
- file_path MUST exist at publish time.
- format MUST match extension and known type.

Allowed values:

- asset_role: crop, page, verification_overlay, contact_sheet, thumbnail
- format: png, jpg, webp

Lifecycle:

- generated -> published -> archived

## 6) Assignment

Purpose:

- Deterministic match between extracted road sign and authoritative reference position.

Primary key:

- assignment_id

Required fields:

- assignment_id
- assignment_run_id
- road_sign_id
- reference_position_id
- match_method
- geometric_iou
- center_distance
- size_ratio
- ambiguity_gap
- decision
- confidence_id
- created_at

Optional fields:

- alternate_candidates
- conflict_flags
- notes

Foreign keys:

- road_sign_id -> road_sign.road_sign_id
- reference_position_id -> reference_position.reference_position_id
- confidence_id -> confidence.confidence_id

Validation rules:

- road_sign_id MUST be unique in final published assignment set.
- reference_position_id MAY map to multiple road_sign_id only if explicitly allowed by policy.
- geometric_iou MUST be in [0, 1].

Allowed values:

- match_method: geometry_primary_v1
- decision: auto_accepted, manual_required, rejected

Lifecycle:

- candidate -> scored -> auto_accepted or manual_required -> finalized

## 7) Validation

Purpose:

- Stores rule-based validation outcomes for an assignment.

Primary key:

- validation_id

Required fields:

- validation_id
- assignment_id
- rule_id
- rule_version
- result
- severity
- checked_at

Optional fields:

- observed_value
- expected_value
- message

Foreign keys:

- assignment_id -> assignment.assignment_id

Validation rules:

- rule_id MUST be deterministic and versioned.
- result MUST be valid enum.

Allowed values:

- result: pass, fail, warn, skipped
- severity: info, low, medium, high, critical

Lifecycle:

- generated per assignment run, immutable after write.

## 8) OCR Result

Purpose:

- Secondary verification evidence for assignments, never primary label source.

Primary key:

- ocr_result_id

Required fields:

- ocr_result_id
- assignment_id
- ocr_engine
- ocr_engine_version
- extracted_text
- code_candidate
- score
- consistency_with_reference
- created_at

Optional fields:

- bounding_boxes
- raw_output
- language

Foreign keys:

- assignment_id -> assignment.assignment_id

Validation rules:

- score MUST be in [0, 1].
- consistency_with_reference MUST be computed from reference_position.official_code comparison.

Allowed values:

- consistency_with_reference: consistent, inconsistent, inconclusive

Lifecycle:

- generated with assignment run, may be regenerated under new ocr_engine_version.

## 9) Confidence

Purpose:

- Canonical confidence object for assignment scoring and thresholds.

Primary key:

- confidence_id

Required fields:

- confidence_id
- assignment_id
- total_score
- geometry_component
- ambiguity_component
- ocr_component
- extraction_component
- threshold_profile_id
- computed_at

Optional fields:

- override_score
- override_reason

Foreign keys:

- assignment_id -> assignment.assignment_id

Validation rules:

- total_score and all components MUST be in [0, 1].
- components SHOULD sum to total_score according to threshold profile.

Allowed values:

- threshold_profile_id: strict_v1

Lifecycle:

- computed -> optionally overridden by approved reviewer policy

## 10) Provenance

Purpose:

- Full audit trail proving authoritative origin and transformation chain.

Primary key:

- provenance_id

Required fields:

- provenance_id
- assignment_id
- authoritative_source_type
- authoritative_source_path
- authoritative_source_version
- source_record_pointer
- transformation_step
- transformation_version
- actor_type
- created_at

Optional fields:

- actor_id
- reviewer_notes
- change_ticket

Foreign keys:

- assignment_id -> assignment.assignment_id

Validation rules:

- At least one provenance record MUST exist per assignment.
- authoritative_source_path MUST resolve in the repository or approved external registry.

Allowed values:

- authoritative_source_type: official_pdf, reference_map, legend_dictionary, reviewer_decision
- actor_type: system, reviewer

Lifecycle:

- append-only; corrections create new record, never destructive edits.

## 11) Website Record

Purpose:

- Frontend-serving record for library browsing and filtering.

Primary key:

- website_record_id

Required fields:

- website_record_id
- assignment_id
- filename
- page_number
- code
- description
- category
- validation_status
- confidence
- provenance_summary

Optional fields:

- badge_labels
- duplicate_of
- duplicate_group_size
- render_metadata

Foreign keys:

- assignment_id -> assignment.assignment_id

Validation rules:

- code and description MUST come from finalized assignment.
- confidence MUST match confidence.total_score or approved override.

Allowed values:

- validation_status: auto_accepted, reviewer_verified, pending_review

Lifecycle:

- generated at publish -> replaced atomically on each platform data release

## 12) Quiz Record

Purpose:

- Quiz-optimized projection of validated records.

Primary key:

- quiz_record_id

Required fields:

- quiz_record_id
- assignment_id
- filename
- code
- description
- category
- quiz_status

Optional fields:

- distractor_pool
- difficulty
- confidence

Foreign keys:

- assignment_id -> assignment.assignment_id

Validation rules:

- quiz records MUST only include assignments meeting quiz threshold policy.

Allowed values:

- quiz_status: active, excluded_low_confidence, excluded_unverified

Lifecycle:

- regenerated from finalized assignments per publish release.

## Cross-Entity Validation Rules

Global constraints:

- Every road_sign MUST have at least one image_asset with asset_role=crop.
- Every finalized assignment MUST have:
  - one confidence record
  - one or more provenance records
  - one or more validation records
- Every low-confidence assignment MUST appear in manual review queue.
- Every website record and quiz record MUST be traceable to assignment_id.

Sign-code format rule:

- Regex: ^[A-Z]{1,4}[0-9]{1,3}(\.[0-9]{1,2})?$
- UNKNOWN placeholders are forbidden in finalized assignments.

## JSON Schema Examples

Note: these are canonical examples for implementation. They are illustrative and may be split into per-entity schema files during implementation.

## Example: Assignment (Draft 2020-12 style)

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "cllt.assignment.schema.v1",
  "type": "object",
  "required": [
    "assignment_id",
    "assignment_run_id",
    "road_sign_id",
    "reference_position_id",
    "match_method",
    "geometric_iou",
    "center_distance",
    "size_ratio",
    "ambiguity_gap",
    "decision",
    "confidence_id",
    "created_at"
  ],
  "properties": {
    "assignment_id": {"type": "string", "minLength": 1},
    "assignment_run_id": {"type": "string", "minLength": 1},
    "road_sign_id": {"type": "string", "minLength": 1},
    "reference_position_id": {"type": "string", "minLength": 1},
    "match_method": {"type": "string", "enum": ["geometry_primary_v1"]},
    "geometric_iou": {"type": "number", "minimum": 0, "maximum": 1},
    "center_distance": {"type": "number", "minimum": 0},
    "size_ratio": {"type": "number", "exclusiveMinimum": 0},
    "ambiguity_gap": {"type": "number", "minimum": 0},
    "decision": {"type": "string", "enum": ["auto_accepted", "manual_required", "rejected"]},
    "confidence_id": {"type": "string", "minLength": 1},
    "created_at": {"type": "string", "format": "date-time"},
    "alternate_candidates": {"type": "array", "items": {"type": "string"}},
    "conflict_flags": {"type": "array", "items": {"type": "string"}},
    "notes": {"type": "string"}
  },
  "additionalProperties": false
}
```

## Example: Reference Position

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "cllt.reference_position.schema.v1",
  "type": "object",
  "required": [
    "reference_position_id",
    "edition_id",
    "page_id",
    "page_number",
    "category",
    "grid_row",
    "grid_col",
    "norm_x",
    "norm_y",
    "norm_w",
    "norm_h",
    "official_code",
    "official_description",
    "reference_status",
    "created_at"
  ],
  "properties": {
    "reference_position_id": {"type": "string"},
    "edition_id": {"type": "string"},
    "page_id": {"type": "string"},
    "page_number": {"type": "integer", "minimum": 1},
    "category": {"type": "string", "enum": ["regulatory", "warning", "guidance", "information", "temporary", "miscellaneous"]},
    "grid_row": {"type": "integer", "minimum": 1},
    "grid_col": {"type": "integer", "minimum": 1},
    "norm_x": {"type": "number", "minimum": 0, "maximum": 1},
    "norm_y": {"type": "number", "minimum": 0, "maximum": 1},
    "norm_w": {"type": "number", "minimum": 0, "maximum": 1},
    "norm_h": {"type": "number", "minimum": 0, "maximum": 1},
    "official_code": {"type": "string", "pattern": "^[A-Z]{1,4}[0-9]{1,3}(\\.[0-9]{1,2})?$"},
    "official_description": {"type": "string", "minLength": 1},
    "reference_status": {"type": "string", "enum": ["draft", "verified", "disputed", "deprecated"]},
    "created_at": {"type": "string", "format": "date-time"}
  },
  "additionalProperties": false
}
```

## Example: Website Record

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "cllt.website_record.schema.v1",
  "type": "object",
  "required": [
    "website_record_id",
    "assignment_id",
    "filename",
    "page_number",
    "code",
    "description",
    "category",
    "validation_status",
    "confidence",
    "provenance_summary"
  ],
  "properties": {
    "website_record_id": {"type": "string"},
    "assignment_id": {"type": "string"},
    "filename": {"type": "string"},
    "page_number": {"type": "integer", "minimum": 1},
    "code": {"type": "string", "pattern": "^[A-Z]{1,4}[0-9]{1,3}(\\.[0-9]{1,2})?$"},
    "description": {"type": "string", "minLength": 1},
    "category": {"type": "string"},
    "validation_status": {"type": "string", "enum": ["auto_accepted", "reviewer_verified", "pending_review"]},
    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
    "provenance_summary": {"type": "string", "minLength": 1},
    "duplicate_of": {"type": "string"},
    "duplicate_group_size": {"type": "integer", "minimum": 1}
  },
  "additionalProperties": false
}
```

## Naming Conventions

ID patterns:

- edition_id: za-rtl-YYYY-MM
- page_id: edition_id + -p + page_number
- reference_position_id: edition_id + -p{page}-r{row}-c{col}
- road_sign_id: run_id + -p{page}-n{ordinal}
- assignment_id: assign-{zero_padded_counter}

File naming:

- Extracted images: page{page}_unknown_{index}.png until assigned.
- Published images retain stable extraction filename unless explicit migration policy is approved.

## Versioning Strategy

Contract versioning:

- Semantic versioning for this data model: major.minor.patch.
- Major bump for breaking schema changes.
- Minor bump for additive backward-compatible fields.
- Patch for clarifications and non-structural fixes.

Dataset versioning:

- Every publish produces dataset_release_id.
- Each record includes contract_version and dataset_release_id.

Algorithm versioning:

- matching_algorithm_version and threshold_profile_id MUST be stored in provenance.

## Backwards Compatibility Strategy

Compatibility policy:

- Additive fields are allowed if optional and documented.
- Required-field additions require major version bump.
- Field removal or rename requires major version bump and migration guide.

Migration support:

- Maintain compatibility adapters for one prior major version.
- Publish migration map for renamed IDs or enum values.

Deprecation policy:

- Deprecate fields for at least one minor cycle before removal.

## Future Extensibility

Planned extensions:

- multilingual descriptions
- region-specific variants
- richer category taxonomy
- per-sign legal metadata references
- API-first transport projection formats

Extension rules:

- Never overload existing field semantics.
- Add extension fields with clear namespace or explicit schema updates.
- Keep provenance complete for all new automated steps.

## Conformance Requirements

A component is conformant only if:

- it reads and writes entities using this contract
- it enforces required field and enum validation
- it preserves referential integrity
- it records provenance for all automated assignments
- it respects OCR-secondary policy
- it passes deterministic rerun checks for identical inputs

## Contract Authority

This document is the platform data contract authority.

All future implementations MUST conform to this specification unless an approved contract version update is merged into this file.
