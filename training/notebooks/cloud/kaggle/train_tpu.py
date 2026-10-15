#!/usr/bin/env python3
"""LoRA fine-tuning entrypoint for the configured Kaggle TPU export."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


def verify_export(data_dir: Path) -> tuple[dict, dict]:
    manifest_path = data_dir / "manifest.json"
    config_path = data_dir / "config.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    config = json.loads(config_path.read_text(encoding="utf-8"))

    for filename, metadata in manifest["files"].items():
        path = data_dir / filename
        if not path.is_file():
            raise FileNotFoundError(f"Export file is missing: {path}")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != metadata["sha256"]:
            raise ValueError(f"SHA-256 mismatch for exported file: {path}")

    if manifest["model"]["repo_id"] != config["model"]["repo_id"]:
        raise ValueError("Export manifest and config name different base models")
    if manifest["model"]["revision"] != config["model"]["revision"]:
        raise ValueError("Export manifest and config name different model revisions")
    return manifest, config


def require_tpu() -> None:
    try:
        import torch_xla.runtime as xr
    except ImportError as error:
        raise RuntimeError("Kaggle TPU runtime is required; torch_xla is unavailable") from error
    if xr.device_type() != "TPU":
        raise RuntimeError(f"Configured TPU run found device type {xr.device_type()!r}, not 'TPU'")


def install_training_dependencies() -> None:
    requirements = Path(__file__).with_name("requirements.txt")
    if not requirements.is_file():
        raise FileNotFoundError(f"Training requirements file is missing: {requirements}")
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            "-r",
            str(requirements),
        ],
        check=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Verify the attached export without importing training libraries or using an accelerator",
    )
    parser.add_argument(
        "--run-training",
        action="store_true",
        help="Run the full configured training job instead of the default two-step preflight",
    )
    args = parser.parse_args()
    local_export = Path(__file__).resolve().parents[4] / "data" / "exports" / "qwen3-30b-a3b"
    data_dir_value = os.environ.get(
        "B13_DATA_DIR",
        str(local_export if local_export.is_dir() else "/kaggle/input/b13-qwen3-30b-a3b-training"),
    )
    data_dir = Path(data_dir_value)
    if not data_dir.is_dir():
        raise FileNotFoundError(
            f"Prepared training export not found at {data_dir}; "
            "set B13_DATA_DIR to the attached Kaggle dataset directory"
        )
    manifest, config = verify_export(data_dir)
    if args.validate_only:
        print(
            json.dumps(
                {
                    "status": "export-valid",
                    "model": config["model"]["repo_id"],
                    "revision": config["model"]["revision"],
                    "rows": manifest["rows"],
                },
                indent=2,
            )
        )
        return

    require_tpu()
    # NOTE: keep this import-time check BEFORE pip install so a missing TPU
    # fails fast without churning the kernel environment.
    try:
        import torch_xla  # noqa: F401
    except ImportError as error:
        raise RuntimeError(
            "torch_xla is required on the Kaggle TPU image; "
            "do not replace the kernel torch stack"
        ) from error
    install_training_dependencies()
    import torch
    import torch_xla.core.xla_model as xm
    from datasets import load_dataset
    from peft import LoraConfig, get_peft_model
    from transformers import (
        AutoModelForCausalLM,
        AutoTokenizer,
        DataCollatorForLanguageModeling,
        Trainer,
        TrainingArguments,
    )

    model_config = config["model"]
    max_length = model_config["max_length"]
    tokenizer = AutoTokenizer.from_pretrained(
        model_config["repo_id"],
        revision=model_config["revision"],
        use_fast=True,
    )
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        model_config["repo_id"],
        revision=model_config["revision"],
        torch_dtype=torch.bfloat16,
        low_cpu_mem_usage=True,
    )
    model.config.use_cache = False
    model = get_peft_model(
        model,
        LoraConfig(
            r=config["lora"]["rank"],
            lora_alpha=config["lora"]["alpha"],
            lora_dropout=config["lora"]["dropout"],
            target_modules=config["lora"]["target_modules"],
            bias="none",
            task_type="CAUSAL_LM",
        ),
    )
    model.print_trainable_parameters()

    raw = load_dataset(
        "json",
        data_files={
            "train": str(data_dir / "train.jsonl"),
            "validation": str(data_dir / "validation.jsonl"),
        },
    )

    def tokenize_row(row: dict) -> dict[str, list[int]]:
        token_ids = tokenizer.apply_chat_template(
            row["messages"],
            tokenize=True,
            add_generation_prompt=False,
            truncation=True,
            max_length=max_length,
        )
        if len(token_ids) < 2:
            raise ValueError("A chat example produced fewer than two tokens")
        return {"input_ids": token_ids}

    tokenized = raw.map(
        tokenize_row,
        remove_columns=raw["train"].column_names,
        desc="Applying the pinned Qwen chat template",
    )

    # Fail fast on context overflow: the export manifest still records
    # context_validation.status=pending, so measure BEFORE spending TPU steps.
    # Any example already at max_length after truncation is counted as
    # truncated; >5% truncated blocks the full run.
    def _lengths(split: str) -> list[int]:
        return [len(ids) for ids in tokenized[split]["input_ids"]]

    train_lengths = _lengths("train")
    val_lengths = _lengths("validation")
    for split_name, lengths in (("train", train_lengths), ("validation", val_lengths)):
        truncated = sum(1 for n in lengths if n >= max_length)
        print(
            f"Context check [{split_name}]: n={len(lengths)}, "
            f"max={max(lengths)}, truncated_at_{max_length}={truncated}"
        )
        if not lengths or min(lengths) < 2:
            raise ValueError(f"Tokenized {split_name} split is empty or degenerate")
    if args.run_training:
        train_trunc_rate = sum(1 for n in train_lengths if n >= max_length) / len(train_lengths)
        if train_trunc_rate > 0.05:
            raise ValueError(
                f"Train truncation rate {train_trunc_rate:.2%} exceeds 5% at "
                f"max_length={max_length}; raise max_length or re-cut the export"
            )

    training = config["training"]
    if args.run_training:
        train_dataset = tokenized["train"]
        eval_dataset = tokenized["validation"]
        max_steps = training["max_steps"]
        epochs = training["epochs"]
        accumulation_steps = training["gradient_accumulation_steps"]
        evaluation_strategy = "steps"
        save_strategy = "steps"
    else:
        train_dataset = tokenized["train"].select(range(min(16, len(tokenized["train"]))))
        eval_dataset = None
        max_steps = 2
        epochs = 1
        accumulation_steps = 1
        evaluation_strategy = "no"
        save_strategy = "no"

    fsdp_config = training["fsdp_config"]
    arguments = TrainingArguments(
        output_dir=config["runtime"]["output_dir"],
        num_train_epochs=epochs,
        max_steps=max_steps,
        per_device_train_batch_size=training["per_device_train_batch_size"],
        per_device_eval_batch_size=training["per_device_eval_batch_size"],
        gradient_accumulation_steps=accumulation_steps,
        learning_rate=training["learning_rate"],
        warmup_ratio=training["warmup_ratio"],
        weight_decay=training["weight_decay"],
        logging_steps=training["logging_steps"],
        save_strategy=save_strategy,
        save_steps=training["save_steps"],
        save_total_limit=training["save_total_limit"],
        eval_strategy=evaluation_strategy,
        eval_steps=training["eval_steps"],
        bf16=training["bf16"],
        gradient_checkpointing=training["gradient_checkpointing"],
        fsdp=training["fsdp"],
        fsdp_config=fsdp_config,
        report_to="none",
        remove_unused_columns=True,
        dataloader_num_workers=0,
        ddp_find_unused_parameters=False,
    )
    trainer = Trainer(
        model=model,
        args=arguments,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        data_collator=DataCollatorForLanguageModeling(tokenizer, mlm=False),
        processing_class=tokenizer,
    )

    if args.run_training:
        print(
            f"Starting full TPU LoRA run: {model_config['repo_id']} "
            f"revision={model_config['revision']}, "
            f"train={manifest['rows']['train']}, "
            f"validation={manifest['rows']['validation']}"
        )
        trainer.train()
        trainer.save_model(config["runtime"]["output_dir"])
        tokenizer.save_pretrained(config["runtime"]["output_dir"])
        output_dir = Path(config["runtime"]["output_dir"])
        shutil.copy2(data_dir / "config.json", output_dir / "training_config.json")
        shutil.copy2(data_dir / "manifest.json", output_dir / "training_manifest.json")
    else:
        print("Starting bounded TPU preflight: 2 optimizer steps, no evaluation or checkpoint save.")
        trainer.train()


if __name__ == "__main__":
    main()
