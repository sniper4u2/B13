#!/usr/bin/env python3
"""Build a deduplicated JSONL export from the registered B13 SFT splits."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

import pyarrow.parquet as parquet

CVE_ID_PATTERN = re.compile(r"\bCVE-\d{4}-\d{4,}\b", re.IGNORECASE)


def digest_messages(messages: list[dict[str, Any]]) -> str:
    encoded = json.dumps(
        messages,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def read_split(path: Path, source_id: str) -> list[dict[str, Any]]:
    table = parquet.read_table(path, columns=["messages"])
    rows = table.to_pylist()
    records: list[dict[str, Any]] = []

    for row_number, row in enumerate(rows, start=1):
        messages = row["messages"]
        if not isinstance(messages, list) or not messages:
            raise ValueError(f"{path}:{row_number} has no non-empty messages list")
        for message in messages:
            if not isinstance(message, dict):
                raise ValueError(f"{path}:{row_number} contains a malformed message")
            if not isinstance(message.get("role"), str) or not message["role"]:
                raise ValueError(f"{path}:{row_number} contains a message without a role")
            content = message.get("content")
            if not isinstance(content, str) or not content.strip():
                raise ValueError(f"{path}:{row_number} contains empty or non-text content")
        records.append(
            {
                "source": source_id,
                "messages": messages,
                "_digest": digest_messages(messages),
                "_cve_ids": {
                    value.upper()
                    for message in messages
                    for value in CVE_ID_PATTERN.findall(message["content"])
                },
            }
        )
    return records


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> str:
    hasher = hashlib.sha256()
    with path.open("wb") as output:
        for record in records:
            line = json.dumps(
                {"source": record["source"], "messages": record["messages"]},
                ensure_ascii=False,
                separators=(",", ":"),
            ).encode("utf-8") + b"\n"
            output.write(line)
            hasher.update(line)
    return hasher.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[2],
        help="B13 workspace root",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path(__file__).resolve().parents[1]
        / "configs"
        / "qwen3-30b-a3b-kaggle-tpu.json",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output directory (default: data/exports/qwen3-30b-a3b)",
    )
    args = parser.parse_args()

    root = args.root.resolve()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    catalog_path = (root / config["dataset"]["catalog"]).resolve()
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    output_dir = args.output or root / "data" / "exports" / "qwen3-30b-a3b"
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    registered = {item["id"]: item for item in catalog["split_sets"]}
    # Split file paths are relative to the canonical workbench directory
    workbench = root / "data" / catalog.get("canonical_source_root", "sources/corpora/datasets-workbench")
    all_train: list[dict[str, Any]] = []
    all_validation: list[dict[str, Any]] = []
    source_stats: dict[str, dict[str, int]] = {}

    for split_id in config["dataset"]["split_sets"]:
        if split_id not in registered:
            raise ValueError(f"Split set {split_id!r} is not registered in {catalog_path}")
        split = registered[split_id]
        train_path = (workbench / split["train_path"]).resolve()
        validation_path = (workbench / split["validation_path"]).resolve()
        if not train_path.is_file():
            raise FileNotFoundError(f"Training split not found: {train_path}")
        if not validation_path.is_file():
            raise FileNotFoundError(f"Validation split not found: {validation_path}")

        train_records = read_split(train_path, split_id)
        validation_records = read_split(validation_path, split_id)
        source_stats[split_id] = {
            "train_input_rows": len(train_records),
            "validation_input_rows": len(validation_records),
        }
        all_train.extend(train_records)
        all_validation.extend(validation_records)

    validation_digests: set[str] = set()
    validation_records: list[dict[str, Any]] = []
    validation_duplicates = 0
    for record in all_validation:
        if record["_digest"] in validation_digests:
            validation_duplicates += 1
            continue
        validation_digests.add(record["_digest"])
        validation_records.append(record)

    validation_cve_ids = set().union(
        *(record["_cve_ids"] for record in validation_records)
    )
    train_cve_ids_before_filter = set().union(
        *(record["_cve_ids"] for record in all_train)
    )
    shared_cve_ids = train_cve_ids_before_filter & validation_cve_ids

    train_digests: set[str] = set()
    train_records: list[dict[str, Any]] = []
    train_duplicates = 0
    train_validation_conflicts = 0
    train_cve_validation_conflicts = 0
    for record in all_train:
        digest = record["_digest"]
        if digest in validation_digests:
            train_validation_conflicts += 1
        elif record["_cve_ids"] & validation_cve_ids:
            train_cve_validation_conflicts += 1
        elif digest in train_digests:
            train_duplicates += 1
        else:
            train_digests.add(digest)
            train_records.append(record)

    if not train_records or not validation_records:
        raise ValueError("The prepared training and validation sets must both be non-empty")

    remaining_train_cve_ids = set().union(
        *(record["_cve_ids"] for record in train_records)
    )
    remaining_validation_cve_ids = set().union(
        *(record["_cve_ids"] for record in validation_records)
    )
    if remaining_train_cve_ids & remaining_validation_cve_ids:
        raise ValueError("CVE ID overlap remains between prepared training and validation data")

    train_path = output_dir / "train.jsonl"
    validation_path = output_dir / "validation.jsonl"
    manifest_path = output_dir / "manifest.json"
    exported_config_path = output_dir / "config.json"
    train_sha256 = write_jsonl(train_path, train_records)
    validation_sha256 = write_jsonl(validation_path, validation_records)
    exported_config_path.write_text(
        json.dumps(config, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    manifest = {
        "schema_version": 1,
        "model": config["model"],
        "source_split_sets": source_stats,
        "source_warnings": config["dataset"].get("source_warnings", {}),
        "rows": {
            "train_before_deduplication": len(all_train),
            "validation_before_deduplication": len(all_validation),
            "train": len(train_records),
            "validation": len(validation_records),
            "duplicate_train_rows_removed": train_duplicates,
            "duplicate_validation_rows_removed": validation_duplicates,
            "train_rows_removed_for_validation_overlap": train_validation_conflicts,
            "train_rows_removed_for_cve_id_validation_overlap": train_cve_validation_conflicts,
            "validation_unique_cve_ids": len(validation_cve_ids),
            "train_validation_shared_cve_ids_before_filter": len(shared_cve_ids),
            "train_unique_cve_ids_after_filter": len(
                set().union(*(record["_cve_ids"] for record in train_records))
            ),
        },
        "files": {
            "train.jsonl": {"sha256": train_sha256},
            "validation.jsonl": {"sha256": validation_sha256},
            "config.json": {"sha256": hashlib.sha256(exported_config_path.read_bytes()).hexdigest()},
        },
        "data_review": {
            "exact_duplicate_check": "performed across all selected train and validation splits",
            "semantic_leakage_check": "not performed",
            "source_licenses": "not verified; review before cloud upload or redistribution",
        },
        "content_role_counts": dict(
            sorted(
                Counter(
                    message["role"]
                    for record in train_records + validation_records
                    for message in record["messages"]
                ).items()
            )
        ),
        "excluded_by_design": [
            "evaluation candidates",
            "raw CSV/JSON/PDF/repository sources that are not registered SFT splits",
            "unclassified final_dataset.csv and unreviewed archives",
            "alternate CVE and code-security transformations outside the selected split sets",
        ],
    }
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"output": str(output_dir), **manifest["rows"]}, indent=2))


if __name__ == "__main__":
    main()
