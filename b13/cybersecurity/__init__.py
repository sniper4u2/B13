"""
B13 Cybersecurity Module

Security tools for the B13 agent:
- SecurityTools: General pentesting capabilities (nmap, nuclei, Burp, ffuf)
- MetasploitTools: Metasploit Framework integration via metasploit-mcp
- C2Integration: Custom C2 server MCP integration
"""

from .security_tools import SecurityTools
from .metasploit_tools import MetasploitTools
from .c2_integration import C2Integration

__all__ = [
    "SecurityTools",
    "MetasploitTools",
    "C2Integration",
]

__version__ = "1.0.0"
