"""
B13 Model Backend Factory (MYTHOS F2 + user request: multi-runtime).

Loads the trained B13 adapter across interchangeable inference backends so a bigger
model can be run later with llama.cpp / vLLM / AirLLM without touching agent code.

Backends (B13_BACKEND env var):
  - "transformers" : HF AutoModelForCausalLM + PEFT adapter (default; training parity)
  - "qwen35_text"  : uncensored Qwen3.5 text tower + adapter (trust_remote_code)
  - "llamacpp"     : llama-cpp-python GGUF (CPU/3GB-VRAM friendly, big models)
  - "vllm"         : vLLM OpenAI-compatible server (GPU, high throughput)
  - "airllm"       : AirLLM layer-wise inference (run >VRAM models on small GPU)
  - "auto"         : pick best available for the machine
"""
from __future__ import annotations
import os
import logging

logger = logging.getLogger(__name__)

ADAPTER_PATH = os.getenv("B13_ADAPTER_PATH", os.path.expanduser("~/b13-adapter"))
MODEL_ID = os.getenv(
    "B13_MODEL_ID",
    "/home/b13/Desktop/hdd10-2026/latestHDD/MYHDD/llm models/models--kainah--Qwen3-30B-A3B-Claude-4.5-Opus-High-Reasoning-2507-ABLITERATED-UNCENSORED-V2-Q4_K_M-GGUF/snapshots/491a0170b23a5d039207805c521b54911dcba674/qwen3-30b-a3b-claude-4.5-opus-high-reasoning-2507-abliterated-uncensored-v2-q4_k_m.gguf",
)
BACKEND = os.getenv("B13_BACKEND", "llamacpp")


def adapter_available() -> bool:
    return os.path.isfile(os.path.join(ADAPTER_PATH, "adapter_config.json")) and os.path.isfile(
        os.path.join(ADAPTER_PATH, "adapter_model.safetensors")
    )


def _have(mod: str) -> bool:
    try:
        __import__(mod)
        return True
    except Exception:
        return False


def pick_backend(preferred: str | None = None) -> str:
    want = (preferred or BACKEND or "auto").lower()
    if want != "auto":
        return want
    if adapter_available() and _have("transformers"):
        return "transformers"
    if _have("vllm"):
        return "vllm"
    if _have("llama_cpp"):
        return "llamacpp"
    if _have("airllm"):
        return "airllm"
    return "transformers"


def load_backend(model_id: str | None = None, backend: str | None = None):
    model_id = model_id or MODEL_ID
    backend = pick_backend(backend)
    logger.info("B13 backend=%s model=%s adapter=%s", backend, model_id, ADAPTER_PATH)
    if backend == "transformers":
        return _load_transformers(model_id)
    if backend == "llamacpp":
        return _load_llamacpp(model_id)
    if backend == "vllm":
        return _load_vllm(model_id)
    if backend == "airllm":
        return _load_airllm(model_id)
    if backend == "qwen35_text":
        return _load_qwen35_text(model_id)
    raise RuntimeError(f"Unknown B13_BACKEND: {backend!r}")


def _load_transformers(model_id: str):
    from smolagents import TransformersModel
    model = TransformersModel(
        model_id=model_id,
        trust_remote_code=(model_id or "").lower().startswith("davidau/"),
    )
    if adapter_available():
        from peft import PeftModel
        model.model = PeftModel.from_pretrained(model.model, ADAPTER_PATH)
        try:
            model.model = model.model.merge_and_unload()
            logger.info("B13 adapter merged into base weights")
        except Exception:
            logger.info("Adapter applied without merge (PEFT layers live)")
    return model


def _load_qwen35_text(model_id: str):
    """Uncensored Qwen3.5 text tower + trained adapter (trust_remote_code required)."""
    from smolagents import TransformersModel
    from transformers import AutoModelForCausalLM, AutoTokenizer
    tok = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
    full = AutoModelForCausalLM.from_pretrained(
        model_id, torch_dtype="auto", trust_remote_code=True)
    text_model = getattr(full, "text_model", None) or getattr(full, "language_model", full)
    model = TransformersModel(model_id=model_id)
    model.model = text_model
    if adapter_available():
        from peft import PeftModel
        model.model = PeftModel.from_pretrained(text_model, ADAPTER_PATH)
    model.tokenizer = tok
    logger.info("Qwen3.5 text tower loaded + adapter=%s", adapter_available())
    return model


def _load_llamacpp(model_id: str):
    if not _have("llama_cpp"):
        raise RuntimeError("llama.cpp backend needs `pip install llama-cpp-python` + B13_GGUF_PATH")
    from llama_cpp import Llama
    gguf = os.getenv("B13_GGUF_PATH")
    if not gguf:
        raise RuntimeError("Set B13_GGUF_PATH to a .gguf file for the llamacpp backend")
    llm = Llama(model_path=gguf,
                n_gpu_layers=int(os.getenv("B13_GGUF_GPU_LAYERS", "0")),
                n_ctx=int(os.getenv("B13_CONTEXT_LENGTH", "8192")))
    return _ServerStyleModel(llm, name=f"llamacpp:{os.path.basename(gguf)}")


def _load_vllm(model_id: str):
    if not _have("vllm"):
        raise RuntimeError("vllm backend needs `pip install vllm` and a running server")
    base = os.getenv("B13_VLLM_BASE_URL", "http://localhost:8000/v1")
    from smolagents import InferenceClientModel
    return InferenceClientModel(model_id=model_id, base_url=base,
                                api_key=os.getenv("B13_VLLM_API_KEY", "EMPTY"))


def _load_airllm(model_id: str):
    if not _have("airllm"):
        raise RuntimeError("airllm backend needs `pip install airllm`")
    from airllm import AutoModel  # type: ignore
    air = AutoModel.from_pretrained(model_id, max_length=int(os.getenv("B13_CONTEXT_LENGTH", "8192")))
    return _ServerStyleModel(air, name=f"airllm:{model_id}")


class _ServerStyleModel:
    """Adapt a raw .generate()-style engine (llama.cpp / AirLLM) to the minimal
    smolagents model surface: .generate(messages|prompt) -> str."""

    def __init__(self, engine, name: str):
        self._engine = engine
        self.model = engine
        self._name = name

    def generate(self, messages=None, prompt=None, **kwargs):  # noqa: A003
        if prompt is None and messages is not None:
            prompt = messages if isinstance(messages, str) else "\n".join(
                m.get("content", "") for m in messages)
        out = self._engine(prompt, **kwargs)
        if isinstance(out, dict):
            try:
                return out["choices"][0]["text"]
            except Exception:
                return out.get("text", str(out))
        if isinstance(out, (list, tuple)) and out:
            return out[0] if isinstance(out[0], str) else str(out[0])
        return str(out)

    def __call__(self, *a, **k):
        return self.generate(*a, **k)

