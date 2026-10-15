"""
B13 C2 Integration - smolagents Tool Wrappers

Tool schemas for C2 server operations.
On Kaggle: schemas are used for training the agent.
Locally: tools connect to the real C2 server.
"""

import os
import sys
import logging
from typing import Any

from smolagents import Tool

from .base_tool import run_async

logger = logging.getLogger(__name__)

# C2 server path - configurable via environment variable
C2_SERVER_PATH = os.getenv(
    "B13_C2_SERVER_PATH",
    os.path.expanduser("/home/b13/Desktop/b13 agent/c2server")
)
C2_SERVER_SRC_PATH = os.path.join(C2_SERVER_PATH, "src")

# Only add to path if directory exists (Kaggle won't have it)
if os.path.isdir(C2_SERVER_PATH):
    sys.path.insert(0, C2_SERVER_PATH)
    sys.path.insert(0, C2_SERVER_SRC_PATH)


def _get_c2_backend():
    """Lazily import C2Integration - only works when C2 server is available"""
    from b13_agent.b13.cybersecurity.c2_integration import C2Integration
    return C2Integration()


class C2ConnectTool(Tool):
    """Connect to the B13 C2 server."""
    name = "c2_connect"
    description = (
        "Connect to the B13 C2 server. Initializes the C2 server connection, "
        "loads configuration, verifies database integrity, and returns "
        "the connection status and available modules."
    )
    inputs = {}
    output_type = "object"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._backend = None

    def forward(self) -> dict:
        if self._backend is None:
            self._backend = _get_c2_backend()
        return run_async(self._backend.connect())


class C2LocationTrackingTool(Tool):
    """Track location using SS7 protocol via C2 server."""
    name = "c2_ss7_location_tracking"
    description = (
        "Track location using SS7 protocol via the C2 server. "
        "Queries the SS7 network for subscriber location, "
        "returns latitude, longitude, and carrier information "
        "for a given MSISDN (phone number with country code)."
    )
    inputs = {
        "target_msisdn": {
            "type": "string",
            "description": "Target MSISDN (phone number with country code, e.g. +33612345678)",
        },
    }
    output_type = "object"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._backend = None

    def forward(self, target_msisdn: str) -> dict:
        if self._backend is None:
            self._backend = _get_c2_backend()
        return run_async(self._backend.track_location(target_msisdn))


class C2SMSInterceptTool(Tool):
    """Intercept SMS messages via SS7 using C2 server."""
    name = "c2_ss7_sms_interception"
    description = (
        "Intercept SMS messages via SS7 protocol using the C2 server. "
        "Starts real-time SMS interception for a target MSISDN, "
        "captures message content including OTPs and authentication codes."
    )
    inputs = {
        "target_msisdn": {
            "type": "string",
            "description": "Target MSISDN to intercept SMS from",
        },
    }
    output_type = "object"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._backend = None

    def forward(self, target_msisdn: str) -> dict:
        if self._backend is None:
            self._backend = _get_c2_backend()
        return run_async(self._backend.intercept_sms(target_msisdn))


class C2CVEExploitTool(Tool):
    """Execute CVE exploit against target using C2 server."""
    name = "c2_cve_exploit_execute"
    description = (
        "Execute a CVE exploit against a target using the C2 server. "
        "Checks the CVE database for known exploits, "
        "executes the exploit on the target, "
        "returns success status and exploitation evidence."
    )
    inputs = {
        "cve_id": {"type": "string", "description": "CVE identifier to exploit (e.g. CVE-2023-32409)"},
        "target": {"type": "string", "description": "Target host or IP address"},
    }
    output_type = "object"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._backend = None

    def forward(self, cve_id: str, target: str) -> dict:
        if self._backend is None:
            self._backend = _get_c2_backend()
        return run_async(self._backend.execute_cve_exploit(cve_id, target))


class C2PayloadGenerateTool(Tool):
    """Generate advanced payload using C2 server's payload generator."""
    name = "c2_generate_payload"
    description = (
        "Generate advanced payload using the C2 server's payload generator. "
        "Creates platform-specific payloads for reverse shell, bind shell, "
        "and other exploitation scenarios. Returns payload ID for tracking."
    )
    inputs = {
        "platform": {
            "type": "string",
            "description": "Target platform (windows, linux, macos)",
            "default": "windows",
            "nullable": True,
        },
        "payload_type": {
            "type": "string",
            "description": "Type of payload (reverse_shell, bind_shell, meterpreter)",
            "default": "reverse_shell",
            "nullable": True,
        },
    }
    output_type = "object"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._backend = None

    def forward(self, platform: str = "windows", payload_type: str = "reverse_shell") -> dict:
        if self._backend is None:
            self._backend = _get_c2_backend()
        return run_async(self._backend.generate_payload(platform=platform, payload_type=payload_type))
