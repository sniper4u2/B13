#!/usr/bin/env python3
"""
Build CVE Tool-Execution SFT Dataset for the B13 Agent.

Converts CVE records into REAL smolagents tool-execution trajectories that
teach the agent to CALL its actual registered tools:
  port_scan, c2_cve_exploit_execute, metasploit_search, metasploit_execute,
  final_answer, etc.

Output schema matches the existing SFT format: a 'messages' column with
[system, user, assistant] where the assistant emits Thought/Code sequences in
the smolagents CodeAgent format (```py ... ``` blocks that call the tools).

DESIGN RULE (no fabrication): the assistant trajectory contains ONLY tool
CALLS (Thought + Code). It never invents Observation output or fake results
(no hardcoded open_ports/session_ids). The agent learns the correct tool-call
SEQUENCE and argument shapes; real Observations are produced at runtime by the
actual tools during rollout / GRPO, not baked into SFT labels.

Usage:
    python3 build_cve_tool_execution_sft.py --src <cve.parquet> --out <out.parquet>
"""
import argparse
import json
import os
from typing import Any, List, Dict

import pandas as pd
import pyarrow.parquet as pq

# Tool names this builder is allowed to teach. Kept in sync with the agent's
# registered tools (b13_agent.agent.get_all_tools). GSM/SS7 tools are optional
# and included only if present in the live tool registry.
BASE_TOOLS = [
    "port_scan", "vulnerability_scan", "web_app_test",
    "privilege_escalation_check", "metasploit_search", "metasploit_execute",
    "metasploit_generate_payload", "metasploit_list_sessions",
    "c2_connect", "c2_cve_exploit_execute", "c2_generate_payload",
    "forensics_audit", "final_answer",
]

SYSTEM_PROMPT = (
    "You are B13, an autonomous cybersecurity AI agent (Clearance 55). "
    "You solve tasks by writing Python code that calls your security tools. "
    "Available tools: " + ", ".join(BASE_TOOLS) + ". "
    "Plan step by step in Thought, then emit Code inside a ```py block that "
    "calls the tools, then finish with final_answer(). Never fabricate tool "
    "output; rely on the Observations returned by the tools."
)


def _s(v: Any, default: str = "unknown") -> str:
    if v is None:
        return default
    try:
        if isinstance(v, float) and pd.isna(v):
            return default
    except Exception:
        pass
    s = str(v).strip()
    return s if s and s.lower() != "nan" else default


def _sev(cvss: float) -> str:
    try:
        cvss = float(cvss)
    except (TypeError, ValueError):
        return "unknown"
    if cvss >= 9.0:
        return "critical"
    if cvss >= 7.0:
        return "high"
    if cvss >= 4.0:
        return "medium"
    if cvss > 0:
        return "low"
    return "none"


def _search_term(sw: str) -> str:
    sw = _s(sw, "remote")
    return sw.replace("_", " ").split()[0] if sw.split() else "remote"


def build_user_task(row: dict, target: str) -> str:
    cve = _s(row.get("cve_id"), "CVE-UNKNOWN")
    sw = _s(row.get("affected_software"), "the target service")
    ver = _s(row.get("affected_versions"), "*")
    cvss = row.get("cvss_score", "N/A")
    return (
        f"Investigate and attempt controlled exploitation of {cve} affecting "
        f"{sw} (versions {ver}), CVSS {cvss}. Target host: {target}. "
        f"Use your tools to: (1) confirm the target is reachable, "
        f"(2) verify {cve} exploitability via the C2 server, "
        f"(3) search Metasploit for a matching module, then (4) report findings."
    )


