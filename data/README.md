# B13 training data layout

The corpus and data sources now live under `data/sources/`, `data/raw/`, and
`repositories/`. Named symlinks under `data/processed/`, `data/evals/`, and
`data/imports/` provide stable views of those sources without creating more
copies.

## Canonical views

| B13 path | Source | Purpose |
| --- | --- | --- |
| `raw/cve/cvelistV5/` | `repositories/github/CVEProject/cvelistV5/` | Raw CVE JSON records, organized by year (1999–2026). |
| `raw/cve/reference-ingest/` | `repositories/github/CVEProject/cve-reference-ingest-data/` | Raw CVE reference material. |
| `processed/cve-sft/` | `sources/corpora/datasets-workbench/processed/vulnerabilities/` | Derived CVE/vulnerability SFT alternatives and train/validation splits. |
| `processed/cve-sft-canonical.parquet` | `sources/corpora/datasets-workbench/processed/vulnerabilities/cve_sft_enhanced_v3.parquet` | Single CVE-SFT candidate currently selected by the source catalog. |
| `processed/agent-skills-sft/` | `sources/corpora/datasets-workbench/processed/agent_skills/` | Agent-skill SFT data. |
| `processed/code-security-sft/` | `sources/corpora/datasets-workbench/processed/code_security/` | Code-security SFT data. |
| `processed/redteam-pentest-sft/` | `sources/corpora/datasets-workbench/processed/redteam_pentest/` | Multi-turn pentest SFT data. |
| `processed/general-sft/` | `sources/corpora/datasets-workbench/processed/data/` | General train/validation SFT split. |
| `processed/master-sft-cleaned.parquet` | `sources/corpora/datasets-workbench/processed/master_sft_cleaned_unified.parquet` | Cleaned unified SFT artifact. |
| `processed/master-sft-enhanced.parquet` | `sources/corpora/datasets-workbench/processed/master_sft_enhanced_unified.parquet` | Enhanced unified SFT artifact. |
| `evals/repo-security-grades/` | `sources/corpora/datasets-workbench/evals/repo_security_grades/` | Evaluation data; keep out of training unless intentionally selected. |

`sources/corpora/datasets-workbench/` is the canonical working tree because it
contains raw, processed, evaluation, documentation, and build-script areas.
`sources/corpora/datasets-hf-export/` is the Hugging Face-style export with
`sft/` and `evals/` paths. Compatibility symlinks retain the former workspace
paths `datasets/` and `DATASETS/`.

## Inventory and deduplication findings

- `datasets/`, `DATASETS/`, and the former `training_environment/datasets/`
  tree contained 23 tabular artifacts verified byte-identical across all three
  trees using SHA-256. The two `dataset_catalog.json` files were also
  byte-identical.
- The duplicate `training_environment/datasets/` copy was removed after
  verifying every one of its 23 files matched `DATASETS/` at the same relative
  path. It is now a symlink through the `DATASETS/` compatibility alias, so
  existing training-script paths still resolve.
- Duplicate tabular files remain in `datasets/processed/` and `DATASETS/sft/`.
  They serve different staging/export layouts and existing scripts refer to
  both; those copies have not been removed.
- `DATASETS/` additionally contains skill-library and other material not in the
  canonical `datasets/processed/` tree. It is not classified as training data
  by default.
- The two corpus trees and loose source files were moved under `b13_agent/`.
  Existing workspace-root names remain symlinks to preserve script paths.
  Several scripts/configurations refer to both corpus layouts; keep both until
  those consumers are migrated and verified.
- The enhanced master contains 16,874 rows; the cleaned master contains 16,594.
  The README's 16,594 claim corresponds to the cleaned artifact, while the JSON
  catalog's 16,874 claim corresponds to the enhanced artifact.
- Metadata inspection verified 10,000 rows for each named CVE candidate,
  5,591 code-security rows, 1,003 red-team rows, and 284 standalone
  agent-skill rows. The general and domain train/validation splits have no
  overlapping `id` keys (CVE uses `cve_id`); see `catalog.json` and run the
  metadata inspector to reproduce the check.
