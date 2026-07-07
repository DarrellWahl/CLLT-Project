# Label Provenance Analysis

Document version: 1.0.0  
Snapshot at (UTC): 2026-07-07  
Prepared by: GitHub Copilot (GPT-5.3-Codex)

## Objective

Design an auditable label-assignment process before any code or description transfer.

This analysis answers:

1. Which datasets already exist in the repository.
2. Which files contain verified sign codes.
3. Which files contain verified descriptions.
4. Which files contain image-to-code mappings.
5. Whether historical outputs can be deterministically matched to current extraction.
6. Whether geometric position on PDF pages can be the primary matching key.
7. Whether OCR should be secondary verification only.

No label transfer was performed in this step.

## Current Extraction Baseline

- Current extracted sign rows: 1090
- Current extracted sign images in website set: 1090
- Current code coverage in active dataset: 0 of 1090
- Current description coverage in active dataset: 0 of 1090
- Current extraction metadata includes page and geometry fields for all 1090 rows.

Primary active extraction files:

- [metadata/page_1_signs.json](../metadata/page_1_signs.json)
- [metadata/page_2_signs.json](../metadata/page_2_signs.json)
- [metadata/page_3_signs.json](../metadata/page_3_signs.json)
- [metadata/page_4_signs.json](../metadata/page_4_signs.json)
- [website/data/signs.json](../website/data/signs.json)
- [metadata/signs_consolidated.json](../metadata/signs_consolidated.json)

## Repository Datasets Relevant To Labeling

### Legend and code-description dictionaries

- [output/sign_legend.json](../output/sign_legend.json): 168 rows with code and description.
- [output/sign_legend_clean.json](../output/sign_legend_clean.json): 168 rows with code and description.

### Historical mapping outputs

- [output/sign_mappings_clean.json](../output/sign_mappings_clean.json): 89 rows with filename, page, code, description.
- [output/sign_mappings.json](../output/sign_mappings.json): 1090 rows, currently empty code and description.
- [output/sign_mappings_complete.json](../output/sign_mappings_complete.json): 1090 rows, currently empty code and description.
- [output/sign_mappings_all.json](../output/sign_mappings_all.json): 1090 rows, code populated with UNKNOWN values only, no descriptions.

### Historical geometry for old mapped filenames

- [output/signs_metadata.csv](../output/signs_metadata.csv): 89 rows with page and geometry for pageX_sign_YYY naming.

### Active extraction geometry and quality fields

- [metadata/page_1_signs.json](../metadata/page_1_signs.json)
- [metadata/page_2_signs.json](../metadata/page_2_signs.json)
- [metadata/page_3_signs.json](../metadata/page_3_signs.json)
- [metadata/page_4_signs.json](../metadata/page_4_signs.json)

### Primary source document

- [assets/pdf/Road Traffic Signs.pdf](../assets/pdf/Road Traffic Signs.pdf)

## Which Files Contain Verified Sign Codes

Highest-confidence verified code list:

- [output/sign_legend_clean.json](../output/sign_legend_clean.json) (168 codes)
- [output/sign_legend.json](../output/sign_legend.json) (168 codes)

Conditionally verified or partially verified codes:

- [output/sign_mappings_clean.json](../output/sign_mappings_clean.json) (89 mapped codes tied to old filename namespace)

Not verified for official assignment:

- [output/sign_mappings_all.json](../output/sign_mappings_all.json) uses UNKNOWN placeholders.
- [output/sign_mappings.json](../output/sign_mappings.json) currently empty codes.
- [output/sign_mappings_complete.json](../output/sign_mappings_complete.json) currently empty codes.
- [website/data/signs.json](../website/data/signs.json) currently empty codes.

## Which Files Contain Verified Descriptions

Highest-confidence verified descriptions:

- [output/sign_legend_clean.json](../output/sign_legend_clean.json)
- [output/sign_legend.json](../output/sign_legend.json)

Conditionally verified descriptions:

- [output/sign_mappings_clean.json](../output/sign_mappings_clean.json) (89 rows only)

Not verified for current assignment:

