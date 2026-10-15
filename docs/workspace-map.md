# Workspace organization map

Bulk data and source repositories have been physically consolidated under
`b13_agent/`. Workspace-root symlinks preserve the former paths used by scripts
and sibling repositories.

## Data and research assets

| Category | Organized location |
| --- | --- |
| Canonical processed/raw dataset workbench | `data/sources/corpora/datasets-workbench/` |
| Unified CVE collection | `data/cve/` |
| Hugging Face-style dataset export and skills bundle | `data/sources/corpora/datasets-hf-export/` |
| Kaggle dataset upload staging copy | `data/sources/cloud-staging/kaggle-dataset/` |
| Raw CVE JSON and CVE references | `repositories/github/CVEProject/cvelistV5/` and `cve-reference-ingest-data/` |
| Standalone HF cache snapshots | `data/raw/huggingface-cache/` |
| CVE CSVs (`cpe`, combined, dataset, fix pairs, KEV, NVD) | `data/raw/csv/cve/` |
| KDD network-security benchmark | `data/raw/csv/security-benchmarks/` |
| Unidentified `final_dataset.csv` | `data/raw/csv/unclassified/` |
| Unrelated banknote-classification table | `data/excluded/non-b13-benchmarks/` |
| `data.zip`, `toolset.zip` | `data/raw/archives/unreviewed/`; neither archive extracted |
| CVE Data Model PDFs | `docs/references/cdm/` |
| CISA/CVD policy and vulnerability report | `docs/references/cisa/` |
| Shell-command dataset paper | `docs/papers/` |
| CVSS/CVE exploratory notebooks | `training/notebooks/exploratory/` |
| Kaggle notebook package | `training/notebooks/cloud/kaggle/` |
| Skill library | `agent_skills/library/skills/` |
| Git clones | `repositories/github/CVEProject/` and `repositories/github/research/` |

### Loose CSV files

`data/raw/csv/cve/` contains `cpe.csv`, `cve_combined.csv`, `cve_dataset.csv`,
`cve_fix_pairs-selected-columns.csv`, `known_exploited_vulnerabilities.csv`,
and `NVD_Cybersecurity_Dataset.csv`. `KDDTest.csv` is filed separately as a
network-security benchmark. `final_dataset.csv` is a 370 MB `label,text` file
whose source/license is not recorded, so it is quarantined from the curated
training candidates until identified.

### Loose PDFs

- `docs/references/cdm/`: `cdm-data-model-v601-508.pdf` and
  `PUBLIC_CDM_LDM_v6.0.pdf`.
- `docs/references/cisa/`: `cisa-vulnerability-review-fy-2024-2025_508.pdf`,
  `joint-guide-establishing-a-cvd-program-to-work-with-security-researchers_508c.pdf`,
  and the renamed KEV prioritization text.
- `docs/papers/`: `Dataset_of_Shell_Commands_Used_by_Participants_of_.pdf`.
- PDFs that belong to a Git repository remain inside that repository; the
  repository tree itself is grouped under `repositories/github/`.

## Repository relocation

All 16 Git clones were clean before relocation. Root aliases preserve all
original clone names; `repositories/README.md` lists the grouped repositories.
The CVEProject working trees remain siblings to preserve relative imports.

## Legacy cloud-training environment

`training_environment/` remains at the workspace root because it contains its
own virtual environment and training scripts/configuration. The environment,
its configs, and scripts remain at the old path; its Kaggle staging directory,
notebook package, and `models/final_model.zip` have been filed under B13 with
compatibility symlinks at the old paths. Credentials and environment
configuration contents were not inspected.

The HF cache snapshot for `nebius/SWE-rebench-V2-PRs` is incomplete: three
Parquet snapshot links have no corresponding blob. The metadata/README files
are present. No download or authentication attempt was made.
The HF-style export's generated `skills/.kilo/node_modules/` directory (62 MB)
was removed; its `package.json` and lockfile remain for reproducible reinstall.

## Loose source-file moves

- Root CSVs were classified using filenames, headers, and file sizes, not sample
  records. `final_dataset.csv` remains unclassified pending source provenance.
- `BankNoteAuthentication.csv` was moved from raw candidates to
  `data/excluded/non-b13-benchmarks/`; its numeric banknote-classification
  schema has no identified B13 training use.
- Loose PDFs were grouped by title/topic. PDFs inside Git repositories remain
  with their source repositories.
- The root `moredata` text export was renamed to
  `docs/references/cisa/kev-prioritization-bod-26-04.txt`.
- Existing paths such as `datasets/`, `DATASETS/`, and each repository name are
  symlinks; use the organized paths under `b13_agent/` for new work.

No source dataset rows were edited. The only duplicate directory removed was
`training_environment/datasets/`, after SHA-256 verification against every
relative-path counterpart in the HF export; its old path is now a symlink.
Empty `training/` and `deployment/` scaffolds were removed.
