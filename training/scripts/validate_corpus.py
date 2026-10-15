#!/usr/bin/env python3
"""Validate + score the B13 SFT corpus for training strength.

Scope: STRUCTURAL QUALITY ONLY. Never filters or censors content (no
"restrictions inside the training"). Flags/can-drop only malformed rows (bad JSON,
missing/empty messages, invalid roles, non-text content). Everything else is kept
and measured. Report: data/interim/corpus_quality_report.json
"""
from __future__ import annotations
import argparse, json, re
from collections import Counter
from pathlib import Path

VALID_ROLES = {"system", "user", "assistant", "tool"}
TOOL_EXEC_SOURCES = {"cve_funcs_tool_execution_sft", "cve_tool_execution_sft"}
CODE_FENCE = re.compile(r"```(?:py|python)?\s*\n(.*?)```", re.DOTALL)
OBS = re.compile(r"<observation>.*?</observation>", re.DOTALL)
FINAL = re.compile(r"\bfinal_answer\s*\(")


def check_row(rec: dict) -> tuple[list[str], dict]:
    defects: list[str] = []
    sig = {"n_msgs": 0, "roles": [], "tool_exec": False, "has_code": False,
           "has_obs": False, "has_final": False, "starts_system": False}
    src = rec.get("source")
    msgs = rec.get("messages")
    if not isinstance(msgs, list) or not msgs:
        return (["no_messages"], sig)
    sig["n_msgs"] = len(msgs)
    sig["starts_system"] = (isinstance(msgs[0], dict) and msgs[0].get("role") == "system")
    sig["tool_exec"] = src in TOOL_EXEC_SOURCES
    prev_role = None
    for i, m in enumerate(msgs):
        if not isinstance(m, dict):
            defects.append(f"msg_{i}_not_dict"); continue
        role = m.get("role"); content = m.get("content")
        sig["roles"].append(role)
        if role not in VALID_ROLES:
            defects.append(f"msg_{i}_bad_role")
        if not isinstance(content, str) or not content.strip():
            defects.append(f"msg_{i}_empty_content"); prev_role = role; continue
        if role == "assistant":
            if CODE_FENCE.search(content): sig["has_code"] = True
            if OBS.search(content): sig["has_obs"] = True
            if FINAL.search(content): sig["has_final"] = True
        if role == prev_role and role == "assistant":
            defects.append("consecutive_assistant")
        prev_role = role
    if sig["tool_exec"] and not sig["has_final"]:
        defects.append("tool_exec_no_final_answer")
    return defects, sig


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", type=Path,
                    default=Path(__file__).resolve().parents[2] / "data/exports/b13-agent-full/train.jsonl")
    ap.add_argument("--output", type=Path,
                    default=Path(__file__).resolve().parents[2] / "data/interim/corpus_quality_report.json")
    ap.add_argument("--context-lengths", type=int, nargs="+", default=[2048, 8192])
    args = ap.parse_args()

    total = clean = rows_with_defects = 0
    defect_counter: Counter[str] = Counter()
    source_counter: Counter[str] = Counter()
    role_counter: Counter[str] = Counter()
    sys_prompts: Counter[str] = Counter()
    grounding = {"tool_exec_with_obs": 0, "tool_exec_total": 0, "tool_exec_with_final": 0}
    over = {L: 0 for L in args.context_lengths}
    chars = []

    with args.input.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            total += 1
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                defect_counter["json_decode_error"] += 1; rows_with_defects += 1; continue
            source_counter[rec.get("source", "<none>")] += 1
            defects, sig = check_row(rec)
            for r in sig["roles"]:
                role_counter[r] += 1
            if defects:
                rows_with_defects += 1
                for d in defects:
                    defect_counter[re.sub(r"_\d+", "_N", d).split(":")[0]] += 1
            else:
                clean += 1
            msgs = rec.get("messages") or []
            if msgs and isinstance(msgs[0], dict) and msgs[0].get("role") == "system":
                sys_prompts[msgs[0]["content"][:80]] += 1
            if sig["tool_exec"]:
                grounding["tool_exec_total"] += 1
                if sig["has_obs"]: grounding["tool_exec_with_obs"] += 1
                if sig["has_final"]: grounding["tool_exec_with_final"] += 1
            clen = sum(len(m.get("content", "")) for m in msgs if isinstance(m, dict))
            chars.append(clen)
            for L in args.context_lengths:
                if clen / 4.0 > L: over[L] += 1

    chars.sort()
    pct = lambda p: chars[int(len(chars) * p)] if chars else 0
    report = {
        "input": str(args.input), "total_rows": total, "clean_rows": clean,
        "rows_with_defects": rows_with_defects,
        "clean_pct": round(100.0 * clean / total, 3) if total else 0.0,
        "defect_classes": dict(defect_counter.most_common()),
        "source_distribution": dict(source_counter.most_common()),
        "role_counts": dict(role_counter.most_common()),
        "distinct_system_prompt_prefixes": len(sys_prompts),
        "top_system_prompts": sys_prompts.most_common(5),
        "grounding": grounding,
        "char_length": {"p50": pct(0.50), "p95": pct(0.95), "p99": pct(0.99), "max": chars[-1] if chars else 0},
        "approx_over_context_tokens": over,
        "note": "structural quality only; no content filtering/censoring applied",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in
                      ["total_rows", "clean_rows", "rows_with_defects", "clean_pct",
                       "defect_classes", "distinct_system_prompt_prefixes",
                       "grounding", "approx_over_context_tokens"]}, indent=2))


if __name__ == "__main__":
    main()

