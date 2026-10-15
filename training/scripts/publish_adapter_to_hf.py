#!/usr/bin/env python3
"""Publish a completed B13 LoRA adapter to a private repo in the logged-in HF account."""

from __future__ import annotations

import argparse
from pathlib import Path

from huggingface_hub import HfApi
from huggingface_hub.utils import RepositoryNotFoundError

UPLOAD_FILES = {
    "adapter_config.json",
    "adapter_model.safetensors",
    "added_tokens.json",
    "generation_config.json",
    "merges.txt",
    "special_tokens_map.json",
    "tokenizer.json",
    "tokenizer_config.json",
    "training_config.json",
    "training_manifest.json",
    "vocab.json",
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("adapter_dir", type=Path, help="Directory containing the saved LoRA adapter")
    parser.add_argument(
        "--repo-name",
        default="b13-qwen3-30b-a3b-lora",
        help="Repository name under the currently authenticated personal account",
    )
    args = parser.parse_args()

    adapter_dir = args.adapter_dir.resolve()
    required = {"adapter_config.json", "adapter_model.safetensors"}
    missing = sorted(name for name in required if not (adapter_dir / name).is_file())
    if missing:
        raise FileNotFoundError(f"Adapter directory is incomplete; missing: {', '.join(missing)}")

    api = HfApi()
    profile = api.whoami()
    username = profile.get("name")
    if not isinstance(username, str) or not username:
        raise RuntimeError("Hugging Face did not return a personal username for the active login")

    repo_id = f"{username}/{args.repo_name}"
    try:
        existing = api.repo_info(repo_id, repo_type="model")
    except RepositoryNotFoundError:
        api.create_repo(repo_id, repo_type="model", private=True)
    else:
        if not existing.private:
            raise RuntimeError(f"Refusing to upload to non-private repository {repo_id}")

    api.upload_folder(
        folder_path=str(adapter_dir),
        repo_id=repo_id,
        repo_type="model",
        allow_patterns=sorted(UPLOAD_FILES),
        commit_message="Upload B13 Qwen3 LoRA adapter and training manifest",
    )
    print(f"Uploaded adapter to private Hugging Face model repo: {repo_id}")


if __name__ == "__main__":
    main()
