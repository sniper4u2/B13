# B13 Agent workspace

This folder contains the current B13 runtime and the isolated Python environment
for future agent and fine-tuning work. The existing training configuration
names `deepseek-ai/DeepSeek-V4-Pro` as its model candidate. See
[`docs/base-model-status.md`](docs/base-model-status.md) for the evidence and
remaining verification gap; no training has been started.

## Layout

| Path | Purpose |
| --- | --- |
| `agent.py`, `app.py`, `runtime.py`, `ui.py`, `b13/` | Existing runtime and UI code; entrypoints are unchanged for now. |
| `data/raw/` | Consolidated raw datasets, source archives, CVE records, and HF dataset-cache snapshots. |
| `data/cve/` | Single CVE collection entrypoint across raw records, source tables, references, and SFT. |
| `data/sources/corpora/` | Physically relocated canonical dataset workbench and HF export trees. |
| `data/imports/` | Named links to the consolidated corpora and legacy cloud-training dataset view. |
| `data/interim/` | Temporary validation and normalization outputs. |
| `data/processed/` | Named read-only views of the existing processed SFT artifacts. |
| `data/evals/` | Evaluation dataset views. |
| `models/base/` | References or local copies of confirmed base models. |
| `models/checkpoints/` | Training checkpoints and exports. |
| `models/adapters/` | Parameter-efficient fine-tuning adapters. |
| `training/configs/` | Reviewed training configurations. |
| `training/scripts/`, `training/notebooks/` | Reproducible data preparation and Kaggle TPU training entrypoints. |
| `requirements-training.txt` | Training dependencies for the Kaggle TPU image; preserve its matching `torch`/`torch_xla` installation. |
| `training/reports/` | Training and evaluation reports. |
| `docs/papers/` | Papers and research notes relevant to the model and datasets. |
| `repositories/github/` | All 16 cloned Git repositories grouped by CVE Project and research source. |
| `agent_skills/library/` | Existing skill library, retained as source material. |
| `mcp/` | MCP integrations and non-secret integration documentation. |
| `tests/` | Runtime, data, and training-pipeline tests. |
| `.venv/` | Local Python 3.12 virtual environment with runtime, data-inspection, and Kaggle CLI dependencies. |

## Current inventory notes

- The runtime dependencies are listed in `requirements.txt`; it does not define
  a fine-tuning stack.
- The selected Qwen3 MoE candidate, split selection, TPU FSDP settings, and
  readiness limits are recorded in
  [`docs/base-model-status.md`](docs/base-model-status.md). Build the local
  train/validation export with
  `./.venv/bin/python training/scripts/prepare_training_export.py`; cloud
  compute and uploads are deliberately separate steps.
- After retrieving a trained adapter from Kaggle, publish it privately under
  the currently authenticated personal Hugging Face account with
  `./.venv/bin/python training/scripts/publish_adapter_to_hf.py <adapter-dir>`.
  The publisher refuses a repository that is not private and does not target
  organization namespaces.
- See [`data/README.md`](data/README.md) for the canonical dataset views,
  duplicate-artifact findings, and CVE source classification.
- See [`docs/workspace-map.md`](docs/workspace-map.md) for relocated files,
  repository groups, compatibility paths, and items intentionally left in the
  legacy training environment.
- Legacy workspace paths such as `datasets/`, `DATASETS/`, and each cloned
  repository name remain as symlinks into their organized locations under this
  folder, so existing scripts and repository sibling layouts continue to work.
- The B13 Kaggle API token is stored only in the ignored `.venv/kaggle_api_token`
  file with owner-only permissions. Activating this venv loads it into
  `KAGGLE_API_TOKEN`; deactivation restores the prior environment value. The
  global `~/.kaggle` configuration is not used or changed.
