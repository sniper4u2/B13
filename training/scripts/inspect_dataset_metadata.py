#!/usr/bin/env python3
"""Report dataset schemas and row counts without printing sample records."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, cast

import pyarrow.csv as arrow_csv  # type: ignore[reportMissingTypeStubs]
import pyarrow.parquet as parquet  # type: ignore[reportMissingTypeStubs]


def parquet_row_count(path: Path) -> int:
    reader: Any = parquet.ParquetFile(path)  # type: ignore[reportUnknownMemberType]
    return reader.metadata.num_rows


def inspect_messages(path: Path) -> dict[str, Any]:
    table: Any = parquet.read_table(path, columns=["messages"])  # type: ignore[reportUnknownMemberType]
    missing_rows = 0
    empty_rows = 0
    malformed_rows = 0
    empty_contents = 0
    roles: Counter[str] = Counter()

    rows = cast(
        list[dict[str, Any]],
        table.to_pylist(),  # type: ignore[reportUnknownMemberType]
    )
    for row in rows:
        messages: Any = row["messages"]
        if messages is None:
            missing_rows += 1
            continue
        if not isinstance(messages, list):
            malformed_rows += 1
            continue
        if not messages:
            empty_rows += 1
            continue
        messages = cast(list[Any], messages)
        for message in messages:
            if not isinstance(message, dict):
                malformed_rows += 1
                continue
            message_fields = cast(dict[str, Any], message)
            role: Any = message_fields.get("role")
            if not isinstance(role, str) or not role:
                malformed_rows += 1
            else:
                roles[role] += 1
            content: Any = message_fields.get("content")
            if not isinstance(content, str) or not content.strip():
                empty_contents += 1

    return {
        "rows_missing_messages": missing_rows,
        "rows_with_empty_messages": empty_rows,
        "malformed_messages": malformed_rows,
        "messages_with_empty_content": empty_contents,
        "role_counts": dict(sorted(roles.items())),
    }


def read_keys(path: Path, columns: list[str]) -> set[tuple[Any, ...]]:
    table: Any = parquet.read_table(path, columns=columns)  # type: ignore[reportUnknownMemberType]
    return {
        tuple(row[column] for column in columns)
        for row in cast(
            list[dict[str, Any]],
            table.to_pylist(),  # type: ignore[reportUnknownMemberType]
        )
    }


def inspect_file(path: Path) -> dict[str, Any]:
    if path.suffix.lower() == ".parquet":
        reader: Any = parquet.ParquetFile(path)  # type: ignore[reportUnknownMemberType]
        result: dict[str, Any] = {
            "path": str(path),
            "format": "parquet",
            "rows": reader.metadata.num_rows,
            "columns": reader.schema_arrow.names,
        }
        if "messages" in result["columns"]:
            result["messages_quality"] = inspect_messages(path)
        return result

    if path.suffix.lower() == ".csv":
        table: Any = arrow_csv.read_csv(path)  # type: ignore[reportUnknownMemberType]
        return {
            "path": str(path),
            "format": "csv",
            "rows": table.num_rows,  # type: ignore[reportUnknownMemberType]
            "columns": list(table.schema.names),  # type: ignore[reportUnknownMemberType]
        }

    raise ValueError(f"Unsupported tabular dataset format: {path}")


def dataset_files(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    if path.is_dir():
        return sorted(
            file
            for file in path.rglob("*")
            if file.is_file() and file.suffix.lower() in {".parquet", ".csv"}
        )
    raise FileNotFoundError(f"Dataset path does not exist: {path}")


def validate_catalog_paths(catalog: dict[str, Any], root: Path) -> None:
    for section in (
        "raw_sources",
        "training_candidates",
        "evaluation_candidates",
        "reference_documents",
    ):
        for item in catalog.get(section, []):
            path = root / item["path"]
            if not path.exists():
                raise FileNotFoundError(f"{section} {item['id']}: {path}")
            files: Any = item.get("files", [])
            # Catalog uses mixed shapes: int counts, dicts keyed by
            # filename, or lists of filenames. Only lists of strings name
            # children to verify; counts and mappings are informational.
            names: list[str] = []
            if isinstance(files, list):
                names = [name for name in files if isinstance(name, str)]
            elif isinstance(files, dict):
                names = [name for name in files.keys() if isinstance(name, str)]
            for name in names:
                child = path / name
                if not child.exists():
                    raise FileNotFoundError(f"{section} {item['id']}: {child}")
            for field in ("source_path", "claim_source", "training_entrypoint"):
                if field in item:
                    source = root / item[field]
                    if not source.exists():
                        raise FileNotFoundError(
                            f"{section} {item['id']} {field}: {source}"
                        )

    for split in catalog.get("split_sets", []):
        for field in ("train_path", "validation_path", "aggregate_path"):
            if field in split:
                path = root / split[field]
                if not path.exists():
                    raise FileNotFoundError(f"split {split['id']} {field}: {path}")


def main() -> None:
    default_catalog = Path(__file__).resolve().parents[2] / "data" / "catalog.json"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=default_catalog)
    args = parser.parse_args()

    catalog_path = args.catalog.resolve()
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    root = catalog_path.parent
    validate_catalog_paths(catalog, root)
    results: list[dict[str, Any]] = []

    for section in ("training_candidates", "evaluation_candidates"):
        for dataset in catalog[section]:
            source = root / dataset["path"]
            files = [
                inspect_file(file)
                for file in dataset_files(source)
            ]
            results.append(
                {
                    "id": dataset["id"],
                    "category": section,
                    "files": files,
                }
            )

    split_results: list[dict[str, Any]] = []
    for split in catalog.get("split_sets", []):
        train_path = root / split["train_path"]
        validation_path = root / split["validation_path"]
        key_columns = split["key_columns"]
        train_keys = read_keys(train_path, key_columns)
        validation_keys = read_keys(validation_path, key_columns)
        result: dict[str, Any] = {
            "id": split["id"],
            "train_rows": parquet_row_count(train_path),
            "validation_rows": parquet_row_count(validation_path),
            "train_validation_key_overlap": len(train_keys & validation_keys),
        }

        if "aggregate_path" in split:
            aggregate_path = root / split["aggregate_path"]
            aggregate_keys = read_keys(aggregate_path, key_columns)
            split_keys = train_keys | validation_keys
            result["aggregate_rows"] = parquet_row_count(aggregate_path)
            result["aggregate_keys_missing_from_splits"] = len(
                aggregate_keys - split_keys
            )
            result["split_keys_missing_from_aggregate"] = len(
                split_keys - aggregate_keys
            )

        split_results.append(result)

    print(
        json.dumps(
            {
                "catalog": str(catalog_path),
                "datasets": results,
                "split_sets": split_results,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