- The four CVE SFT variants contain the same 10,000 unique `cve_id` values.
  They are alternative versions, not four additive datasets. The
  `cve_sft_enhanced_v3.parquet` is exposed as the current single candidate
  because that is the variant selected by the existing dataset catalog; compare
  quality and provenance before final export.
- The general split files contain 14,934 train and 1,660 validation rows and
  exactly cover the 16,594-row cleaned master. They do not cover 280 rows in
  the enhanced master. The enhanced master and cleaned split set should not be
  mixed as if they represented the same version.
- The standalone agent-skill artifact and its split files do not match:
  18 standalone IDs are absent from the splits and 14 split IDs are absent
  from the standalone artifact. Reconcile this lineage before choosing one.
- The CSV and Parquet evaluation exports each contain 130,173 rows. They are
  separate encodings; do not add their row counts as if they were distinct
  examples. Keep evaluation data separate from training.
- The raw `blackhat_ai.json` has 1,003 conversations, the same record count as
  the red-team Parquet export. Role counts match, but the records do not match
  under a simple role-preserving conversion with an optional leading system
  message. Treat these as distinct/related sources until the transformation is
  reviewed; do not stack them by default.
- The code-security `enhanced_reasoning` and `enhanced_v2` files each contain
  5,591 rows with distinct message payloads. Their sets of `(filename, ability)`
  metadata pairs match, but they have no common stable row ID; treat them as
  alternative transformations until provenance is verified, not as proven
  independent additions.
- `processed/code_security/train-00000-of-00001.parquet` is a separate 5,591-row
  prompt-format artifact with columns `prompt` and `reward_model`. It is not the
  same schema or split lineage as the 5,031/560-row ChatML files; it remains an
  alternative rather than being silently combined.
- Six loose CVE CSVs are grouped under `raw/csv/cve/`. Their schemas represent
  different sources. A multiline-aware audit parsed all records with no
  malformed row widths: NVD Cybersecurity Dataset 337,705; CPE 269,236;
  `cve_combined.csv` 119,864; `cve_dataset.csv` 39,810; KEV 1,739; and
  CVE fix pairs 104 rows for 52 CVE IDs. Physical newline counts are not row
  counts for files containing embedded newlines.
- All 337,705 NVD CSV CVE IDs and every ID in the other CVE-ID CSV tables occur
  in the local 404,333-record CVE List v5 checkout. These CSV tables overlap
  the source list and each other; treat them as enrichment or validation
  sources, not additive independent examples. Do not concatenate them without
  joining on normalized CVE IDs and retaining per-field provenance.
- `final_dataset.csv` (370,622,156 bytes; `label,text`) parses to 515,345
  records, but remains unclassified and excluded pending source, license, and
  content review. The unrelated banknote classification table is filed under
  `excluded/` and is not a training candidate.
- `data.zip` and `toolset.zip` remain unextracted under
  `raw/archives/unreviewed/`. The `data.zip` member names identify participant
  user-action logs; exclude them pending privacy, consent, source, and license
  review. `toolset.zip` contains a `.env`-named archive entry and has not been
  opened.
- PDF papers and guidance documents are reference material, not training
  examples. The included shell-command paper describes a separate human
  participant dataset; no source dataset or rights grant is established here.
  Do not train on the paper text itself.
