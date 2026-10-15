import logging
import time
import traceback

from agent import create_agent

LOGGER = logging.getLogger("b13.runtime")


class B13Runtime:

    def __init__(self):
        self.agent = None
        self.run_count = 0

    def reset(self):
        self.agent = None
        self.run_count = 0

    def execute(self, task):

        task = (task or "").strip()

        if not task:
            raise ValueError("Task cannot be empty.")

        started = time.perf_counter()

        try:

            if self.agent is None:
                self.agent = create_agent()

            result = self.agent.run(
                task,
                reset=True,
            )

            self.run_count += 1

            elapsed = time.perf_counter() - started

            return {
                "success": True,
                "answer": str(result).strip(),
                "run": self.run_count,
                "elapsed": elapsed,
                "events": [
                    "Task received",
                    "Agent initialized",
                    "Execution completed",
                    "Response generated",
                ],
                "error": None,
            }

        except Exception as exc:

            elapsed = time.perf_counter() - started

            LOGGER.error(
                "B13 execution failed: %s",
                exc,
            )

            LOGGER.debug(
                traceback.format_exc()
            )

            return {
                "success": False,
                "answer": "",
                "run": self.run_count + 1,
                "elapsed": elapsed,
                "events": [
                    "Task received",
                    "Execution failed",
                ],
                "error": (
                    f"{type(exc).__name__}: {exc}"
                ),
            }