def build_assistant_trajectory(row: dict, target: str = "10.10.0.5") -> str:
    """
    Build a multi-step smolagents trajectory of Thought + Code tool CALLS.
    NO fabricated Observations. Real Observations come from the tools at runtime.
    """
    cve = _s(row.get("cve_id"), "CVE-UNKNOWN")
    sw = _s(row.get("affected_software"), "target")
    ver = _s(row.get("affected_versions"), "*")
    cvss = row.get("cvss_score", "N/A")
    sev = _sev(row.get("cvss_score"))
    cwe = _s(row.get("cwe_id"), "CWE-unknown")
    st = _search_term(sw)

    steps: List[str] = []
    # Step 1: reachability / exposure
    steps.append(
        "Thought: I need to confirm the target service is reachable and identify "
        f"exposed ports before exploiting {cve}. I'll start with a port scan.\n"
        "Code:\n"
        "```py\n"
        f'scan = port_scan(target="{target}", ports="1-65535")\n'
        "print(scan)\n"
        "```"
    )
    # Step 2: C2 exploitability check
    steps.append(
        "Thought: Now I'll query the C2 server to verify exploitability of "
        f"{cve} against {sw}.\n"
        "Code:\n"
        "```py\n"
        f'exploit_check = c2_cve_exploit_execute(cve_id="{cve}", target="{target}")\n'
        "print(exploit_check)\n"
        "```"
    )
    # Step 3: metasploit module search
    steps.append(
        "Thought: Let me cross-reference with a public Metasploit module "
        f"matching {sw}.\n"
        "Code:\n"
        "```py\n"
        f'mods = metasploit_search(search_term="{st}")\n'
        "print(mods)\n"
        "```"
    )
    # Step 4: conditional execute (agent decides from real Observations)
    steps.append(
        "Thought: If the C2 check and module search confirm exploitability, "
        f"I'll execute the matched module against {target}. Otherwise I'll "
        "report non-exploitability.\n"
        "Code:\n"
        "```py\n"
        "# Execute only if prior Observations confirm exploitability\n"
        "if exploit_check.get('result', {}).get('success') and mods.get('count', 0) > 0:\n"
        '    session = metasploit_execute(exploit_name=mods["modules"][0]["full_name"], '
        f'target="{target}", options={{"RHOSTS": "{target}"}})\n'
        "    print(session)\n"
        "else:\n"
        "    session = {'status': 'skipped', 'reason': 'not confirmed exploitable'}\n"
        "```"
    )
    # Final answer - grounded in the REAL CVE metadata (not fabricated runtime data)
    final = {
        "cve": cve,
        "software": sw,
        "versions": ver,
        "cvss": str(cvss),
        "severity": sev,
        "cwe": cwe,
        "target": target,
        "methodology": [
            "port_scan", "c2_cve_exploit_execute",
            "metasploit_search", "metasploit_execute",
        ],
        "verdict_pending_runtime": (
            f"{cve} ({sev}) against {sw} {ver}; confirm exploitation from "
            f"live tool Observations before declaring success."
        ),
    }
    steps.append(
        "Thought: I've gathered reachability, C2 exploitability, and module "
        "data. I'll compile the findings from the Observations.\n"
        "Code:\n"
        "```py\n"
        "final_answer(" + json.dumps(final) + ")\n"
        "```"
    )
    return "\n".join(steps)


def build_records(df: pd.DataFrame, target: str = "10.10.0.5") -> List[Dict[str, Any]]:
    """Convert a CVE dataframe into tool-execution SFT records."""
    records = []
    for i, row in df.iterrows():
        d = row.to_dict()
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_task(d, target)},
            {"role": "assistant", "content": build_assistant_trajectory(d, target)},
        ]
        records.append({
            "id": _s(d.get("id"), f"TOOL-{len(records):06d}"),
            "cve_id": _s(d.get("cve_id"), "CVE-UNKNOWN"),
            "messages": messages,
        })
    return records


def convert(src: str, out: str, limit: int = None, target: str = "10.10.0.5"):
    pf = pq.ParquetFile(src)
    total = pf.metadata.num_rows
    print(f"[+] Source: {src}  rows={total:,}")

    cols = [c for c in ["id", "cve_id", "published_date", "cvss_score",
                        "cvss_vector", "cwe_id", "affected_software",
                        "affected_versions"] if c in pf.schema_arrow.names]
    df = pd.read_parquet(src, columns=cols)
    if limit:
        df = df.head(limit)

    records = build_records(df, target)
    out_df = pd.DataFrame(records)
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    out_df.to_parquet(out, index=False)
    print(f"[+] Wrote {len(out_df):,} tool-execution trajectories -> {out}")

    sample = json.dumps(out_df.iloc[0]["messages"])
    tools_called = [t for t in BASE_TOOLS if t + "(" in sample]
    print(f"[+] Sample tools called: {tools_called}")
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--target", default="10.10.0.5")
    args = ap.parse_args()
    convert(args.src, args.out, args.limit, args.target)
