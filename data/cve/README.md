# Unified CVE collection

Use this directory as the single entrypoint for B13 CVE material. It groups
different source formats while keeping their original schemas separate:

- `raw-records/` — CVE List V5 repository; the records are under `cves/`.
- `references/` — CVE reference-ingest source data.
- `source-tables/` — CPE, NVD, KEV, combined-CVE, and fix-pair CSV sources.
- `sft-variants/` — alternative processed vulnerability SFT versions and
  train/validation splits.
- `selected-sft.parquet` — the current single SFT candidate,
  `cve_sft_enhanced_v3.parquet`, selected by the existing dataset catalog.

The four 10,000-row SFT versions have identical `cve_id` sets. They are
alternative transformations and must not be concatenated as independent
examples. The selected SFT file has ChatML `messages`; the older v5 file
requires serialization before fine-tuning. Keep raw records, source CSVs, and
SFT examples separate because their schemas and provenance differ.
