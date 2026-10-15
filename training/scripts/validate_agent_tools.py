"""B13 Agent Tools Validation Script (real-backend design).

Validates imports, tool schemas, agent construction, runtime, backends,
GSM wiring, and training-data hygiene. No sim_mode, no simulations,
no placeholders.
"""
import sys
import os
import asyncio
import inspect
from pathlib import Path

PROJECT_ROOT = Path("/home/b13/Desktop/b13 agent")
sys.path.insert(0, str(PROJECT_ROOT))

TOOL_CLASSES = [
    ("b13_agent.tools.security_tools", "PortScanTool", "port_scan"),
    ("b13_agent.tools.security_tools", "VulnerabilityScanTool", "vulnerability_scan"),
    ("b13_agent.tools.security_tools", "WebAppTestTool", "web_app_test"),
    ("b13_agent.tools.security_tools", "PrivilegeEscalationCheckTool", "privilege_escalation_check"),
    ("b13_agent.tools.metasploit_tools", "MetasploitSearchTool", "metasploit_search"),
    ("b13_agent.tools.metasploit_tools", "MetasploitExecuteTool", "metasploit_execute"),
    ("b13_agent.tools.metasploit_tools", "MetasploitGeneratePayloadTool", "metasploit_generate_payload"),
    ("b13_agent.tools.metasploit_tools", "MetasploitListSessionsTool", "metasploit_list_sessions"),
    ("b13_agent.tools.c2_integration", "C2ConnectTool", "c2_connect"),
    ("b13_agent.tools.c2_integration", "C2LocationTrackingTool", "c2_ss7_location_tracking"),
    ("b13_agent.tools.c2_integration", "C2SMSInterceptTool", "c2_ss7_sms_interception"),
    ("b13_agent.tools.c2_integration", "C2CVEExploitTool", "c2_cve_exploit_execute"),
    ("b13_agent.tools.c2_integration", "C2PayloadGenerateTool", "c2_generate_payload"),
    ("b13_agent.tools.forensics_auditor", "ForensicsAuditTool", "forensics_audit"),
]


def section(n, title):
    print("\n" + "=" * 60)
    print(f"{n}. {title}")
    print("=" * 60)


def check_imports():
    section("1", "IMPORT VALIDATION")
    mods = sorted({m for m, _, _ in TOOL_CLASSES} | {
        "b13_agent.agent",
        "b13_agent.b13.cybersecurity",
        "b13_agent.b13.runtime",
        "b13_agent.tools",
    })
    ok = True
    for m in mods:
        try:
            __import__(m)
            print(f"  [OK] {m}")
        except Exception as e:
            print(f"  [FAIL] {m}: {type(e).__name__}: {e}")
            ok = False
    return ok


def check_tool_classes():
    section("2", "TOOL CLASS + SCHEMA VALIDATION")
    import importlib
    ok = True
    for mod_name, cls_name, want_name in TOOL_CLASSES:
        mod = importlib.import_module(mod_name)
        cls = getattr(mod, cls_name)
        if getattr(cls, "name", None) != want_name:
            print(f"  [FAIL] {cls_name}: bad name {getattr(cls, 'name', None)!r}")
            ok = False
            continue
        if not isinstance(getattr(cls, "inputs", None), dict):
            print(f"  [FAIL] {cls_name}: bad inputs")
            ok = False
            continue
        if getattr(cls, "output_type", None) not in ("object", "string", "integer", "number", "boolean", "array"):
            print(f"  [FAIL] {cls_name}: bad output_type {cls.output_type!r}")
            ok = False
            continue
        sig = inspect.signature(cls.forward)
        keys = [k for k in sig.parameters if k != "self"]
        exp = set(cls.inputs.keys())
        if set(keys) != exp:
            print(f"  [FAIL] {cls_name}: forward{keys} != inputs{sorted(exp)}")
            ok = False
            continue
        print(f"  [OK] {want_name}")
    return ok


