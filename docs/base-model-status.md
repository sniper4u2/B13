# Base model status

## Selected fine-tuning candidate

The B13 Kaggle TPU preparation path is configured for
[`Qwen/Qwen3-30B-A3B`](https://huggingface.co/Qwen/Qwen3-30B-A3B) at immutable
revision `ad44e777bcd18fa416d9da3bd8f70d33ebb85d39`. Its published configuration
identifies a Qwen3 MoE architecture with 128 experts and top-8 routing; the
selected model card declares Apache-2.0. This is a LoRA fine-tuning candidate,
not evidence that a Kaggle TPU run has succeeded.

The older Kaggle training script referred to `deepseek-ai/DeepSeek-V4-Pro`, an
unverified Kaggle dataset, and a misspelled Kaggle owner. That script and its
metadata have been replaced; the new Kaggle kernel is private and has no
dataset attached yet.

## Existing checkpoint

The metadata inside `models/checkpoints/distilbert-final-model.zip` (also
available through the compatibility path
`training_environment/models/final_model.zip`) reports
`model_type: distilbert` and contains no exact model repository identifier.
That does not establish that the archive is the configured DeepSeek candidate;
it is not being treated as the agent's base model.

## Before training

The local machine has a GTX 1650 Ti with 4 GiB, not an RTX 6000 Pro. The
verified Kaggle account reports 30 GPU-hours and 20 TPU-hours remaining. The
configured route therefore targets Kaggle's eight-core TPU with XLA FSDP; it
must be runtime-tested before spending TPU quota. The Hugging Face CLI is
already authenticated, but no dataset or adapter has been uploaded.

Prepare the registered train/validation splits with:

```bash
./.venv/bin/python training/scripts/prepare_training_export.py
```

This creates an ignored local export under `data/exports/qwen3-30b-a3b/`.
It combines only registered SFT split files, removes exact duplicate
conversations across sources, keeps validation examples out of training, and
writes a manifest with source counts and hashes. Evaluation data, raw
unclassified files, unreviewed archives, and alternate transformations remain
excluded. The agent-skills split is included as its own registered version;
its known aggregate/split lineage mismatch is recorded in the manifest.

The separate local CVE-record candidate is under
`data/exports/cve-record-summary/`. It contains 338,369 train and 37,513
validation examples from published CVE records, excluding 9,987 CVE IDs
mentioned in registered SFT. Its source revision, MITRE attribution, hashes,
and per-field omission counts are recorded in the candidate manifest. This
candidate is not part of the registered export or the current Kaggle dataset.
Its examples still need pinned-tokenizer length validation against the
configured 2,048-token window, a data-mixture decision, and CNA rights review
before upload or training. The currently attached private Kaggle dataset is an
older SFT-only snapshot and must not be used for the next run.

No cloud compute was launched. The private Kaggle kernel has no data source
attached, and the staged export has not been uploaded. A training run requires
the export to be staged privately and the TPU runtime to pass a smoke test.
After training, `training/scripts/publish_adapter_to_hf.py` can publish the
adapter to a private repository under the currently authenticated personal
Hugging Face account; it refuses public repositories and does not target
organizations.
