# B13 Agent — base model vs trained system (read this before training)

`Qwen/Qwen2.5-Coder-32B-Instruct` is the **frozen base model** used for B13
fine-tuning. It ships no B13 skills, tools, or wiring. The B13 agent is the
**system built on top of it**:

| Layer | What it is | Where it lives |
| --- | --- | --- |
| Base weights (frozen) | Qwen2.5-Coder-32B-Instruct, Apache-2.0 | `training/configs/qwen3-30b-a3b-kaggle-tpu.json` → `model.repo_id/revision` (NOTE: config file name is legacy; actual base is Qwen2.5-Coder-32B per `train_tpu.py` and `agent.py`) |
| LoRA adapter (this run) | rank-64 attention+MLP delta that teaches B13 behavior | `training/notebooks/cloud/kaggle/train_tpu.py` → `/kaggle/working/b13-checkpoint` |
| SFT behavior (this run) | 78,367 train rows: CVE analysis, CWE/code-security, red-team pentest flows, agent tool-calling | `data/exports/b13-agent-full/train.jsonl` (private Kaggle `jhonmccarty/b13-agent-train-full`) |
| Agent runtime | `smolagents` CodeAgent + search tools | `agent.py`, `runtime.py` |
| B13 capabilities (runtime) | port/vuln/webapp/priv-esc tools, Metasploit RPC, C2 library client, skill library | `b13/cybersecurity/`, `agent_skills/library/skills/b13_security/` |
| Adapter loading | **NOT YET IMPLEMENTED** — see MYTHOS_FINDINGS.md F2 | `agent.py` (gap) |
| Deploy target | base + adapter merged or PEFT-loaded at inference | target: `training/scripts/publish_adapter_to_hf.py` (private, personal account) |

Training produces the **adapter**, not a new base. The adapter + runtime + tools together are the B13 agent.