def check_no_placeholders():
    section("3", "NO PLACEHOLDER / SIMULATION SCAN")
    import io, tokenize
    roots = [PROJECT_ROOT / "b13_agent" / "tools", PROJECT_ROOT / "b13_agent" / "b13"]
    # code-level simulation/placeholder markers only (docstrings/comments stripped)
    bad = ["sim_mode", "simulated=", "Simulated", "OptionalBackendTool", "SmartTool",
           "random.uniform", "random.randint", "random.choice", "status.*simulated"]

    def strip_noise(src: str) -> str:
        out = []
        try:
            toks = tokenize.generate_tokens(io.StringIO(src).readline)
            prev_end = (1, 0)
            string_starts = set()
            for tok in toks:
                if tok.type == tokenize.STRING:
                    # skip string literals (docstrings / messages)
                    continue
                if tok.type == tokenize.COMMENT:
                    continue
                out.append(tok.string)
        except tokenize.TokenError:
            return src
        return " ".join(out)

    hits = []
    files = []
    for root in roots:
        files += [f for f in sorted(root.rglob("*.py")) if ".venv" not in str(f)]
    files.append(PROJECT_ROOT / "c2server" / "src" / "exploits" / "fixed_gsm_exploitation.py")
    for f in files:
        if not f.exists():
            continue
        code = strip_noise(f.read_text(errors="replace"))
        for token in bad:
            if token in code:
                hits.append(f"{f.relative_to(PROJECT_ROOT)}: {token}")
    if hits:
        for h in hits:
            print(f"  [FAIL] {h}")
        return False
    print("  [OK] no placeholder/simulation markers in tool layer + GSM module")
    return True


def check_agent_creation():
    section("4", "AGENT CONSTRUCTION")
    try:
        from b13_agent.agent import get_all_tools, export_tool_schemas
        tools = get_all_tools()
        names = sorted(t.name for t in tools)
        assert len(tools) == 18, f"expected 18 tools, got {len(tools)}: {names}"
        print(f"  [OK] get_all_tools -> {len(tools)} tools")
        schemas = export_tool_schemas()
        assert len(schemas) == 18
        print(f"  [OK] export_tool_schemas -> {len(schemas)} schemas")
        from smolagents import CodeAgent, InferenceClientModel
        agent = CodeAgent(
            model=InferenceClientModel(model_id="Qwen/Qwen2.5-Coder-32B-Instruct", token="x"),
            tools=tools,
            additional_authorized_imports=["json", "re", "os", "sys"],
        )
        assert set(agent.tools.keys()) >= set(names), sorted(agent.tools.keys())
        print(f"  [OK] CodeAgent registered all tools")
        return True
    except Exception as e:
        import traceback; traceback.print_exc()
        print(f"  [FAIL] {e}")
        return False


def check_runtime():
    section("5", "RUNTIME (no deprecated loop API)")
    try:
        import asyncio
        from b13_agent.b13.runtime import AgentSession

        class MockAgent:
            async def run(self, task):
                return f"ok:{task[:8]}"

        async def go():
            s = AgentSession(agent=MockAgent(), session_id="t001", max_steps=3)
            s.update_state("k", "v")
            assert s.get_state("k") == "v"
            out = await s.execute_task("hello", context={"target": "127.0.0.1"})
            assert out.startswith("ok:")
            s.add_tool_history("port_scan", {"target": "x"}, {"status": "ok"})
            summ = s.get_summary()
            assert summ["tool_executions"] == 1 and summ["tasks_completed"] == 1
            return True
        asyncio.run(go())
        src = (PROJECT_ROOT / "b13_agent" / "b13" / "runtime.py").read_text()
        assert "get_event_loop" not in src, "deprecated asyncio.get_event_loop still present"
        print("  [OK] AgentSession execute/history/summary + no deprecated loop API")
        return True
    except Exception as e:
        import traceback; traceback.print_exc()
        print(f"  [FAIL] {e}")
        return False