- The CVE List v5 checkout contains 404,333 unique CVE IDs (385,869 `PUBLISHED`,
  18,464 `REJECTED`). The [CVE Program Terms of
  Use](https://www.cve.org/Legal/TermsOfUse) grant rights to reproduce and
  prepare derivative works of CVE, provided copies reproduce MITRE's copyright
  designation and that license. CNA contributions and external references may
  have additional rights or terms and need separate review before
  redistribution. The raw-source audit counts published records with English
  descriptions and data-field completeness. The dataset export README is
  MIT-licensed, but that metadata does not establish rights for every
  upstream record.
- `repositories/github/` contains 16 clones. Their source code, schemas, and
  policy documents are reference material rather than SFT by default. Only
  five clones have a root license file (four CC0, one MIT); a code license does
  not automatically cover all repository data, PDFs, or third-party content.
- The `SSH-Shell-Attacks` repository describes 233,035 session records and
  processed feature variants. The repository has an MIT license, but its
  dataset-specific rights and privacy terms are not established. Session
  records may contain credentials or personal identifiers, so this data is
  excluded and must not be inspected or transformed until the owner provides a
  pre-scrubbed dataset and authorization.
- Existing CVE-SFT rows cover 10,000 CVE IDs that are also present in the raw
  CVE List. The auditor checks CVE identifiers mentioned in every registered
  train/validation split as well; exclude those IDs from any raw-derived CVE
  training examples to keep the holdout boundary intact. It found 380 CVE IDs
  mentioned across both train and validation messages, even though registered
  row keys do not overlap. The training export builder now drops train examples
  mentioning any CVE ID found in validation.
- Row counts and key overlap are now checked, but schema meaning, content
  quality, licensing, and semantic train/validation leakage still need review.
- The metadata validator checked every catalogued ChatML/`messages` artifact:
  there are no null or empty message lists, malformed message entries, or
  empty message contents in those files. This is a structural check only, not
  a judgment of the examples' correctness or suitability.

## CVE repositories versus CVE datasets

`cvelistV5/` is the raw CVE-record source. `cve-reference-ingest-data/` is
reference material. The CVEProject Git clones are grouped under
`repositories/github/CVEProject/`; code and policy repositories are references,
not model-training corpora. The CVE SFT alternatives under `processed/cve-sft/`
are derived training artifacts and remain separate from raw records. This
keeps one discoverable CVE collection without mixing source records,
references, code, and instruction-tuning examples into one undifferentiated
file.

## Local CVE record candidate

`exports/cve-record-summary/` is a generated, local-only ChatML candidate
prepared from the pinned CVE List v5 revision recorded in its manifest. It
contains 338,369 training and 37,513 validation examples. Only `PUBLISHED`
records with English CNA descriptions are included; rejected records and
9,987 CVE IDs already mentioned in registered SFT data are excluded. CVE IDs
are split as indivisible groups using a deterministic SHA-256 assignment.

The export includes an attribution file for MITRE's CVE terms. It does not
include external reference contents. CNA-contributed content may have
additional terms, so the attribution does not establish redistribution rights
for every field. Review the CVE Program terms and source-specific rights before
uploading or distributing the export.

Affected-product and version lists are capped per record; exact omission counts
are in `exports/cve-record-summary/manifest.json`. The candidate has not yet
been checked against the pinned tokenizer's 2,048-token training limit, mixed
with the registered SFT export, or approved for training. Keep it local until
those checks and the data-mixture decision are complete.

## Before a training export

Validate each selected artifact's schema and row count; deduplicate records
across the selected SFT sources; detect overlap between training and
validation; record source revision, license, transformations, and hashes; and
export only the explicitly selected datasets. Evaluation data must stay
separate from training unless deliberately reclassified.

Rebuild the local CVE candidate with:

```bash
./b13_agent/.venv/bin/python ./b13_agent/training/scripts/prepare_cve_record_sft.py
```

This command reads the registered SFT splits and the local CVE List checkout,
writes generated files only under `data/exports/cve-record-summary/`, and
reports row counts without printing CVE descriptions.

## Reproducing metadata checks

From the workspace root:

```bash
./b13_agent/.venv/bin/python -m pip install -r ./b13_agent/requirements-data.txt
./b13_agent/.venv/bin/python ./b13_agent/training/scripts/inspect_dataset_metadata.py
./b13_agent/.venv/bin/python ./b13_agent/training/scripts/audit_raw_sources.py
```

The inspector reports Parquet/CSV schemas and row counts, checks train/validation
key overlap for the registered split sets, and prints no sample rows.
The raw-source auditor uses multiline-aware CSV parsing, checks row widths and
CVE-ID overlap against the local CVE List and existing CVE SFT splits, and
records CVE JSON field completeness without emitting source record text. Its
machine-readable report is `data/interim/raw-source-audit.json`.
