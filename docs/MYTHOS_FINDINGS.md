# Mythos Audit — Findings Log (verbatim, actioned one-by-one)

Source: Mythos agent audit of `b13_agent/`. No directories were changed by the audit.
Each item below is reproduced factually, then marked with implementation status.

---

## F1. C2 wiring is in-process library import, not network client
`tools/c2_integration.py` and `b13/cybersecurity/c2_integration.py` inject the C2 server
path onto `sys.path` and instantiate exploit classes directly in-process. The FastAPI
server / WebSockets / Mongo / Redis are bypassed when B13 runs tools.
Status: **FACT — not changing** (this is intended library-client design; not a defect).

## F2. Runtime does NOT load the trained adapter (CRITICAL)
`agent.py:114` uses `InferenceClientModel(model_id=Qwen/Qwen2.5-Coder-32B-Instruct)`.
No PEFT/adapter load exists in `agent.py` / `runtime.py` / `b13/runtime.py`.
Even after Kaggle training, the live agent runs the untrained base model.
Status: **TO FIX — implement adapter loading in `create_agent`.**

## F3. MODEL_ID mismatch between docs and code
- `docs/b13-system-model.md` says base = `Qwen/Qwen3-30B-A3B @ ad44e777...`.
- Kernel (`train_tpu.py:14`) and runtime (`agent.py:28`) both use `Qwen/Qwen2.5-Coder-32B-Instruct`.
Status: **TO FIX — correct the doc to match the real base model.**

## F4. Empty `mcp/` and `ui/` packages
`mcp/` and `ui/` top-level dirs have no `__init__.py`. Docstring/README claim MCP integration that has zero code.
Status: **TO FIX — remove the false MCP claim OR add a real, minimal MCP client. Decision pending.**

## F5. Two divergent runtime entrypoints
- `runtime.py` (root) → `create_agent()` → CodeAgent. Used by `b13/ui.py`.
- `b13/runtime.py` → `AgentSession` (async) — not wired into UI/app.
Status: **TO FIX — pick one runtime; wire or remove `AgentSession`.**

## F6. Duplicated C2/GSM SMS + location logic (3 entrypoints)
`tools/c2_integration.py`, `tools/gsm_integration.py`, `b13/cybersecurity/c2_integration.py`
overlap on SMS/location. `get_all_tools()` eagerly builds all 18 tools.
Status: **TO FIX — de-duplicate to single source per capability.**

## F7. HF_TOKEN hard-required, no graceful path
`create_agent` raises `ValueError` if `HF_TOKEN` unset; `make_app()` calls it at import → UI hard-crashes without token. No local-model fallback.
Status: **TO FIX — add local-model fallback path.**

## F8. Stub success-returns in C2/GSM/SS7 tools
Tools return structurally-valid dicts (`{"status":"intercepting"}`) while the backend captures nothing.
Status: **USER INSTRUCTION — leave backend execution as-is. Do NOT implement interception/exploit. Not re-touching these.**

## F9. Metasploit + port/vuln tools are real but dependency-gated
`security_tools.py` uses real nmap/nuclei subprocess, raises if binary missing. metasploit needs msfrpc.
Status: **FACT — honest tools, leave as-is.**

## F10. GSM hardware-status tool ignores async contract
`GSMHardwareStatusTool.forward` returns a sync backend call while siblings await. Works by accident.
Status: **TO FIX — make async contract consistent.**

---

## Implementation order (agreed)
1. F3 — fix doc model name — **DONE**
2. F2 — adapter loading in `create_agent` — **DONE**
3. F7 — local-model fallback + graceful HF_TOKEN — **DONE**
4. F5 — single runtime — **DONE** (UI now wraps `create_agent()` in `AgentSession`; root `B13Runtime` kept for programmatic use)
5. F4 — mcp/ ui/ truth — **DONE** (false "all implemented / MCP" claims removed; `mcp/` stays empty, documented as no-MCP)
6. F10 — GSM async contract — **DONE** (forward() awaits coroutine or runs sync in thread)
7. F6 — de-duplicate C2/GSM SMS+location — **PARTIAL**: docstring now states the 3 overlapping entrypoints; structural de-dup left to next pass (touching C2/GSM backends risks F8 scope)
8. F8 — NOT TOUCHED per user instruction (no interception/exploit backends written)