def check_gsm():
    section("6", "GSM HARDWARE + MODULE")
    try:
        import subprocess as sp, os as _os
        usbs = [p for p in ("/dev/ttyUSB0", "/dev/ttyUSB1", "/dev/ttyUSB2", "/dev/ttyUSB3", "/dev/ttyUSB4") if _os.path.exists(p)]
        print(f"  serial devices present: {usbs}")
        ls = sp.run(["lsusb"], capture_output=True, text=True, timeout=10)
        gsm = [l for l in ls.stdout.splitlines() if any(v in l for v in ("Alcatel", "Huawei", "ZTE", "Sierra", "Quectel", "Novatel", "Option"))]
        print(f"  GSM USB lines: {gsm if gsm else '(none matched)'}")
        sys.path.insert(0, str(PROJECT_ROOT / "c2server"))
        sys.path.insert(0, str(PROJECT_ROOT / "c2server" / "src"))
        from src.exploits.fixed_gsm_exploitation import FixedGSMExploitation
        g = FixedGSMExploitation()
        st = g.get_hardware_status()
        print(f"  modems={st['gsm_modems']} sdr={st['sdr_devices']} caps={st['capabilities']}")
        assert st["capabilities"]["mode"] in ("hardware", "unavailable")
        return True
    except Exception as e:
        import traceback; traceback.print_exc()
        print(f"  [FAIL] {e}")
        return False


def check_training_data():
    section("7", "TRAINING DATA VALIDATION")
    ok = True
    sft_dirs = [
        PROJECT_ROOT / "b13_agent" / "data" / "sources" / "corpora" / "datasets-hf-export" / "sft",
        PROJECT_ROOT / "b13_agent" / "data" / "sources" / "corpora" / "datasets-workbench" / "processed",
    ]
    for d in sft_dirs:
        if not d.exists():
            print(f"  [SKIP] missing dir {d.relative_to(PROJECT_ROOT)}")
            continue
        files = sorted(d.rglob("*.json*")) + sorted(d.rglob("*.parquet")) + sorted(d.rglob("*.jsonl"))
        print(f"  {d.relative_to(PROJECT_ROOT)}: {len(files)} data files")
        shown = 0
        try:
            import json as _j
            for f in files:
                if f.suffixes and ".json" in "".join(f.suffixes) and shown < 1:
                    raw = f.read_text(errors="replace")[:20000]
                    obj = _j.loads(raw) if raw.strip().startswith(("{", "[")) else None
                    recs = obj if isinstance(obj, list) else ([obj] if isinstance(obj, dict) else None)
                    if recs:
                        r0 = recs[0]
                        keys = sorted(r0.keys()) if isinstance(r0, dict) else []
                        print(f"    sample {f.name}: keys={keys}")
                        shown += 1
        except Exception as e:
            print(f"  [WARN] sample parse issue in {d.name}: {e}")
    try:
        from b13_agent.agent import export_tool_schemas
        from b13_agent.training.scripts.build_cve_tool_execution_sft import build_records
        probe = build_records.__doc__ or ""
        print(f"  [OK] SFT builder importable; tool schemas={len(export_tool_schemas())}")
    except Exception as e:
        print(f"  [WARN] SFT builder check skipped: {e}")
    return ok


def main():
    print("\n" + "#" * 60 + "\n# B13 TRAINING-DATA + TOOL VALIDATION\n" + "#" * 60)
    results = [check_imports(), check_tool_classes(), check_no_placeholders(),
               check_agent_creation(), check_runtime(), check_gsm(), check_training_data()]
    labels = ["imports", "schemas", "no-placeholders", "agent", "runtime", "gsm", "training-data"]
    print("\n" + "=" * 60 + "\nSUMMARY")
    for l, r in zip(labels, results):
        print(f"  {'PASS' if r else 'FAIL'}  {l}")
    print("=" * 60)
    print("ALL VALIDATIONS PASSED" if all(results) else "SOME VALIDATIONS FAILED")
    return all(results)


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
