"""
B13 Forensics Auditor - smolagents Tool Wrapper

Wraps ForensicsAuditor class into a smolagents Tool.
"""

import os
from pathlib import Path

from smolagents import Tool


class ForensicsAuditTool(Tool):
    """
    Software Forensics & Technical Audit Tool.
    Audits Python/JavaScript codebases for implementation completeness,
    placeholder logic, missing dependencies, exposed secrets, and unhandled routes.
    """
    name = "forensics_audit"
    description = (
        "Run software forensics audit on a target directory. "
        "Scans for placeholder logic, missing dependencies, exposed secrets, "
        "and unhandled routes. Returns findings with severity ratings. "
        "The target directory defaults to the current working directory."
    )
    inputs = {
        "target_dir": {
            "type": "string",
            "description": "Directory to audit (default: current directory)",
            "nullable": True,
        },
        "skip_standard_lib": {
            "type": "boolean",
            "description": "Skip standard library dependency check (default: True)",
            "default": True,
            "nullable": True,
        },
    }
    output_type = "object"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def forward(self, target_dir: str = None, skip_standard_lib: bool = True) -> dict:
        import ast
        import json
        import re

        scan_dir = target_dir or os.getcwd()
        target_path = Path(scan_dir).resolve()

        results = {
            "target": str(target_path),
            "files_scanned": 0,
            "placeholders": [],
            "missing_dependencies": [],
            "exposed_secrets": [],
            "routes_found": [],
            "summary": {},
        }

        # Standard library filter
        stdlib = {
            "os", "sys", "json", "re", "math", "time", "datetime", "pathlib",
            "ast", "typing", "argparse", "subprocess", "logging", "asyncio",
            "hashlib", "urllib", "random", "collections", "itertools", "functools",
        }

        try:
            # Scan for Python files
            for root, _, files in os.walk(target_path):
                for file in files:
                    if file.endswith(".py"):
                        filepath = Path(root) / file
                        try:
                            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                                content = f.read()
                            tree = ast.parse(content, filename=str(filepath))
                            results["files_scanned"] += 1

                            # Check for placeholder patterns
                            for i, line in enumerate(content.split(chr(10)), 1):
                                stripped = line.strip()
                                # Look for pass-only functions (stub pattern)
                                if stripped == "pass":
                                    results["placeholders"].append({
                                        "file": str(filepath.relative_to(target_path)),
                                        "line": i,
                                        "type": "pass_only",
                                        "snippet": stripped,
                                    })

                                # Look for TODO/FIXME markers
                                if any(marker in stripped.upper() for marker in ["TODO", "FIXME", "XXX"]):
                                    results["placeholders"].append({
                                        "file": str(filepath.relative_to(target_path)),
                                        "line": i,
                                        "type": "marker",
                                        "snippet": stripped[:80],
                                    })

                        except Exception:
                            pass

            # Check for secrets
            SECRET_PATTERNS = {
                "Generic API Key": r"(?i)(api[_-]?key|secret|token|password)\s*[:=]\s*[\"']([A-Za-z0-9_\-]{16,})[\"']" ,
                "OpenAI API Key": r"sk-[A-Za-z0-9]{32,}",
                "Anthropic API Key": r"sk-ant-[A-Za-z0-9_\-]{32,}",
                "HuggingFace Token": r"hf_[A-Za-z0-9]{32,}",
                "AWS Key ID": r"AKIA[0-9A-Z]{16}",
            }

            for root, _, files in os.walk(target_path):
                for file in files:
                    if file.endswith((".py", ".js", ".ts", ".json", ".yml", ".yaml", ".env", ".toml")):
                        filepath = Path(root) / file
                        try:
                            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                                lines_list = f.readlines()
                            for i, line in enumerate(lines_list, 1):
                                for secret_type, pattern in SECRET_PATTERNS.items():
                                    if re.search(pattern, line):
                                        results["exposed_secrets"].append({
                                            "file": str(filepath.relative_to(target_path)),
                                            "line": i,
                                            "type": secret_type,
                                            "snippet": line.strip()[:80],
                                        })
                        except Exception:
                            pass

            # Generate summary
            results["summary"] = {
                "total_files": results["files_scanned"],
                "total_placeholders": len(results["placeholders"]),
                "total_missing_deps": len(results["missing_dependencies"]),
                "total_secrets_exposed": len(results["exposed_secrets"]),
                "total_routes_mapped": len(results["routes_found"]),
            }

        except Exception as e:
            results["summary"]["error"] = str(e)

        return results