- [output/sign_mappings_all.json](../output/sign_mappings_all.json) has no descriptions.
- [output/sign_mappings.json](../output/sign_mappings.json) has no descriptions.
- [output/sign_mappings_complete.json](../output/sign_mappings_complete.json) has no descriptions.
- [website/data/signs.json](../website/data/signs.json) has no descriptions.

## Which Files Contain Image-To-Code Mappings

Available mapping files:

- [output/sign_mappings_clean.json](../output/sign_mappings_clean.json): image filename to code mapping for 89 historical images.
- [output/sign_mappings_all.json](../output/sign_mappings_all.json): image filename to UNKNOWN placeholder code for 1090 rows.
- [output/sign_mappings.json](../output/sign_mappings.json): mapping structure exists but code fields empty.
- [output/sign_mappings_complete.json](../output/sign_mappings_complete.json): mapping structure exists but code fields empty.

Current active extracted images use pageX_unknown_YYY naming and are tracked in:

- [metadata/page_1_signs.json](../metadata/page_1_signs.json)
- [metadata/page_2_signs.json](../metadata/page_2_signs.json)
- [metadata/page_3_signs.json](../metadata/page_3_signs.json)
- [metadata/page_4_signs.json](../metadata/page_4_signs.json)

## Can Historical Outputs Be Deterministically Matched To Current Extraction

Short answer: not directly from current repository state.

Evidence:

- Historical clean mapping rows: 89
- Current extracted rows: 1090
- Filename overlap between historical clean mapping and current extraction: 0
- Theoretical maximum coverage from historical clean mapping even if fully recoverable: 8.17 percent
- IoU geometry matching from historical [output/signs_metadata.csv](../output/signs_metadata.csv) to current extraction boxes: 0 matches even at IoU >= 0.20

Key reason:

- Historical [output/signs_metadata.csv](../output/signs_metadata.csv) geometry represents a different extraction target profile (small row-like strips near y around 9323 to 9359), while current extraction boxes are much larger sign crops spread broadly across the page.
- This indicates incompatible extraction products, not a simple rename difference.

Conclusion:

- Deterministic direct transfer from historical mappings to current extraction is not currently reliable.

## Can Geometric Position Be The Primary Matching Key

Yes, with conditions.

Geometric position should be the primary deterministic key only when all of the following are true:

- Same source page image set and stable dimensions.
- Same extraction region policy for each page.
- Matching is done in normalized page coordinates.
- Candidate uniqueness constraints are enforced.
- Matching thresholds are explicit and versioned.

Recommended primary key format:

- page
- normalized center x, normalized center y
- normalized width, normalized height
- deterministic tie-break on filename order

Recommended deterministic match rules:

- Primary: IoU threshold in normalized space.
- Secondary deterministic guard: center distance threshold.
- Reject ambiguous cases where two candidates are too close in score.

Given current evidence, geometry can be primary, but only against a truly authoritative reference geometry set derived from the official manual and validated once.

## Should OCR Be Secondary Verification Only

Yes.

Recommendation:

- OCR should not be the primary mapping method.
- OCR should be secondary evidence used to validate or down-rank geometric matches.

Rationale:

- OCR is sensitive to crop quality, symbol complexity, blur, and small text.
- Repository configuration already reflects this caution with OCR disabled in extraction config for primary flow.
- OCR is suitable for confidence adjustment and manual-review prioritization, not initial authoritative assignment.

## Authoritative Source Ranking

Confidence scale:

- 5: authoritative and directly assignable
- 4: authoritative but requires deterministic transform
- 3: useful but partial or unverified linkage
- 2: weak for direct assignment
- 1: non-authoritative for final labeling