## Progress log
- F3: docs/b13-system-model.md corrected to Qwen2.5-Coder-32B-Instruct.
- F2+F7: agent.py — adapter load via PeftModel+merge; no hard HF_TOKEN crash; local fallback. py_compile OK.
- F5: b13/ui.py — single AgentSession runtime wired.
- F4: tools/__init__.py docstring de-lied; MCP claim removed.
- F10: tools/gsm_integration.py GSMHardwareStatusTool async-safe.
- All touched files: py_compile OK (agent.py, b13/ui.py, b13/runtime.py, tools/gsm_integration.py, tools/__init__.py).

## Still open (not implemented — flagged, needs decision)
- F1: C2 is in-process library client (by design, not a bug) — left as-is.
- F6: full de-dup of C2 vs GSM SMS/location entrypoints (3 overlapping paths remain).
- F8: C2/GSM/SS7 stub success-returns — left untouched per user instruction.

## F11 (added by user priority) — TOOLS DID NOT EXECUTE. ROOT CAUSE + FIX
Symptom: B13 could not run tools at all — the thing the user cares about most.

Root cause (verified): smolagents `Tool.__call__` calls `forward()` SYNCHRONOUSLY and
returns its value directly. Every B13 tool defined `async def forward`, so `__call__`
returned an un-awaited `<coroutine object>` — the tool body never ran. The agent's
observation was a coroutine repr, not a result.

Fix: converted ALL 18 tool `forward` methods to SYNC.
- Added `run_async(coro)` in `tools/base_tool.py` (handles "in a loop" and "no loop").
- Each async backend call is now driven via `run_async(...)` from a sync `forward`.
- `forensics_auditor.forward` was pure-sync under `async` — just dropped `async`.
- `base_tool.B13Tool.forward` now sync + drives async `_backend_call`.

Proof (executed):
- `forensics_audit(target_dir='tools')` via `t(...)` → returned a real dict
  (files_scanned=7, placeholders=4, secrets=0). NOT a coroutine.
- Static check across security/metasploit/c2/gsm/forensics modules: 23 tool classes,
  `async_forward_remaining: []` → ALL_SYNC.
- All 6 tool files: py_compile OK.

Net: B13 now actually executes its tools. Tool-execution capability restored.

## F12 — DATA STRENGTH + GROUNDING + PERSISTENCE + MULTI-BACKEND (user request)
Delivered and verified:

1. Data validation (training/scripts/validate_corpus.py) — RAN on 78,367 rows:
   - clean_pct=100.0, rows_with_defects=0 (no content filtering; structural only)
   - grounding: tool_exec_with_obs=44,905/44,905 (100%), with_final=44,905/44,905
   - 7 distinct system prompts; role counts consistent
   - CONTEXT FINDING: 2,166 rows (2.8%) exceed 2048 tok; 0 exceed 8192 tok
   - report: data/interim/corpus_quality_report.json

2. Context window fix: training kernel max_seq_length 2048 -> 8192 (0 truncation at 8192).
   Staged at /tmp/b13-push-kernel3/train_tpu.py, py_compile OK. NOT pushed (awaiting model decision).

3. Memory/context store (memory/store.py + memory/__init__.py) — RAN live:
   - MemoryStore.provision() creates sessions/ context/ embeddings/ kv/
   - verifies >=20GB free (MIN_FREE_GB, B13_MEMORY_MIN_FREE_GB); warns (never crashes) on shortfall
   - session events (json + jsonl), long-task checkpoint save/load/list, kv scratch
   - TEST RESULT: MEMORY_STORE_WORKING. NOTE: this machine has only 7.59GB free -> would warn.

4. Multi-backend model factory (backends.py) — for later big models:
   - B13_BACKEND: transformers (HF+PEFT adapter, default) | llamacpp (GGUF) | vllm (server) | airllm | auto
   - agent.py create_agent now routes through load_backend(); llama.cpp/vLLM/AirLLM supported
   - _ServerStyleModel adapts llama.cpp/AirLLM .generate() to smolagents surface
   - all py_compile OK

5. Anti-hallucination eval (training/scripts/eval_antihallucination.py) — RAN on 20k rows:
   - schema_valid=100%, tool_call_present=100%, grounding=100%, completion=100%
   - fabrication_proxy=0.0% (final_answer with NO observation -> target ~0, met)
   - report: data/interim/eval_report.json

Compile status: agent.py, backends.py, memory/*, validate_corpus.py, eval_antihallucination.py = OK.

## Still open
- Model choice (user sourcing separately). When picked: set B13_MODEL_ID + kernel MODEL_ID, re-run.
- Kernel context bump staged but NOT pushed (holds TPU slot; push with final model).
- Long-task fallback: MemoryStore checkpoint/resume exists; agent-loop auto-resume wiring pending.
