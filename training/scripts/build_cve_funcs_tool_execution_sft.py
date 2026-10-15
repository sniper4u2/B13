#!/usr/bin/env python3
"""
Build CVE-Funcs Tool-Execution SFT Dataset for the B13 Agent.

Streams the large cve_funcs.csv (real vulnerable/fixed code pairs) and converts
each into a smolagents tool-execution trajectory that teaches the agent to call
its REAL tools: forensics_audit, vulnerability_scan, c2_cve_exploit_execute,
metasploit_search, final_answer.

DESIGN RULE (no fabrication): the assistant trajectory contains ONLY tool CALLS
(Thought + ```py Code blocks). It never invents Observation output or fake
results. The vulnerable code itself is REAL (extracted from the CSV); runtime
Observations come from the actual tools.

Usage:
    python3 build_cve_funcs_tool_execution_sft.py \
        --src ./cve_funcs.csv --out <out.parquet> --limit 5000
"""
import argparse
import json
import os
from typing import Optional, List, Dict, Any

import pandas as pd

BASE_TOOLS = [
    "forensics_audit", "vulnerability_scan", "port_scan",
    "c2_cve_exploit_execute", "metasploit_search", "metasploit_execute",
    "c2_generate_payload", "final_answer",
]

SYSTEM_PROMPT = (
    "You are B13, an autonomous cybersecurity AI agent (Clearance 55). "
    "You solve tasks by writing Python code that calls your security tools: "
    + ", ".join(BASE_TOOLS) + ". "
    "Plan in Thought, emit Code inside a ```py block that calls the tools, read "
    "the real Observations, and finish with final_answer(). Never fabricate "
    "tool output."
)


def _unescape(s: str) -> str:
    if not isinstance(s, str):
        return ""
    try:
        return s.encode("utf-8", "ignore").decode("unicode_escape")
    except Exception:
        return s


def extract_func(content: str, rng: str) -> Optional[str]:
    if not isinstance(rng, str) or "," not in rng:
        return None
    try:
        a, b = [int(x) for x in rng.split(",")]
    except ValueError:
        return None
    lines = _unescape(content).split("\n")
    if b > len(lines) or a < 1 or b <= a:
        return None
    return "\n".join(lines[a - 1:b]).strip()


def _cve(v) -> str:
    s = str(v).strip().strip('"').strip()
    return s if s and s.lower() != "nan" else "CVE-UNKNOWN"


def _s(v, default="unknown") -> str:
    if v is None:
        return default
    try:
        if isinstance(v, float) and pd.isna(v):
            return default
    except Exception:
        pass
    s = str(v).strip()
    return s if s and s.lower() != "nan" else default


def clip(code: str, n: int = 1200) -> str:
    code = code.strip()
    return code if len(code) <= n else code[:n] + "\n// ... (truncated)"


def build_user_task(cve, lang, func, fpath, repo) -> str:
    return (
        f"Perform a forensic code audit of a known-vulnerable function and "
        f"verify exploitability.\n"
        f"- CVE: {cve}\n- Language: {lang}\n- Function: `{func}`\n"
        f"- File: {fpath}\n- Repo: {repo}\n\n"
        f"Steps: (1) forensics_audit the function to classify the flaw, "
        f"(2) vulnerability_scan to rate severity, "
        f"(3) c2_cve_exploit_execute to check exploitability, "
        f"(4) metasploit_search for a matching module, then report with the fix."
    )


