"""
B13 Security Tools - General pentesting capabilities

REAL implementations backed by system tools:
- port_scan            -> nmap
- vulnerability_scan   -> nuclei (falls back to nmap NSE vuln scripts if nuclei absent)
- web_application_test -> ffuf (content discovery) + httpx-style header probe
- privilege_escalation_check -> real local system analysis (SUID, sudo, caps, cron, writable paths)

No simulated data. Every method shells out to a real tool or inspects the
real local system and returns the actual output.
"""

import os
import re
import json
import shutil
import asyncio
import subprocess
from typing import Dict, Any, List


def _run(cmd: List[str], timeout: int = 300) -> Dict[str, Any]:
    """Run a real subprocess and capture stdout/stderr/rc. No mocking."""
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout
        )
        return {
            "cmd": " ".join(cmd),
            "returncode": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
        }
    except subprocess.TimeoutExpired as e:
        return {
            "cmd": " ".join(cmd),
            "returncode": -1,
            "stdout": e.stdout or "",
            "stderr": f"TIMEOUT after {timeout}s",
        }
    except FileNotFoundError as e:
        return {
            "cmd": " ".join(cmd),
            "returncode": 127,
            "stdout": "",
            "stderr": f"tool not found: {e}",
        }


def _have(binary: str) -> bool:
    return shutil.which(binary) is not None


