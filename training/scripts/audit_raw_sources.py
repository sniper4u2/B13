#!/usr/bin/env python3
"""Audit raw CVE and CSV structure without emitting source record content."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import pyarrow.parquet as parquet


def audit_csv(path: Path) -> tuple[dict[str, Any], set[str]]:
    csv.field_size_limit(sys.maxsize)
    result: dict[str, Any] = {
        "path": str(path),
        "bytes": path.stat().st_size,
        "records": 0,
        "headers": [],
        "bad_width_records": 0,
        "blank_cells": 0,
        "key_column": None,
        "unique_keys": None,
        "duplicate_keys": None,
    }
    ids: set[str] = set()
    seen: set[str] = set()

    with path.open("r", encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source, strict=True)
        headers = reader.fieldnames or []
        result["headers"] = headers
        key = next(
            (
                name
                for name in headers
                if name.lower() in {"cve_id", "cveid", "cve_number"}
            ),
            None,
        )
        result["key_column"] = key
        duplicate_keys = 0

        for row in reader:
            result["records"] += 1
            if None in row:
                result["bad_width_records"] += 1
            result["blank_cells"] += sum(
                value is None or not value.strip() for value in row.values()
            )
            value = row.get(key) if key else None
            if value:
                normalized = value.strip().upper()
                ids.add(normalized)
                if normalized in seen:
                    duplicate_keys += 1
                else:
                    seen.add(normalized)

    if key:
        result["unique_keys"] = len(seen)
        result["duplicate_keys"] = duplicate_keys
    return result, ids


def audit_cvelist(
    root: Path,
    csv_ids: dict[str, set[str]],
) -> tuple[dict[str, Any], set[str], set[str]]:
    cve_root = root / "repositories" / "github" / "CVEProject" / "cvelistV5" / "cves"
    files = sorted(
        path for path in cve_root.rglob("CVE-*.json") if path.is_file()
    )
    states: Counter[str] = Counter()
    years: Counter[str] = Counter()
    languages: Counter[str] = Counter()
    missing: Counter[str] = Counter()
    ids: set[str] = set()
    published_ids: set[str] = set()
    duplicates = 0
    invalid_json = 0
    non_object_json = 0
    records_with_cna = 0
    published_records = 0
    published_with_english_description = 0
    published_without_english_description = 0
    published_with_affected = 0
    published_with_metrics = 0
    csv_overlap: dict[str, dict[str, int]] = {}

    for path in files:
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            invalid_json += 1
            continue
        if not isinstance(record, dict):
            non_object_json += 1
            continue

        metadata = record.get("cveMetadata")
        if not isinstance(metadata, dict):
            missing["cveMetadata_object"] += 1
            continue

        cve_id = metadata.get("cveId")
        if not isinstance(cve_id, str) or not cve_id.strip():
            missing["cveId"] += 1
            continue
        normalized_id = cve_id.strip().upper()
        if normalized_id in ids:
            duplicates += 1
        else:
            ids.add(normalized_id)

        id_parts = normalized_id.split("-")
        years[id_parts[1] if len(id_parts) > 1 else "[unknown]"] += 1
        state = metadata.get("state")
        states[state if isinstance(state, str) else "[missing]"] += 1
        if state == "PUBLISHED":
            published_records += 1
            published_ids.add(normalized_id)

        containers = record.get("containers")
        cna = containers.get("cna") if isinstance(containers, dict) else None
        if not isinstance(cna, dict):
            missing["containers.cna_object"] += 1
            continue
        records_with_cna += 1

        descriptions = cna.get("descriptions")
        if not isinstance(descriptions, list) or not descriptions:
            missing["cna.descriptions"] += 1
            has_english_description = False
        else:
            has_english_description = False
            for description in descriptions:
                if isinstance(description, dict):
                    language = description.get("lang")
                    languages[language if isinstance(language, str) else "[missing]"] += 1
                    if (
                        language in {"en", "en-US"}
                        and isinstance(description.get("value"), str)
                        and description["value"].strip()
                    ):
                        has_english_description = True

        affected = cna.get("affected")
        metrics = cna.get("metrics")
        if state == "PUBLISHED":
            published_with_english_description += has_english_description
            published_without_english_description += not has_english_description
            published_with_affected += isinstance(affected, list) and bool(affected)
            published_with_metrics += isinstance(metrics, list) and bool(metrics)

        for field in ("references", "affected", "problemTypes", "metrics"):
            value = cna.get(field)
            if not isinstance(value, list) or not value:
                missing[f"cna.{field}"] += 1

    for source, source_ids in csv_ids.items():
        csv_overlap[source] = {
            "unique_ids": len(source_ids),
            "ids_in_cvelist": len(source_ids & ids),
            "ids_not_in_cvelist": len(source_ids - ids),
        }

    report = {
        "path": str(cve_root),
        "record_files": len(files),
        "unique_cve_ids": len(ids),
        "duplicate_cve_ids": duplicates,
        "invalid_json_files": invalid_json,
        "non_object_json_files": non_object_json,
        "published_records": published_records,
        "published_with_english_description": published_with_english_description,
        "published_without_english_description": published_without_english_description,
        "published_with_affected": published_with_affected,
        "published_with_metrics": published_with_metrics,
        "states": dict(sorted(states.items())),
        "records_by_year": dict(sorted(years.items())),
        "records_with_cna_container": records_with_cna,
        "missing_or_empty_fields": dict(sorted(missing.items())),
        "description_languages": dict(languages.most_common(50)),
        "csv_id_overlap": csv_overlap,
    }
    return report, ids, published_ids


def read_cve_sft_ids(root: Path) -> dict[str, set[str]]:
    catalog = json.loads((root / "data" / "catalog.json").read_text(encoding="utf-8"))
    split = next(item for item in catalog["split_sets"] if item["id"] == "cve-enhanced-v3")
    key_columns = split["key_columns"]
    result: dict[str, set[str]] = {}
    for label in ("train", "validation"):
        path = root / "data" / split[f"{label}_path"]
        table = parquet.read_table(path, columns=key_columns)
        result[label] = {
            str(row[key_columns[0]]).strip().upper()
            for row in table.to_pylist()
            if row[key_columns[0]] is not None
        }
    return result


def read_cve_mentions_from_sft(
    root: Path,
) -> tuple[dict[str, Any], dict[str, set[str]]]:
    catalog = json.loads((root / "data" / "catalog.json").read_text(encoding="utf-8"))
    mentions: dict[str, set[str]] = {"train": set(), "validation": set()}
    counts: dict[str, dict[str, int]] = {}
    pattern = re.compile(r"\bCVE-\d{4}-\d{4,}\b", re.IGNORECASE)

    for split in catalog["split_sets"]:
        counts[split["id"]] = {}
        for label in ("train", "validation"):
            path = root / "data" / split[f"{label}_path"]
            table = parquet.read_table(path, columns=["messages"])
            rows = table.to_pylist()
            split_ids: set[str] = set()
            for row in rows:
                messages = row["messages"]
                if not isinstance(messages, list):
                    continue
                for message in messages:
                    if not isinstance(message, dict):
                        continue
                    content = message.get("content")
                    if isinstance(content, str):
                        split_ids.update(value.upper() for value in pattern.findall(content))
            mentions[label].update(split_ids)
            counts[split["id"]][label] = len(split_ids)

    report = {
        "by_split_unique_mentions": counts,
        "train_unique_mentions": len(mentions["train"]),
        "validation_unique_mentions": len(mentions["validation"]),
        "train_validation_shared_mentions": len(
            mentions["train"] & mentions["validation"]
        ),
        "all_unique_mentions": len(mentions["train"] | mentions["validation"]),
    }
    return report, mentions


def pairwise_overlap(ids_by_source: dict[str, set[str]]) -> dict[str, dict[str, int]]:
    overlap: dict[str, dict[str, int]] = {}
    names = sorted(ids_by_source)
    for index, left in enumerate(names):
        for right in names[index + 1 :]:
            overlap[f"{left} <> {right}"] = {
                "left_unique_ids": len(ids_by_source[left]),
                "right_unique_ids": len(ids_by_source[right]),
                "shared_ids": len(ids_by_source[left] & ids_by_source[right]),
            }
    return overlap


def audit_ssh_research_data(root: Path) -> dict[str, Any]:
    data_root = (
        root
        / "repositories"
        / "github"
        / "research"
        / "SSH-Shell-Attacks"
        / "data"
    )
    files = sorted(data_root.rglob("*.parquet"))
    results: list[dict[str, Any]] = []
    for path in files:
        metadata = parquet.ParquetFile(path).metadata
        results.append(
            {
                "path": str(path.relative_to(root)),
                "bytes": path.stat().st_size,
                "rows": metadata.num_rows,
            }
        )
    return {
        "files": results,
        "row_counts_match_across_variants": len({item["rows"] for item in results}) <= 1,
        "license_status": (
            "repository has an MIT license, but the dataset-specific license and "
            "privacy/provenance terms are not established"
        ),
        "training_disposition": (
            "excluded; session logs may contain credentials or personal identifiers; "
            "do not inspect or transform until pre-scrubbed data and authorization are provided"
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[2],
        help="B13 workspace root",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Report path (default: data/interim/raw-source-audit.json)",
    )
    args = parser.parse_args()
    root = args.root.resolve()
    csv_root = root / "data" / "raw" / "csv"
    csv_reports: list[dict[str, Any]] = []
    csv_ids: dict[str, set[str]] = {}

    for path in sorted(csv_root.rglob("*.csv")):
        report, ids = audit_csv(path)
        report["path"] = str(path.relative_to(root))
        csv_reports.append(report)
        if ids:
            csv_ids[path.name] = ids

    cvelist_report, cvelist_ids, published_cvelist_ids = audit_cvelist(root, csv_ids)
    cve_sft_ids = read_cve_sft_ids(root)
    sft_all_ids = cve_sft_ids["train"] | cve_sft_ids["validation"]
    sft_mentions_report, sft_mentions = read_cve_mentions_from_sft(root)
    all_sft_mentions = sft_mentions["train"] | sft_mentions["validation"]
    cvelist_report["published_ids_mentioned_in_registered_sft"] = len(
        published_cvelist_ids & all_sft_mentions
    )
    cvelist_report["published_ids_available_for_new_raw_cve_sft"] = len(
        published_cvelist_ids - all_sft_mentions
    )

    report = {
        "schema_version": 1,
        "method": {
            "csv_parser": "Python csv.DictReader with multiline fields enabled and expanded field-size limit",
            "raw_record_text_emitted": False,
            "source_files_modified": False,
            "toolset_zip_opened": False,
        },
        "csv_sources": csv_reports,
        "cvelist_v5": cvelist_report,
        "cve_source_overlap": {
            "csv_pairwise": pairwise_overlap(csv_ids),
            "with_existing_cve_sft": {
                "train_unique_ids": len(cve_sft_ids["train"]),
                "validation_unique_ids": len(cve_sft_ids["validation"]),
                "train_validation_overlap": len(
                    cve_sft_ids["train"] & cve_sft_ids["validation"]
                ),
                "cvelist_ids_already_in_sft": len(cvelist_ids & sft_all_ids),
                "cvelist_ids_outside_sft": len(cvelist_ids - sft_all_ids),
                "csv_source_ids_already_in_sft": {
                    name: len(ids & sft_all_ids) for name, ids in sorted(csv_ids.items())
                },
                "cvelist_sft_train_validation_ids": {
                    "train_ids_in_cvelist": len(cve_sft_ids["train"] & cvelist_ids),
                    "validation_ids_in_cvelist": len(cve_sft_ids["validation"] & cvelist_ids),
                },
                "cve_mentions_across_registered_sft": sft_mentions_report,
            },
            "training_policy": (
                "Do not add any raw-derived CVE example for an ID already present "
                "in the existing CVE SFT train or validation splits."
            ),
        },
        "ssh_research_data": audit_ssh_research_data(root),
        "source_disposition": {
            "cvelistV5": {
                "use": "eligible for local derived SFT from PUBLISHED records after applying attribution",
                "terms_url": "https://www.cve.org/Legal/TermsOfUse",
                "requirements": "CVE Usage grants reproduction and derivative-work rights; reproduce MITRE's copyright designation and the license in copies.",
                "third_party_note": "CNA-provided records and external references may carry additional rights or terms; review per-source attribution before redistribution.",
            },
            "KDDTest.csv": "evaluation-only benchmark; exclude from training",
            "unclassified/final_dataset.csv": "exclude pending source, license, and content review",
            "data.zip": "participant user-action logs; exclude pending privacy, consent, and provenance review",
            "toolset.zip": "not opened; archive listing contains a .env entry",
            "SSH-Shell-Attacks dataset": (
                "excluded; only Parquet footer metadata was read after session-log "
                "schema indicated possible credential or personal-identifier content"
            ),
            "PDF papers and guidance": "reference material only; do not convert document text into SFT examples without rights and source-dataset verification",
            "Git repositories": "upstream schemas, code, and references; not direct SFT examples",
        },
    }
    output = args.output or root / "data" / "interim" / "raw-source-audit.json"
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "report": str(output),
                "csv_files": len(csv_reports),
                "cvelist_record_files": report["cvelist_v5"]["record_files"],
                "cvelist_unique_ids": report["cvelist_v5"]["unique_cve_ids"],
                "csv_records": {
                    item["path"]: item["records"] for item in csv_reports
                },
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