def build_trajectory(cve, lang, func, fpath, repo, vuln_code, fix_msg) -> str:
    target = "10.10.0.5"
    vc = clip(vuln_code)
    fix = _s(fix_msg, "Apply the upstream security patch.").split("\n")[0][:200]
    cve = _cve(cve)
    steps: List[str] = []
    # Step 1: forensic audit (the vulnerable code is REAL, passed as input)
    steps.append(
        "Thought: I'll audit the vulnerable function to classify the flaw type "
        "and severity.\n"
        "Code:\n"
        "```py\n"
        "audit = forensics_audit(target_dir='.', skip_standard_lib=True)\n"
        f"vuln_code = '''{vc}'''\n"
        "print({'audit': audit, 'function_under_review': vuln_code})\n"
        "```"
    )
    # Step 2: vulnerability scan / classify
    steps.append(
        "Thought: Now I'll rate the severity of the flaw.\n"
        "Code:\n"
        "```py\n"
        f'finding = vulnerability_scan(target="{target}")\n'
        "print(finding)\n"
        "```"
    )
    # Step 3: C2 exploitability
    steps.append(
        "Thought: I'll verify exploitability of the CVE via the C2 server.\n"
        "Code:\n"
        "```py\n"
        f'exploit_check = c2_cve_exploit_execute(cve_id="{cve}", target="{target}")\n'
        "print(exploit_check)\n"
        "```"
    )
    # Step 4: metasploit module search
    steps.append(
        "Thought: I'll look for a reference Metasploit module for this flaw.\n"
        "Code:\n"
        "```py\n"
        f'mods = metasploit_search(search_term="{lang}")\n'
        "print(mods)\n"
        "```"
    )
    # Final answer - grounded in REAL CVE metadata + the fix message from the CSV
    final = {
        "cve": cve,
        "language": lang,
        "function": func,
        "file": fpath,
        "repo": repo,
        "vulnerable_code": vc,
        "methodology": [
            "forensics_audit", "vulnerability_scan",
            "c2_cve_exploit_execute", "metasploit_search",
        ],
        "fix_summary": fix,
        "verdict_pending_runtime": (
            f"{cve} in {func} ({lang}); confirm exploitability from live tool "
            f"Observations, then apply upstream fix."
        ),
    }
    steps.append(
        "Thought: I've audited the flaw, rated it, and checked exploitability. "
        "I'll compile the report from the Observations.\n"
        "Code:\n```py\n"
        "final_answer(" + json.dumps(final) + ")\n"
        "```"
    )
    return "\n".join(steps)


def build_records(df: pd.DataFrame) -> List[Dict[str, Any]]:
    records = []
    for _, row in df.iterrows():
        cve = _cve(row.get("cve_id"))
        lang = _s(row.get("language"), "unknown")
        func = _s(row.get("function_name"), "unknown")
        fpath = _s(row.get("file_path"), "")
        repo = _s(row.get("repo_url"), "")
        vuln_code = extract_func(row.get("before_file_content"),
                                 row.get("before_function_range"))
        if not vuln_code or len(vuln_code) < 20:
            continue
        fix_msg = row.get("message")
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_task(cve, lang, func, fpath, repo)},
            {"role": "assistant", "content": build_trajectory(cve, lang, func, fpath, repo, vuln_code, fix_msg)},
        ]
        records.append({
            "id": f"CF-{len(records):06d}",
            "cve_id": cve,
            "language": lang,
            "messages": messages,
        })
    return records


def convert(src, out, limit=None, chunk_size=2000):
    usecols = ["cve_id", "language", "file_path", "function_name",
               "before_file_content", "before_function_range", "message", "repo_url"]
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    if os.path.exists(out):
        os.remove(out)

    import pyarrow as pa
    import pyarrow.parquet as pq

    reader = pd.read_csv(src, usecols=usecols, chunksize=chunk_size,
                         on_bad_lines="skip", low_memory=False)
    writer = None
    written = 0
    for chunk in reader:
        if limit and written >= limit:
            break
        records = build_records(chunk)
        if limit:
            room = limit - written
            records = records[:room]
        if records:
            table = pa.Table.from_pylist(records)
            if writer is None:
                writer = pq.ParquetWriter(out, table.schema)
            writer.write_table(table)
            written += len(records)
    if writer is not None:
        writer.close()
    print(f"[+] Wrote {written:,} tool-execution trajectories -> {out}")
    return written


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="./cve_funcs.csv")
    ap.add_argument("--out", default="b13_agent/data/processed/cve_funcs_tool_execution_sft.parquet")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--chunk-size", type=int, default=2000)
    args = ap.parse_args()
    convert(args.src, args.out, args.limit, args.chunk_size)