| Source | Contains Official Code | Contains Official Description | Contains Image Mapping | Confidence | Notes |
|---|---|---|---|---:|---|
| [assets/pdf/Road Traffic Signs.pdf](../assets/pdf/Road Traffic Signs.pdf) | Yes | Yes | Yes (visually) | 5 | Primary legal/source authority; requires deterministic extraction and validation pipeline. |
| [output/sign_legend_clean.json](../output/sign_legend_clean.json) | Yes | Yes | No | 4 | Strong code-description dictionary extracted from manual legend; no image linkage. |
| [output/sign_legend.json](../output/sign_legend.json) | Yes | Yes | No | 4 | Same role as legend clean; cross-check source. |
| [output/sign_mappings_clean.json](../output/sign_mappings_clean.json) | Yes (89) | Yes (89) | Yes (89) | 3 | Valuable historical subset, but currently disconnected from active extraction namespace and geometry. |
| [output/signs_metadata.csv](../output/signs_metadata.csv) | No | No | Geometry for 89 old filenames | 2 | Historical geometry does not align with current extraction boxes. |
| [metadata/page_1_signs.json](../metadata/page_1_signs.json) and peers | No | No | Yes | 3 | Authoritative for current crop geometry and image identity only, not labels. |
| [output/sign_mappings_all.json](../output/sign_mappings_all.json) | UNKNOWN only | No | Yes | 1 | Placeholder-only mapping; not authoritative for official labels. |
| [output/sign_mappings.json](../output/sign_mappings.json) | Empty | Empty | Yes | 1 | Structure exists, labels absent. |
| [output/sign_mappings_complete.json](../output/sign_mappings_complete.json) | Empty | Empty | Yes | 1 | Structure exists, labels absent. |
| [website/data/signs.json](../website/data/signs.json) | Empty | Empty | Yes | 1 | Active serving dataset; currently unlabeled. |

## Recommended Deterministic Mapping Strategy

### Stage A: Build authoritative reference map

- Derive an authoritative reference table from the official manual pages:
  - page
  - normalized sign geometry
  - official code
  - official description
  - provenance pointer to manual region
- Use [output/sign_legend_clean.json](../output/sign_legend_clean.json) as the code-description canonical dictionary.
- Keep this table versioned and immutable once approved.

### Stage B: Deterministic geometric matching

- Match each current extracted sign from [metadata/page_1_signs.json](../metadata/page_1_signs.json) through [metadata/page_4_signs.json](../metadata/page_4_signs.json) to the authoritative reference by page and normalized geometry.
- Assign labels only if deterministic uniqueness criteria pass.
- Record per-assignment provenance fields:
  - source file
  - source row id
  - match method
  - geometric score
  - OCR verification score (if used)

### Stage C: Secondary verification and review queue

- Run OCR only as verification.
- Compute final assignment confidence using weighted deterministic components.
- Automatically queue low-confidence or ambiguous assignments for manual review.

### Stage D: Immutable audit artifacts

- Save all assignments and decisions to dedicated audit outputs in logs or metadata with run id, tool version, and thresholds.
- Keep deterministic rerun checks as a release gate.

## Estimated Automatic Match Coverage And Manual Review

Based on current repository state only:

- Deterministically auto-matchable now with high confidence: 0 percent
- Upper bound from disconnected historical clean mapping: 8.17 percent
- Estimated manual review now: 91.83 to 100 percent

After building an authoritative geometry reference table from the manual:

- Expected deterministic automatic assignment: 85 to 95 percent
- Expected manual review queue: 5 to 15 percent

These are planning estimates and must be replaced with measured rates after first calibrated run.

## Risks Of False Mappings

- Geometry aliasing where nearby signs have similar sizes and positions.
- Legacy namespace confusion between pageX_sign_YYY and pageX_unknown_YYY.
- OCR hallucinations or partial text causing wrong code suggestions.
- Cross-page accidental matches if page key is omitted.
- Drift from extraction parameter changes between runs.
- Silent overrides if multiple sources are merged without priority rules.

Mitigations:

- Hard page constraint in matching.
- Normalized geometry thresholds and ambiguity rejection.
- Strict source precedence rules.
- Mandatory provenance record per assignment.
- Mandatory manual review for low confidence and unresolved ambiguity.

## Formal Completion Definition For This Phase

This phase is finished only when all are true:

- 100 percent of extracted signs have an image.
- 100 percent have the correct official code.
- 100 percent have the correct official description.
- Every label has traceable provenance to an authoritative source.
- Every automatic assignment includes a confidence score.
- Every low-confidence assignment is queued for manual review.
- The full extraction and labeling pipeline reruns from the original PDF and reproduces the same results.

## Decision

Do not start automatic label transfer yet.

Next required step is to build and approve the authoritative reference map and deterministic match thresholds, then implement assignment with full provenance and review-queue outputs.
