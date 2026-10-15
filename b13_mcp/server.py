"""B13 full MCP server - ALL 18 tools + memory + skills + training validation.

Every tool calls its REAL backend path. No simulated success.
When hardware/infra is absent the backend returns success=False with the
real reason. The MCP layer never invents coordinates or sessions.
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp.server.mcpserver import MCPServer

mcp = MCPServer("b13-full")


@mcp.tool()
def forensics_audit(target_dir: str = ".", skip_standard_lib: bool = True) -> dict:
    """Real AST + secret forensics audit on a target directory."""
    from tools.forensics_auditor import ForensicsAuditTool
    return ForensicsAuditTool().forward(target_dir=target_dir, skip_standard_lib=skip_standard_lib)


@mcp.tool()
def port_scan(target: str, ports: str = "1-1000") -> dict:
    """Real nmap TCP port scan. Requires nmap. Target must be authorized."""
    from tools.security_tools import PortScanTool
    return PortScanTool().forward(target=target, ports=ports)


@mcp.tool()
def vulnerability_scan(target: str) -> dict:
    """Real nuclei/nmap vulnerability scan. Requires binary installed."""
    from tools.security_tools import VulnerabilityScanTool
    return VulnerabilityScanTool().forward(target=target)


@mcp.tool()
def web_app_test(target: str) -> dict:
    """Real web-app test (ffuf + header probe)."""
    from tools.security_tools import WebAppTestTool
    return WebAppTestTool().forward(target=target)


@mcp.tool()
def privilege_escalation_check() -> dict:
    """Real local privesc recon (SUID, sudo, caps, kernel)."""
    from tools.security_tools import PrivilegeEscalationCheckTool
    return PrivilegeEscalationCheckTool().forward()


@mcp.tool()
def metasploit_search(search_term: str) -> dict:
    """Real msfconsole search. Requires msfconsole on PATH."""
    from tools.metasploit_tools import MetasploitSearchTool
    return MetasploitSearchTool().forward(search_term=search_term)


@mcp.tool()
def metasploit_execute(exploit_name: str, target: str) -> dict:
    """Real msfconsole exploit execution. Authorized targets only."""
    from tools.metasploit_tools import MetasploitExecuteTool
    return MetasploitExecuteTool().forward(exploit_name=exploit_name, target=target, options={})


@mcp.tool()
def metasploit_generate_payload(payload_type: str, lhost: str, lport: int) -> dict:
    """Real msfvenom payload generation - writes real file + sha256."""
    from tools.metasploit_tools import MetasploitGeneratePayloadTool
    return MetasploitGeneratePayloadTool().forward(payload_type=payload_type, lhost=lhost, lport=lport)


@mcp.tool()
def metasploit_list_sessions() -> dict:
    """Real msfconsole sessions -l."""
    from tools.metasploit_tools import MetasploitListSessionsTool
    return MetasploitListSessionsTool().forward()


@mcp.tool()
def c2_connect() -> dict:
    """Connect to local C2 library - verifies db + loads 5 real modules."""
    from tools.c2_integration import C2ConnectTool
    return C2ConnectTool().forward()

@mcp.tool()
def c2_ss7_location_tracking(target_msisdn: str) -> dict:
    """SS7 location via real FixedSS7Exploitation - honest False when no infra."""
    from tools.c2_integration import C2LocationTrackingTool
    return C2LocationTrackingTool().forward(target_msisdn=target_msisdn)


@mcp.tool()
def c2_ss7_sms_interception(target_msisdn: str) -> dict:
    """SMS intercept via real AdvancedSMSInterceptor + GSM modem AT probe."""
    from tools.c2_integration import C2SMSInterceptTool
    return C2SMSInterceptTool().forward(target_msisdn=target_msisdn)


@mcp.tool()
def c2_cve_exploit_execute(cve_id: str, target: str) -> dict:
    """CVE exploit via real CVEExploitation + cve_exploits.yaml."""
    from tools.c2_integration import C2CVEExploitTool
    return C2CVEExploitTool().forward(cve_id=cve_id, target=target)


@mcp.tool()
def c2_generate_payload(platform: str = "windows", payload_type: str = "reverse_shell") -> dict:
    """Payload via real AdvancedPayloadGenerator."""
    from tools.c2_integration import C2PayloadGenerateTool
    return C2PayloadGenerateTool().forward(platform=platform, payload_type=payload_type)


@mcp.tool()
def gsm_hardware_status() -> dict:
    """Real GSM hardware probe (lsusb + ttyUSB + rtl_test/hackrf_info)."""
    from tools.gsm_integration import GSMHardwareStatusTool
    return GSMHardwareStatusTool().forward()


@mcp.tool()
def gsm_track_location(target_msisdn: str) -> dict:
    """GSM location via real modem + HLR-Lookups API."""
    from tools.gsm_integration import GSMTrackLocationTool
    return GSMTrackLocationTool().forward(target_msisdn=target_msisdn)


@mcp.tool()
def gsm_intercept_sms(target_msisdn: str) -> dict:
    """SMS via real modem AT+CMGL. Honest failure when no SMS port."""
    from tools.gsm_integration import GSMInterceptSMSTool
    return GSMInterceptSMSTool().forward(target_msisdn=target_msisdn)


@mcp.tool()
def gsm_intercept_calls(target: str) -> dict:
    """Call intercept via real modem/SDR. Honest failure when no hardware."""
    from tools.gsm_integration import GSMInterceptCallsTool
    return GSMInterceptCallsTool().forward(target=target)


@mcp.tool()
def memory_status() -> dict:
    """Provision + report local B13 memory store."""
    from memory.store import MemoryStore
    return MemoryStore().provision()


@mcp.tool()
def list_b13_skills() -> dict:
    """List B13 security skills + scripts from real filesystem."""
    import pathlib
    base = pathlib.Path(__file__).resolve().parent.parent / "agent_skills" / "library" / "skills" / "b13_security"
    if not base.is_dir():
        return {"skills": [], "base": str(base), "exists": False}
    out = []
    for p in sorted(base.iterdir()):
        if not p.is_dir():
            continue
        scripts = sorted([s.name for s in (p / "scripts").iterdir() if s.is_file()]) if (p / "scripts").is_dir() else []
        out.append({"name": p.name, "scripts": scripts})
    return {"skills": out, "count": len(out)}


@mcp.tool()
def validate_training_export() -> dict:
    """Validate all 3 training exports (sha256 where pinned)."""
    import hashlib
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent / "data" / "exports"
    result: dict = {}
    for export_id in ("qwen3-30b-a3b", "b13-agent-full", "cve-record-summary"):
        d = root / export_id
        mp = d / "manifest.json"
        if not mp.is_file():
            result[export_id] = {"exists": False}
            continue
        manifest = json.loads(mp.read_text(encoding="utf-8"))
        files = {}
        for fn, meta in (manifest.get("files") or {}).items():
            p = d / fn
            if not p.is_file():
                files[fn] = {"exists": False}
            elif isinstance(meta, dict) and "sha256" in meta:
                files[fn] = {"exists": True, "sha256_match": hashlib.sha256(p.read_bytes()).hexdigest() == meta["sha256"]}
            else:
                files[fn] = {"exists": True, "bytes": p.stat().st_size}
        result[export_id] = {"dir": str(d), "files": files, "rows": manifest.get("rows", {})}
    return result


@mcp.tool()
def backend_status() -> dict:
    """Real local inference readiness: GGUF, binaries, env config."""
    import shutil
    gguf = os.getenv("B13_GGUF_PATH", "/home/b13/Desktop/hdd10-2026/Qwen2.5-MOE-2X7B-DeepSeek-Abliterated-Censored-19B-D_AU-Q4_k_m.gguf")
    return {
        "gguf": {"path": gguf, "exists": os.path.isfile(gguf), "bytes": os.path.getsize(gguf) if os.path.isfile(gguf) else 0},
        "binaries": {b: shutil.which(b) is not None for b in ("nmap", "nuclei", "msfconsole", "msfvenom", "ffuf")},
        "env": {
            "B13_BACKEND": os.getenv("B13_BACKEND", "auto"),
            "B13_MODEL_ID": os.getenv("B13_MODEL_ID", ""),
            "B13_ADAPTER_PATH": os.getenv("B13_ADAPTER_PATH", os.path.expanduser("~/b13-adapter")),
            "B13_GGUF_PATH": os.getenv("B13_GGUF_PATH", ""),
            "B13_VLLM_BASE_URL": os.getenv("B13_VLLM_BASE_URL", "http://localhost:8000/v1"),
        },
    }


if __name__ == "__main__":
    mcp.run()
