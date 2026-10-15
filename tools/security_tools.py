"""
B13 Security Tools - smolagents Tool Wrappers

Tool schemas for security operations.
On Kaggle: schemas are used for training the agent.
Locally: tools connect to the real SecurityTools backend.
"""

import logging
from typing import Any

from smolagents import Tool

from .base_tool import run_async

logger = logging.getLogger(__name__)


def _get_security_backend():
    """Lazily import SecurityTools - only works locally with required tools installed"""
    from b13_agent.b13.cybersecurity.security_tools import SecurityTools
    return SecurityTools()


class PortScanTool(Tool):
    """Port scanning tool for the B13 agent."""
    name = "port_scan"
    description = (
        "Scan a target host for open ports and services using nmap. "
        "Returns list of open ports with service information "
        "and banner grabbing results."
    )
    inputs = {
        "target": {"type": "string", "description": "Target host or IP address to scan"},
        "ports": {
            "type": "string",
            "description": "Port range(s) to scan, e.g. '1-65535' or '22,80,443'",
            "nullable": True,
        },
    }
    output_type = "object"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._backend = None

    def forward(self, target: str, ports: str = "1-65535") -> dict:
        if self._backend is None:
            self._backend = _get_security_backend()
        return run_async(self._backend.port_scan(target, ports))


class VulnerabilityScanTool(Tool):
    """Vulnerability scanning tool for the B13 agent."""
    name = "vulnerability_scan"
    description = (
        "Perform vulnerability scanning on a target using nuclei and nmap. "
        "Returns CVEs, service banners, and severity ratings "
        "for all vulnerabilities found."
    )
    inputs = {
        "target": {"type": "string", "description": "Target host or IP address to scan"},
    }
    output_type = "object"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._backend = None

    def forward(self, target: str) -> dict:
        if self._backend is None:
            self._backend = _get_security_backend()
        return run_async(self._backend.vulnerability_scan(target))


class WebAppTestTool(Tool):
    """Web application security testing tool for the B13 agent."""
    name = "web_app_test"
    description = (
        "Perform web application security testing using Burp Suite and ffuf. "
        "Returns OWASP Top 10 findings, SQL injection vulnerabilities, "
        "and XSS results."
    )
    inputs = {
        "target": {
            "type": "string",
            "description": "Target URL to test (e.g. https://example.com)",
        },
    }
    output_type = "object"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._backend = None

    def forward(self, target: str) -> dict:
        if self._backend is None:
            self._backend = _get_security_backend()
        return run_async(self._backend.web_application_test(target))


class PrivilegeEscalationCheckTool(Tool):
    """Privilege escalation check tool for the B13 agent."""
    name = "privilege_escalation_check"
    description = (
        "Check for local privilege escalation vectors on the current system. "
        "Performs static binary analysis for setuid binaries, "
        "checks /etc/passwd for weak permissions, "
        "scans for kernel vulnerabilities, and lists SUID binaries."
    )
    inputs = {}
    output_type = "object"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._backend = None

    def forward(self) -> dict:
        if self._backend is None:
            self._backend = _get_security_backend()
        return run_async(self._backend.privilege_escalation_check())
