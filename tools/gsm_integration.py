"""
B13 GSM Integration - smolagents Tool Wrappers

Tool schemas for GSM device operations via the C2 server.
On Kaggle: schemas are used for training the agent.
Locally: tools connect to the real GSM hardware.
"""

import os
import sys
import logging
from typing import Any

from smolagents import Tool

from .base_tool import run_async

logger = logging.getLogger(__name__)

C2_SERVER_PATH = os.getenv(
    "B13_C2_SERVER_PATH",
    os.path.expanduser("/home/b13/Desktop/b13 agent/c2server")
)
C2_SERVER_SRC_PATH = os.path.join(C2_SERVER_PATH, "src")

if os.path.isdir(C2_SERVER_PATH):
    sys.path.insert(0, C2_SERVER_PATH)
    sys.path.insert(0, C2_SERVER_SRC_PATH)


def _get_gsm_backend():
    """Lazily import FixedGSMExploitation from the C2 server src/"""
    from src.exploits.fixed_gsm_exploitation import FixedGSMExploitation
    return FixedGSMExploitation()


class GSMHardwareStatusTool(Tool):
    """Detect GSM hardware connected to the C2 server."""
    name = "gsm_hardware_status"
    description = (
        "Detect and report all GSM hardware connected to the system. "
        "Scans for USB GSM modems (Huawei, ZTE, Alcatel, Sierra, Quectel, etc.) "
        "and SDR devices (RTL-SDR, HackRF). Returns device paths, capabilities, "
        "and whether location tracking, SMS interception, and call interception "
        "are available."
    )
    inputs = {}
    output_type = "object"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._backend = None

    def forward(self) -> dict:
        if self._backend is None:
            self._backend = _get_gsm_backend()
        # MYTHOS F10 + smolagents sync contract: forward() must be sync. Drive the
        # backend (sync or async) to completion here.
        import inspect
        result = self._backend.get_hardware_status()
        if inspect.isawaitable(result):
            return run_async(result)
        return result


class GSMTrackLocationTool(Tool):
    """Track GSM location using real hardware + HLR-Lookups cloud intelligence."""
    name = "gsm_track_location"
    description = (
        "Track the location of a phone number (MSISDN) using GSM hardware "
        "and HLR-Lookups.com cloud intelligence. Requires a GSM modem to be "
        "connected. Returns country, carrier, network (MCC/MNC), HLR status, "
        "and available GPS coordinates."
    )
    inputs = {
        "target_msisdn": {
            "type": "string",
            "description": "Target MSISDN with country code (e.g. +33612345678)",
        },
    }
    output_type = "object"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._backend = None

    def forward(self, target_msisdn: str) -> dict:
        if self._backend is None:
            self._backend = _get_gsm_backend()
        return run_async(self._backend.track_location(target_msisdn))


class GSMInterceptSMSTool(Tool):
    """Intercept SMS messages via GSM modem serial connection."""
    name = "gsm_intercept_sms"
    description = (
        "Intercept SMS messages for a target MSISDN via a real GSM modem. "
        "Opens a serial connection to the modem, sends AT commands to list "
        "stored SMS messages, and returns intercepted message content. "
        "Requires a GSM modem (e.g. Alcatel HSPA, Huawei E3372) to be connected."
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
            self._backend = _get_gsm_backend()
        return run_async(self._backend.intercept_sms(target_msisdn))


class GSMInterceptCallsTool(Tool):
    name = "gsm_intercept_calls"
    description = (
        "Intercept GSM calls for a target number via a real GSM modem or SDR. "
        "Requires GSM hardware to be connected. Returns interception session ID "
        "and device used."
    )
    inputs = {
        "target": {
            "type": "string",
            "description": "Target phone number to intercept calls from",
        },
    }
    output_type = "object"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._backend = None

    def forward(self, target: str) -> dict:
        if self._backend is None:
            self._backend = _get_gsm_backend()
        return run_async(self._backend.intercept_calls(target))
