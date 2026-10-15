"""
B13 Metasploit Tools - smolagents Tool Wrappers

Tool schemas for Metasploit Framework operations.
On Kaggle: schemas are used for training the agent.
Locally: tools connect to the real Metasploit RPC API.
"""

import logging
from typing import Any

from smolagents import Tool

from .base_tool import run_async

logger = logging.getLogger(__name__)


def _get_metasploit_backend():
    """Lazily import MetasploitTools - only works locally with Metasploit RPC running"""
    from b13_agent.b13.cybersecurity.metasploit_tools import MetasploitTools
    return MetasploitTools()


class MetasploitSearchTool(Tool):
    """Search for exploits in Metasploit database."""
    name = "metasploit_search"
    description = (
        "Search for exploits in the Metasploit Framework database. "
        "Returns matching exploit modules with their descriptions, "
        "platform targets, and required parameters."
    )
    inputs = {
        "search_term": {
            "type": "string",
            "description": "Search term for exploit search (e.g. 'windows', 'sql injection')",
        },
    }
    output_type = "object"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._backend = None

    def forward(self, search_term: str) -> dict:
        if self._backend is None:
            self._backend = _get_metasploit_backend()
        return run_async(self._backend.search_exploit(search_term))


class MetasploitExecuteTool(Tool):
    """Execute an exploit against target using Metasploit."""
    name = "metasploit_execute"
    description = (
        "Execute an exploit against a target using Metasploit. "
        "Returns session ID and exploit output. "
        "Requires the Metasploit Framework to be running."
    )
    inputs = {
        "exploit_name": {
            "type": "string",
            "description": "Name of the exploit module to execute (e.g. 'exploit/multi/http/struts2_s2_057')",
        },
        "target": {"type": "string", "description": "Target host or IP address"},
        "options": {
            "type": "object",
            "description": "Additional options for the exploit (e.g. {'RHOSTS': '192.168.1.100', 'RPORT': '80'})",
            "nullable": True,
        },
    }
    output_type = "object"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._backend = None

    def forward(self, exploit_name: str, target: str, options: dict = None) -> dict:
        if self._backend is None:
            self._backend = _get_metasploit_backend()
        return run_async(self._backend.execute_exploit(exploit_name, target, options or {}))


class MetasploitGeneratePayloadTool(Tool):
    """Generate a Metasploit payload."""
    name = "metasploit_generate_payload"
    description = (
        "Generate a Metasploit payload for a target platform. "
        "Returns the generated payload and its parameters. "
        "Supports reverse_tcp, reverse_http, bind_tcp, and more."
    )
    inputs = {
        "payload_type": {
            "type": "string",
            "description": "Type of payload to generate (e.g. 'reverse_tcp', 'reverse_http', 'bind_tcp')",
        },
        "lhost": {"type": "string", "description": "Local host IP address for reverse payloads"},
        "lport": {"type": "integer", "description": "Local port for reverse payload"},
    }
    output_type = "object"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._backend = None

    def forward(self, payload_type: str, lhost: str, lport: int) -> dict:
        if self._backend is None:
            self._backend = _get_metasploit_backend()
        return run_async(self._backend.generate_payload(payload_type, lhost, lport))


class MetasploitListSessionsTool(Tool):
    """List active Metasploit sessions."""
    name = "metasploit_list_sessions"
    description = (
        "List active Metasploit sessions from the Metasploit Framework console. "
        "Returns session IDs, session types, connection states, and target addresses."
    )
    inputs = {}
    output_type = "object"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._backend = None

    def forward(self) -> dict:
        if self._backend is None:
            self._backend = _get_metasploit_backend()
        return run_async(self._backend.list_sessions())
