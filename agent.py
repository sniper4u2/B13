"""
B13 Agent - Tool-Enabled Code Agent

Main agent creation module for the B13 cyber-forensics agent.
Designed for both local execution and Kaggle TPU fine-tuning.

On Kaggle: tools are instantiated for schema extraction (training the model
    to learn correct tool-call formats). Backend connections are lazy.
Locally: tools connect to real backends (C2 server, nmap, Metasploit, etc.)
"""

import os
import logging

from smolagents import (
    CodeAgent,
    InferenceClientModel,
    DuckDuckGoSearchTool,
    VisitWebpageTool,
)
from backends import load_backend

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

MODEL_ID = "Qwen/Qwen3-30B-A3B"
# Trained B13 LoRA adapter location (MYTHOS F2). Override via B13_ADAPTER_PATH.
ADAPTER_PATH = os.getenv("B13_ADAPTER_PATH", os.path.expanduser("~/b13-adapter"))


def _adapter_available() -> bool:
    return os.path.isfile(os.path.join(ADAPTER_PATH, "adapter_config.json")) and os.path.isfile(
        os.path.join(ADAPTER_PATH, "adapter_model.safetensors")
    )


def _load_local_model(model_id: str = None):
    """Load base weights (+ trained B13 adapter if present) locally (MYTHOS F2)."""
    from smolagents import TransformersModel

    model_id = model_id or MODEL_ID
    logger.info("Loading LOCAL model %s (adapter=%s)", model_id, ADAPTER_PATH)
    model = TransformersModel(model_id=model_id)
    if _adapter_available():
        try:
            from peft import PeftModel

            model.model = PeftModel.from_pretrained(model.model, ADAPTER_PATH)
            try:
                model.model = model.model.merge_and_unload()
                logger.info("B13 adapter merged into base weights")
            except Exception:
                logger.info("Adapter applied without merge (running PEFT layers live)")
        except Exception as exc:
            logger.warning("Could not apply adapter, running bare base: %s", exc)
    return model

AUTHORIZED_IMPORTS = [
    "pandas",
    "numpy",
    "math",
    "re",
    "json",
    "datetime",
    "ast",
    "pathlib",
    "subprocess",
    "sys",
    "os",
]


def get_all_tools():
    """Return all B13 tool instances.

    Tools are instantiated without requiring backend connections.
    Backends are lazily initialized on first forward() call.
    This makes the tools Kaggle-compatible for schema extraction.
    """
    from b13_agent.tools import (
        PortScanTool,
        VulnerabilityScanTool,
        WebAppTestTool,
        PrivilegeEscalationCheckTool,
        MetasploitSearchTool,
        MetasploitExecuteTool,
        MetasploitGeneratePayloadTool,
        MetasploitListSessionsTool,
        C2ConnectTool,
        C2LocationTrackingTool,
        C2SMSInterceptTool,
        C2CVEExploitTool,
        C2PayloadGenerateTool,
        GSMHardwareStatusTool,
        GSMTrackLocationTool,
        GSMInterceptSMSTool,
        GSMInterceptCallsTool,
        ForensicsAuditTool,
    )

    return [
        PortScanTool(),
        VulnerabilityScanTool(),
        WebAppTestTool(),
        PrivilegeEscalationCheckTool(),
        MetasploitSearchTool(),
        MetasploitExecuteTool(),
        MetasploitGeneratePayloadTool(),
        MetasploitListSessionsTool(),
        C2ConnectTool(),
        C2LocationTrackingTool(),
        C2SMSInterceptTool(),
        C2CVEExploitTool(),
        C2PayloadGenerateTool(),
        GSMHardwareStatusTool(),
        GSMTrackLocationTool(),
        GSMInterceptSMSTool(),
        GSMInterceptCallsTool(),
        ForensicsAuditTool(),
    ]


def create_agent(token=None, model_id: str = None, include_web_tools: bool = True):
    """Create a B13 agent with all security tools.

    Args:
        token: HF token for the model. Uses HF_TOKEN env var if None.
        model_id: Model ID. Uses MODEL_ID if None.
        include_web_tools: Include DuckDuckGoSearchTool and VisitWebpageTool.

    Returns:
        CodeAgent: Configured agent with tools registered.
    """
    token = token or os.getenv("HF_TOKEN")
    model_id = model_id or MODEL_ID

    # MYTHOS F2 + F7 + multi-backend: resolve the model through the backend factory
    # (transformers+adapter by default; llama.cpp / vLLM / AirLLM via B13_BACKEND).
    backend = os.getenv("B13_BACKEND", "auto")
    if backend != "auto" or _adapter_available():
        model = load_backend(model_id=model_id, backend=None if backend == "auto" else backend)
    elif token:
        model = InferenceClientModel(model_id=model_id, token=token)
    else:
        logger.warning(
            "No adapter at %s and no HF_TOKEN; loading local base model. "
            "Set B13_ADAPTER_PATH to run the trained B13.", ADAPTER_PATH,
        )
        model = load_backend(model_id=model_id, backend="transformers")

    tool_list = get_all_tools()

    if include_web_tools:
        tool_list.extend([
            DuckDuckGoSearchTool(),
            VisitWebpageTool(),
        ])

    logger.info(f"Agent created with {len(tool_list)} tools")
    logger.info(f"Model: {model_id}")

    return CodeAgent(
        model=model,
        tools=tool_list,
        additional_authorized_imports=AUTHORIZED_IMPORTS,
        executor_type="local",
        stream_outputs=False,
    )


def export_tool_schemas() -> dict:
    """Export tool schemas for fine-tuning dataset generation.

    Returns a dict mapping tool names to their schemas.
    This is used to generate training data for the agent.
    """
    tools = get_all_tools()
    schemas = {}
    for tool in tools:
        schemas[tool.name] = {
            "description": tool.description,
            "inputs": tool.inputs,
            "output_type": tool.output_type,
        }
    return schemas
