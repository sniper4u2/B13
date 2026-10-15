"""
B13 Agent Tool Layer

Tool wrappers registered with the smolagents CodeAgent.

Reality (MYTHOS F4/F8 - do not overstate):
- port_scan / vulnerability_scan / web_app_test / privilege_escalation_check:
  real nmap/nuclei/curl subprocess calls; raise RuntimeError if the binary is absent.
- forensics_audit: real local static analysis (AST/secret/dependency scan).
- metasploit_* : real msfrpc calls; require a running Metasploit RPC (METASPLOIT_RPC_URL).
- C2 / GSM / SS7 tools: wire to the local c2server library client. Backends that
  do not perform real capture return an availability/"unavailable" status rather
  than faking success. No interception/exploit backend is implemented here.
- There is NO MCP client layer; the mcp/ package is intentionally empty.
"""

from .base_tool import B13Tool
from .security_tools import (
    PortScanTool,
    VulnerabilityScanTool,
    WebAppTestTool,
    PrivilegeEscalationCheckTool,
)
from .metasploit_tools import (
    MetasploitSearchTool,
    MetasploitExecuteTool,
    MetasploitGeneratePayloadTool,
    MetasploitListSessionsTool,
)
from .c2_integration import (
    C2ConnectTool,
    C2LocationTrackingTool,
    C2SMSInterceptTool,
    C2CVEExploitTool,
    C2PayloadGenerateTool,
)
from .gsm_integration import (
    GSMHardwareStatusTool,
    GSMTrackLocationTool,
    GSMInterceptSMSTool,
    GSMInterceptCallsTool,
)
from .forensics_auditor import ForensicsAuditTool

__all__ = [
    "B13Tool",
    "PortScanTool",
    "VulnerabilityScanTool",
    "WebAppTestTool",
    "PrivilegeEscalationCheckTool",
    "MetasploitSearchTool",
    "MetasploitExecuteTool",
    "MetasploitGeneratePayloadTool",
    "MetasploitListSessionsTool",
    "C2ConnectTool",
    "C2LocationTrackingTool",
    "C2SMSInterceptTool",
    "C2CVEExploitTool",
    "C2PayloadGenerateTool",
    "GSMHardwareStatusTool",
    "GSMTrackLocationTool",
    "GSMInterceptSMSTool",
    "GSMInterceptCallsTool",
    "ForensicsAuditTool",
]
