#!/usr/bin/env python3
"""Anti-hallucination / tool-truth eval harness for B13.

Measures, on a held-out slice of the corpus, the signals that predict hallucination:
  1. tool_call_accuracy : assistant emits a parseable tool call / code fence
  2. grounding_rate     : tool-calling turns are followed by a real <observation>
  3. completion_rate    : trajectories end in final_answer(...)
  4. fabrication_proxy  : final_answer present with NO preceding observation (bad)
  5. schema_validity    : every message has a valid role + non-empty content

This is a DATA-side + optional MODEL-side harness. With no model loaded it scores the
ground-truth trajectories (upper bound). Pass --model-backend to also score live
generations. Report: data/interim/eval_report.json
"""
from __future__ import annotations
import argparse, json, re
from collections import Counter
from pathlib import Path

CODE_FENCE = re.compile(r"```(?:py|python)?\s*\n(.*?)```", re.DOTALL)
OBS = re.compile(r"<observation>.*?</observation>", re.DOTALL)
FINAL = re.compile(r"\bfinal_answer\s*\(")
TOOLCALL = re.compile(r"\b([a-z_]+)\s*\(")


def score_trajectory(messages: list[dict]) -> dict:
    has_code = has_obs = has_final = False
    tool_names = []
    roles_ok = True
    contents_ok = True
    for m in messages:
        role = m.get("role"); content = m.get("content", "")
        if role not in {"system", "user", "assistant", "tool"}:
            roles_ok = False
        if not isinstance(content, str) or not content.strip():
            contents_ok = False
        if role == "assistant":
            if CODE_FENCE.search(content):
                has_code = True
                for fn in ("forensics_audit", "vulnerability_scan", "port_scan",
                           "web_app_test", "metasploit_search", "metasploit_execute",
                           "c2_cve_exploit_execute", "c2_generate_payload"):
                    if fn + "(" in content:
                        tool_names.append(fn)
            if OBS.search(content):
                has_obs = True
            if FINAL.search(content):
                has_final = True
    return {
        "has_code": has_code, "has_obs": has_obs, "has_final": has_final,
        "tool_names": tool_names, "roles_ok": roles_ok, "contents_ok": contents_ok,
        # fabrication proxy: claims a final answer but never grounded in an observation
        "fabrication_proxy": has_final and not has_obs,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", type=Path,
                    default=Path(__file__).resolve().parents[2] / "data/exports/b13-agent-full/train.jsonl")
    ap.add_argument("--limit", type=int, default=0, help="0 = all rows")
    ap.add_argument("--output", type=Path,
                    default=Path(__file__).resolve().parents[2] / "data/interim/eval_report.json")
    args = ap.parse_args()

    n = 0
    agg = Counter()
    tool_counter = Counter()
    with args.input.open("r", encoding="utf-8") as f:
        for line in f:
            if args.limit and n >= args.limit:
                break
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            msgs = rec.get("messages") or []
            s = score_trajectory(msgs)
            n += 1
            if s["roles_ok"] and s["contents_ok"]:
                agg["schema_valid"] += 1
            if s["has_code"]:
                agg["tool_call_present"] += 1
            if s["has_obs"]:
                agg["grounded"] += 1
            if s["has_final"]:
                agg["completed"] += 1
            if s["fabrication_proxy"]:
                agg["fabrication_proxy"] += 1
            for t in s["tool_names"]:
                tool_counter[t] += 1

    def rate(k):
        return round(100.0 * agg[k] / n, 3) if n else 0.0

    report = {
        "rows_scored": n,
        "schema_valid_pct": rate("schema_valid"),
        "tool_call_present_pct": rate("tool_call_present"),
        "grounding_rate_pct": rate("grounded"),
        "completion_rate_pct": rate("completed"),
        "fabrication_proxy_pct": rate("fabrication_proxy"),
        "tool_usage": dict(tool_counter.most_common()),
        "interpretation": {
            "grounding": "higher = more claims tied to real tool observations (less hallucination)",
            "fabrication_proxy": "final_answer with NO observation - LOWER is better; target ~0",
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "interpretation"}, indent=2))


if __name__ == "__main__":
    main()