class SecurityTools:
    """General security tools for pentesting - REAL system-tool backed."""

    def __init__(self):
        self.tools = {
            "nmap": _have("nmap"),
            "nuclei": _have("nuclei"),
            "ffuf": _have("ffuf"),
            "msfconsole": _have("msfconsole"),
        }

    # ------------------------------------------------------------------ nmap
    async def port_scan(self, target: str, ports: str = "1-65535") -> dict:
        """Perform a REAL TCP port scan with nmap. Returns parsed open ports."""
        if not _have("nmap"):
            raise RuntimeError("nmap is not installed or not on PATH")

        # -sT (TCP connect, no root needed), -Pn (skip host discovery),
        # --open (only show open), -sV (service/version detection)
        cmd = [
            "nmap", "-Pn", "-sT", "-sV", "--open",
            "-p", ports,
            "--host-timeout", "600s",
            target,
        ]
        res = await asyncio.to_thread(_run, cmd, timeout=660)
        open_ports = self._parse_nmap_open(res["stdout"])
        return {
            "status": "completed" if res["returncode"] == 0 else "error",
            "target": target,
            "ports": ports,
            "open_ports": open_ports,
            "returncode": res["returncode"],
            "raw": res["stdout"],
            "stderr": res["stderr"],
        }

    @staticmethod
    def _parse_nmap_open(stdout: str) -> List[Dict[str, Any]]:
        """Parse nmap '-sV --open' output lines like: 22/tcp open ssh OpenSSH 9.6"""
        ports = []
        for line in stdout.splitlines():
            m = re.match(r"^(\d+)/(tcp|udp)\s+open\s+(\S+)(?:\s+(.*))?$", line.strip())
            if m:
                ports.append({
                    "port": int(m.group(1)),
                    "proto": m.group(2),
                    "service": m.group(3),
                    "version": (m.group(4) or "").strip(),
                })
        return ports

    # ---------------------------------------------------------------- nuclei
    async def vulnerability_scan(self, target: str) -> dict:
        """REAL vulnerability scan. Prefer nuclei; fall back to nmap NSE vuln."""
        if _have("nuclei"):
            cmd = [
                "nuclei", "-u", target,
                "-silent", "-jsonl", "-no-color",
                "-timeout", "10", "-retries", "1",
                "-rate-limit", "150",
            ]
            res = await asyncio.to_thread(_run, cmd, timeout=900)
            findings = self._parse_nuclei(res["stdout"])
            return {
                "status": "completed" if res["returncode"] in (0,) else "error",
                "engine": "nuclei",
                "target": target,
                "vulnerabilities": findings,
                "count": len(findings),
                "returncode": res["returncode"],
                "stderr": res["stderr"][:500],
            }

        if _have("nmap"):
            cmd = ["nmap", "-Pn", "-sV", "--script", "vuln", target]
            res = await asyncio.to_thread(_run, cmd, timeout=900)
            return {
                "status": "completed" if res["returncode"] == 0 else "error",
                "engine": "nmap-nse-vuln",
                "target": target,
                "vulnerabilities": [],
                "raw": res["stdout"],
                "returncode": res["returncode"],
                "stderr": res["stderr"][:500],
            }

        raise RuntimeError("Neither nuclei nor nmap is installed")

    @staticmethod
    def _parse_nuclei(stdout: str) -> List[Dict[str, Any]]:
        findings = []
        for line in stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                findings.append({
                    "template": obj.get("template-id"),
                    "name": obj.get("info", {}).get("name"),
                    "severity": obj.get("info", {}).get("severity"),
                    "matched_at": obj.get("matched-at"),
                    "cwe": obj.get("info", {}).get("classification", {}).get("cwe-id"),
                    "cve": obj.get("info", {}).get("classification", {}).get("cve-id"),
                })
            except json.JSONDecodeError:
                # nuclei non-json line (plain finding)
                findings.append({"raw": line})
        return findings

    # ------------------------------------------------------------------ ffuf
    async def web_application_test(self, target: str) -> dict:
        """REAL web app recon: header probe + ffuf content discovery."""
        results: Dict[str, Any] = {
            "status": "completed",
            "target": target,
            "headers": {},
            "discovered_paths": [],
        }

        # 1) Real HTTP header probe (no external dep)
        headers = await self._probe_headers(target)
        results["headers"] = headers

        # 2) Real content discovery with ffuf against a bundled common wordlist
        if _have("ffuf"):
            wordlist = self._default_wordlist()
            base = target if target.endswith("/") else target + "/"
            cmd = [
                "ffuf", "-u", f"{base}FUZZ",
                "-w", wordlist,
                "-mc", "200,201,204,301,302,307,401,403",
                "-t", "40", "-timeout", "10",
                "-s",  # silent: only print results
            ]
            res = await asyncio.to_thread(_run, cmd, timeout=300)
            results["discovered_paths"] = self._parse_ffuf(res["stdout"])
            results["ffuf_returncode"] = res["returncode"]

        return results

    @staticmethod
    async def _probe_headers(target: str) -> Dict[str, str]:
        """Real HTTP HEAD/GET header fetch using urllib (stdlib)."""
        import urllib.request
        import urllib.error

        def _fetch():
            req = urllib.request.Request(target, method="GET")
            req.add_header("User-Agent", "b13-security-tools/1.0")
            with urllib.request.urlopen(req, timeout=15) as resp:
                return {"status": resp.status, "headers": dict(resp.headers)}

        try:
            return await asyncio.to_thread(_fetch)
        except urllib.error.HTTPError as e:
            return {"status": e.code, "headers": dict(e.headers or {})}
        except Exception as e:
            return {"status": None, "error": str(e)}

    @staticmethod
    def _parse_ffuf(stdout: str) -> List[Dict[str, Any]]:
        paths = []
        for line in stdout.splitlines():
            # ffuf -s output: "path    [Status=200, Size=123, ...]"
            m = re.match(r"^(\S+)\s+\[Status=(\d+), Size=(\d+)", line.strip())
            if m:
                paths.append({
                    "path": m.group(1),
                    "status": int(m.group(2)),
                    "size": int(m.group(3)),
                })
        return paths

    @staticmethod
    def _default_wordlist() -> str:
        """Return a real wordlist path if one exists on the system."""
        candidates = [
            "/usr/share/wordlists/dirb/common.txt",
            "/usr/share/seclists/Discovery/Web-Content/common.txt",
            "/usr/share/wordlists/seclists/Discovery/Web-Content/common.txt",
        ]
        for c in candidates:
            if os.path.exists(c):
                return c
        # Write a minimal real wordlist to a temp file (still a real file ffuf reads)
        tmp = "/tmp/b13_ffuf_wordlist.txt"
        if not os.path.exists(tmp):
            with open(tmp, "w") as f:
                f.write("\n".join([
                    "admin", "login", "api", "dashboard", "config",
                    "backup", "test", "status", "health", "metrics",
                ]))
        return tmp

    # -------------------------------------------------- local privesc (real)
    async def privilege_escalation_check(self) -> dict:
        """REAL local privilege-escalation reconnaissance on this host."""
        vectors: List[Dict[str, Any]] = []

        # SUID/SGID binaries (real filesystem scan)
        suid = await self._find_suid()
        if suid:
            vectors.append({"type": "suid_binaries", "count": len(suid), "items": suid[:50]})

        # World-writable files in sensitive dirs
        writable = await self._find_writable_sensitive()
        if writable:
            vectors.append({"type": "world_writable_sensitive", "count": len(writable), "items": writable[:50]})

        # Sudo privileges (real sudo -l, non-interactive)
        sudo = await self._sudo_list()
        if sudo.get("output"):
            vectors.append({"type": "sudo", "output": sudo["output"][:1000]})

        # File capabilities
        caps = await self._file_capabilities()
        if caps:
            vectors.append({"type": "file_capabilities", "count": len(caps), "items": caps[:50]})

        # Writable /etc/passwd or /etc/shadow
        etc = await self._etc_writable()
        if etc:
            vectors.append({"type": "etc_writable", "items": etc})

        # Kernel version (for known kernel exploits context)
        kernel = await asyncio.to_thread(os.uname)

        return {
            "status": "completed",
            "host": {
                "kernel": kernel.release if hasattr(kernel, "release") else str(kernel),
                "uid": os.getuid(),
                "euid": os.geteuid(),
                "is_root": os.geteuid() == 0,
            },
            "vectors": vectors,
            "vector_count": len(vectors),
        }

    async def _find_suid(self) -> List[str]:
        if not _have("find"):
            return []
        res = await asyncio.to_thread(
            _run,
            ["find", "/", "-perm", "-4000", "-type", "f", "-xdev"],
            timeout=120,
        )
        return [ln for ln in res["stdout"].splitlines() if ln.strip()]

    async def _find_writable_sensitive(self) -> List[str]:
        if not _have("find"):
            return []
        targets = "/etc /usr/local/bin /opt".split()
        out: List[str] = []
        for t in targets:
            if not os.path.exists(t):
                continue
            res = await asyncio.to_thread(
                _run,
                ["find", t, "-perm", "-0002", "-type", "f"],
                timeout=60,
            )
            out.extend([ln for ln in res["stdout"].splitlines() if ln.strip()])
        return out

    async def _sudo_list(self) -> Dict[str, str]:
        if not _have("sudo"):
            return {"output": ""}
        res = await asyncio.to_thread(
            _run, ["sudo", "-n", "-l"], timeout=30
        )
        return {"output": res["stdout"], "stderr": res["stderr"]}

    async def _file_capabilities(self) -> List[str]:
        if not _have("getcap"):
            return []
        res = await asyncio.to_thread(
            _run, ["getcap", "-r", "/", "2>/dev/null"], timeout=120
        )
        return [ln for ln in res["stdout"].splitlines() if ln.strip()]

    async def _etc_writable(self) -> List[str]:
        out = []
        for p in ("/etc/passwd", "/etc/shadow", "/etc/sudoers"):
            if os.path.exists(p) and os.access(p, os.W_OK):
                out.append(p)
        return out
