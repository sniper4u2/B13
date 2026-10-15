"""
B13 Runtime Module - Agent session execution

Manages agent execution sessions with tool execution support.
Updated to work with the new tool layer.
"""

import asyncio
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class AgentSession:
    """Manages agent execution sessions with tool execution support."""

    def __init__(self, agent, session_id: str = None, max_steps: int = 30):
        """
        Initialize the agent session.

        Args:
            agent: The smolagents CodeAgent instance.
            session_id: Unique session identifier.
            max_steps: Maximum number of tool execution steps before aborting.
        """
        self.agent = agent
        self.session_id = session_id or self._generate_session_id()
        self.state: Dict[str, Any] = {}
        self.max_steps = max_steps
        self.tool_history: list[dict] = []
        self.tasks_completed = 0

    @staticmethod
    def _generate_session_id() -> str:
        """Generate a unique session ID."""
        import uuid
        return f"sess_{uuid.uuid4().hex[:12]}"

    async def execute_task(self, task: str, context: dict = None) -> str:
        """
        Execute a cybersecurity task by the agent.

        Args:
            task: The task description for the agent.
            context: Optional context dict (e.g., target, parameters).

        Returns:
            The agent's response string.
        """
        self.state["task"] = task
        self.state["started_at"] = asyncio.get_running_loop().time()
        self.state["context"] = context or {}

        extended_task = self._build_task_with_context(task, context)

        logger.info(f"[{self.session_id}] Starting task: {task[:100]}...")

        try:
            result = await self.agent.run(extended_task)
            self.state["status"] = "completed"
            self.state["completed_at"] = asyncio.get_running_loop().time()
            self.tasks_completed += 1
            return result
        except Exception as e:
            self.state["status"] = "error"
            self.state["error"] = str(e)
            logger.error(f"[{self.session_id}] Task failed: {e}")
            return f"Error executing task: {str(e)}"

    def _build_task_with_context(self, task: str, context: dict = None) -> str:
        """
        Build the task instruction with context information.
        Adds context markers to help the agent understand the environment.
        """
        context_text = ""
        if context:
            context_items = []
            for key, value in context.items():
                if key == "target":
                    context_items.append(f"Target: {value}")
                elif key == "cve_id":
                    context_items.append(f"CVE to analyze: {value}")
                elif key == "ports":
                    context_items.append(f"Ports to scan: {value}")
                elif key == "output_format":
                    context_items.append(f"Format: {value}")
            context_text = "\n[CONTEXT]\n" + "\n".join(context_items) + "\n[/CONTEXT]"

        return (
            f"{task}{context_text}\n[INSTRUCTIONS]\nUse your available tools to "
            f"complete this task. You have {self.max_steps} steps to complete "
            f"this task."
        )

    def update_state(self, key: str, value: Any):
        """Update session state."""
        self.state[key] = value

    def get_state(self, key: str, default: Any = None) -> Any:
        """Get session state value."""
        return self.state.get(key, default)

    def add_tool_history(self, tool_name: str, input_data: dict, output_data: dict):
        """Record a tool execution in history."""
        self.tool_history.append({
            "tool": tool_name,
            "input": input_data,
            "output": output_data,
            "timestamp": asyncio.get_running_loop().time(),
        })

    def get_summary(self) -> dict:
        """Get session summary."""
        elapsed = 0
        if self.state.get("started_at") and self.state.get("completed_at"):
            elapsed = self.state["completed_at"] - self.state["started_at"]

        return {
            "session_id": self.session_id,
            "status": self.state.get("status", "running"),
            "task": self.state.get("task", ""),
            "tasks_completed": self.tasks_completed,
            "tool_executions": len(self.tool_history),
            "elapsed_seconds": round(elapsed, 2),
            "error": self.state.get("error"),
        }
