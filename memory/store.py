"""
B13 Persistent Memory / Context Store (user requirement).

On agent init on ANY machine, provision a local store for context + memorisation and
verify at least MIN_FREE_GB (default 20) of disk is free for it. The store holds:
  - sessions/   : per-task conversation + tool history (JSONL)
  - context/    : long-task working memory, checkpoints for resume
  - embeddings/ : optional vector memory (numpy .npy / faiss if present)
  - kv/         : scratch key-value notes the agent persists across runs

Everything is local, on-disk, append-safe. No network. Falls back to a warning
(never crashes) if free space is short, but records the shortfall in status().
"""
from __future__ import annotations
import json
import os
import shutil
import time
import uuid
from pathlib import Path
from typing import Any

STORE_ROOT = os.getenv("B13_MEMORY_DIR", os.path.expanduser("~/b13-memory"))
MIN_FREE_GB = float(os.getenv("B13_MEMORY_MIN_FREE_GB", "20"))


def _free_gb(path: str) -> float:
    try:
        return shutil.disk_usage(path).free / (1024 ** 3)
    except Exception:
        return -1.0


class MemoryStore:
    """Local, persistent context + memory store for the B13 agent."""

    def __init__(self, root: str | None = None, min_free_gb: float | None = None):
        self.root = Path(root or STORE_ROOT).expanduser()
        self.min_free_gb = float(min_free_gb if min_free_gb is not None else MIN_FREE_GB)
        self.provisioned = False
        self.free_gb_at_init = None
        self.shortfall = False

    def provision(self) -> dict:
        """Create the directory tree and verify free space. Idempotent."""
        self.root.mkdir(parents=True, exist_ok=True)
        for sub in ("sessions", "context", "embeddings", "kv"):
            (self.root / sub).mkdir(parents=True, exist_ok=True)
        self.free_gb_at_init = _free_gb(str(self.root))
        self.shortfall = 0 <= self.free_gb_at_init < self.min_free_gb
        self.provisioned = True
        status = self.status()
        if self.shortfall:
            # Never crash the agent on low disk; warn loudly + record.
            print(f"[b13-memory] WARNING: only {self.free_gb_at_init:.1f}GB free, "
                  f"below required {self.min_free_gb:.0f}GB at {self.root}")
        return status

    def status(self) -> dict:
        return {
            "root": str(self.root),
            "provisioned": self.provisioned,
            "free_gb_now": round(_free_gb(str(self.root)), 2) if self.root.exists() else None,
            "free_gb_at_init": None if self.free_gb_at_init is None else round(self.free_gb_at_init, 2),
            "min_free_gb": self.min_free_gb,
            "space_ok": (not self.shortfall) if self.provisioned else None,
        }

    # ---- sessions ----
    def new_session(self, task: str | None = None) -> str:
        sid = f"{time.strftime('%Y%m%d-%H%M%S')}_{uuid.uuid4().hex[:8]}"
        rec = {"session_id": sid, "task": task, "created": time.time(), "events": []}
        (self.root / "sessions" / f"{sid}.json").write_text(json.dumps(rec, indent=2))
        return sid

    def append_session_event(self, session_id: str, event: dict) -> None:
        p = self.root / "sessions" / f"{session_id}.json"
        rec = json.loads(p.read_text()) if p.exists() else {"session_id": session_id, "events": []}
        rec["events"].append({"t": time.time(), **event})
        p.write_text(json.dumps(rec, indent=2))

    def append_session_jsonl(self, session_id: str, event: dict) -> None:
        with (self.root / "sessions" / f"{session_id}.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps({"t": time.time(), **event}, ensure_ascii=False) + "\n")

    # ---- long-task context / checkpoint-resume ----
    def save_context(self, task_id: str, state: dict) -> Path:
        p = self.root / "context" / f"{task_id}.json"
        p.write_text(json.dumps({"task_id": task_id, "saved": time.time(), "state": state},
                                ensure_ascii=False, indent=2))
        return p

    def load_context(self, task_id: str) -> dict | None:
        p = self.root / "context" / f"{task_id}.json"
        return json.loads(p.read_text())["state"] if p.exists() else None

    def list_contexts(self) -> list[str]:
        return sorted(p.stem for p in (self.root / "context").glob("*.json"))

    # ---- scratch kv ----
    def kv_set(self, key: str, value: Any) -> None:
        (self.root / "kv" / f"{key}.json").write_text(json.dumps(value, ensure_ascii=False))

    def kv_get(self, key: str, default: Any = None) -> Any:
        p = self.root / "kv" / f"{key}.json"
        return json.loads(p.read_text()) if p.exists() else default
