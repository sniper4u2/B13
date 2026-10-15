# Repository collection

All 16 clean Git clones have been grouped under `repositories/github/`.
Repository working trees and `.git` metadata were moved intact; root-level
symlinks preserve former paths. The CVEProject repositories remain siblings in
one directory so relative sibling-project dependencies keep working.

## CVE Project

Located in `github/CVEProject/`:

- `automation-working-group`
- `consumer-working-group`
- `cve-core`
- `cve-documents`
- `cvelistV5` — raw CVE record source
- `cveproject.github.io`
- `cve-reference-ingest-data` — reference-data source
- `CVE-Search-API`
- `cve-services`
- `cve-user-registry-client`
- `cve-validation-library`
- `CVE-Validation-Library-CLI-Example`
- `cve-website`
- `frontier-ai-researcher-cnas-pilot`
- `researcher-working-group`

## Research

Located in `github/research/`:

- `SSH-Shell-Attacks` — research repository with data, notebooks, and reports.

Each working tree had a clean Git status before and after relocation.

| Repository | Branch | Checked-out commit | Origin |
| --- | --- | --- | --- |
| `automation-working-group` | `master` | `77daab5f2` | `https://github.com/CVEProject/automation-working-group` |
| `consumer-working-group` | `main` | `78d1a1d` | `https://github.com/CVEProject/consumer-working-group` |
| `cve-core` | `dev` | `dfdfc13` | `https://github.com/CVEProject/cve-core` |
| `cve-documents` | `master` | `0ed1fba` | `https://github.com/CVEProject/cve-documents` |
| `cvelistV5` | `main` | `bf24876406c` | `https://github.com/CVEProject/cvelistV5` |
| `cveproject.github.io` | `master` | `edf6d28` | `https://github.com/CVEProject/cveproject.github.io` |
| `cve-reference-ingest-data` | `main` | `6e5c8e6de` | `https://github.com/CVEProject/cve-reference-ingest-data` |
| `CVE-Search-API` | `main` | `d09aa0d` | `https://github.com/CVEProject/CVE-Search-API` |
| `cve-services` | `dev` | `cc941221` | `https://github.com/CVEProject/cve-services` |
| `cve-user-registry-client` | `dev` | `2b6e3f3` | `https://github.com/CVEProject/cve-user-registry-client` |
| `cve-validation-library` | `main` | `24c431d` | `https://github.com/CVEProject/cve-validation-library` |
| `CVE-Validation-Library-CLI-Example` | `main` | `c0a9fbf` | `https://github.com/CVEProject/CVE-Validation-Library-CLI-Example` |
| `cve-website` | `dev` | `00fd29e2` | `https://github.com/CVEProject/cve-website` |
| `frontier-ai-researcher-cnas-pilot` | `main` | `9f46173` | `https://github.com/CVEProject/frontier-ai-researcher-cnas-pilot` |
| `researcher-working-group` | `main` | `8be8608` | `https://github.com/CVEProject/researcher-working-group` |
| `SSH-Shell-Attacks` | `main` | `3fabb73` | `https://github.com/eliainnocenti/SSH-Shell-Attacks` |

Verify a repository with
`git -C repositories/github/CVEProject/cvelistV5 status --short --branch`.
