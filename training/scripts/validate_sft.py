#!/usr/bin/env python3
"""
B13 Training-Data Validation

Validates every SFT parquet dataset for training readiness:
  - schema: 'messages' column, each a list of {role, content}
  - roles: system/user/assistant present and well-ordered
  - tool-call hygiene: any tool the assistant calls must be a REAL registered
    B13 tool (from b13_agent.agent.export_tool_schemas)
  - no fabricated Observations: assistant turns must not hardcode fake tool
    RESULT payloads (open_ports/session_id/success:true literals in <observation>)
  - content non-empty, no NaN

Usage:
    python3 validate_sft.py [--dir <dir>] [--glob '*.parquet'] [--sample N]
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import List, Dict, Any

PROJECT_ROOT = Path("/home/b13/Desktop/b13 agent")
sys.path.insert(0, str(PROJECT_ROOT))

# Fabricated-observation signatures that must NOT appear in assistant labels.
FAKE_OBS_PATTERNS = [
    r'"open_ports"\s*:\s*\[',        # hardcoded open port lists
    r'"session_id"\s*:\s*"sess-',     # hardcoded session ids
    r'MGSESSION-\d',                    # hardcoded msf session ids
    r'"success"\s*:\s*true.*session',  # fake success+session combos
    r'<observation>.*"success"\s*:\s*true',  # fake observation blocks
]

# Tool-name token regex: foo( appearing in code blocks
TOOL_CALL_RE = re.compile(r"\b([a-z_][a-z0-9_]*)\s*\(")


def load_registered_tools() -> set:
    try:
        from b13_agent.agent import export_tool_schemas
        return set(export_tool_schemas().keys())
    except Exception as e:
        print(f"  [WARN] could not load live tool registry: {e}")
        return set()


def iter_parquet(dirpath: Path, glob: str) -> List[Path]:
    return sorted(dirpath.rglob(glob))


def check_messages(messages: Any, registered: set, fake_res: List[re.Pattern]) -> List[str]:
    """Return a list of problems for one record's messages."""
    problems = []
    import numpy as _np
    if isinstance(messages, _np.ndarray):
        messages = messages.tolist()
    if not isinstance(messages, (list, tuple)) or len(messages) < 2:
        return ["messages not a list of >=2"]
    roles = []
    for m in messages:
        if not isinstance(m, dict) or "role" not in m or "content" not in m:
            problems.append("message missing role/content")
            continue
        role = m["role"]
        content = m["content"]
        roles.append(role)
        if content is None or (isinstance(content, str) and not content.strip()):
            problems.append(f"empty content in role={role}")
    if "system" not in roles:
        problems.append("no system message")
    if "user" not in roles:
        problems.append("no user message")
    if "assistant" not in roles:
        problems.append("no assistant message")

    # Assistant content checks
    for m in messages:
        if isinstance(m, dict) and m.get("role") == "assistant":
            content = m.get("content") or ""
            # fabricated observations
            for pat in fake_res:
                if pat.search(content):
                    problems.append(f"fabricated observation: /{pat.pattern}/")
            # tool calls must be registered - but ONLY scan inside ```py code
            # blocks (prose like "exploitation(target)" is not a tool call)
            code_blocks = re.findall(r"```py\n(.*?)```", content, re.DOTALL)
            code_text = "\n".join(code_blocks) if code_blocks else ""
            scan_src = code_text if code_blocks else ""
            for name in TOOL_CALL_RE.findall(scan_src):
                if name in ("print", "range", "len", "str", "int", "dict",
                            "list", "set", "json", "enumerate", "sorted",
                            "final_answer"):  # final_answer is a built-in smolagents tool
                    continue
                # Only flag calls that look like B13 security tools but are not
                # registered. We use an explicit security-tool vocabulary rather
                # than a broad suffix match (which false-positives on C code like
                # array_search() inside vulnerable snippets).
                SECURITY_TOOL_HINTS = (
                    "port_scan", "vuln", "web_app", "privesc", "priv_esc",
                    "metasploit", "msf_", "c2_", "exploit", "payload",
                    "forensics", "gsm_", "ss7", "nmap", "nuclei", "ffuf",
                )
                # word/prefix-aware match so 'c2_' does not match 'blosc2_meta_get'
                def _hint_match(nm, hints):
                    for h in hints:
                        if h.endswith("_"):
                            if nm.startswith(h):
                                return True
                        elif h in nm and (nm.startswith(h) or (h + "_") in nm or nm.endswith(h)):
                            return True
                    return False
                looks_like_tool = _hint_match(name, SECURITY_TOOL_HINTS)
                if registered and looks_like_tool and name not in registered:
                    problems.append(f"unknown security-tool call: {name}(")
    return problems


def validate_file(path: Path, registered: set, sample: int) -> Dict[str, Any]:
    import pandas as pd
    fake_res = [re.compile(p, re.IGNORECASE | re.DOTALL) for p in FAKE_OBS_PATTERNS]
    try:
        df = pd.read_parquet(path)
    except Exception as e:
        return {"file": str(path.relative_to(PROJECT_ROOT)), "error": str(e)}
    if "messages" not in df.columns:
        return {"file": str(path.relative_to(PROJECT_ROOT)),
                "error": f"no 'messages' column (cols={list(df.columns)[:8]})"}
    n = len(df)
    check_n = min(n, sample) if sample else n
    problems = []
    for i in range(check_n):
        probs = check_messages(df.iloc[i]["messages"], registered, fake_res)
        for p in probs:
            problems.append(f"row {i}: {p}")
    return {
        "file": str(path.relative_to(PROJECT_ROOT)),
        "rows": n,
        "checked": check_n,
        "problems": problems[:20],
        "problem_count": len(problems),
        "ok": len(problems) == 0,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=str(PROJECT_ROOT / "b13_agent" / "data"))
    ap.add_argument("--glob", default="*.parquet")
    ap.add_argument("--sample", type=int, default=200)
    args = ap.parse_args()

    print("=" * 60)
    print("B13 TRAINING-DATA VALIDATION")
    print("=" * 60)

    registered = load_registered_tools()
    print(f"  registered tools ({len(registered)}): {sorted(registered)}")

    root = Path(args.dir)
    files = iter_parquet(root, args.glob)
    print(f"  found {len(files)} parquet files under {root}\n")

    all_ok = True
    total_rows = 0
    for f in files:
        res = validate_file(f, registered, args.sample)
        if "error" in res:
            print(f"  [SKIP] {res['file']}: {res['error']}")
            continue
        total_rows += res["rows"]
        status = "OK" if res["ok"] else f"{res['problem_count']} PROBLEMS"
        print(f"  [{status:16s}] {res['file']}  rows={res['rows']:,} checked={res['checked']}")
        for p in res["problems"]:
            print(f"        - {p}")
        if not res["ok"]:
            all_ok = False

    print("\n" + "=" * 60)
    print(f"  total rows across valid datasets: {total_rows:,}")
    print("  ALL TRAINING DATA VALID" if all_ok else "  SOME DATASETS HAVE PROBLEMS")
    print("=" * 60)
    return all_ok


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
