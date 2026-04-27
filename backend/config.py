import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]


def _load_local_env() -> None:
    """Load KEY=VALUE pairs from project .env into process environment."""
    env_path = BASE_DIR / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


_load_local_env()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")

MODEL_PRIMARY_CHAT = os.getenv("MODEL_PRIMARY_CHAT", "tinyllama:latest")
MODEL_FAST = os.getenv("MODEL_FAST", "qwen2.5:0.5b")
MODEL_REASONING = os.getenv("MODEL_REASONING", "qwen3.5:0.8b")
MODEL_HEAVY = os.getenv("MODEL_HEAVY", "qwen3.5:2b")

WHISPER_BIN = os.getenv(
    "WHISPER_BIN",
    str(BASE_DIR / "whisper.cpp" / "build" / "bin" / "whisper-cli"),
)
WHISPER_MODEL = os.getenv(
    "WHISPER_MODEL",
    str(BASE_DIR / "whisper.cpp" / "models" / "ggml-tiny.en.bin"),
)

PIPER_BIN = os.getenv("PIPER_BIN", "piper")
PIPER_MODEL = os.getenv("PIPER_MODEL", str(BASE_DIR / "models" / "en_US-lessac-low.onnx"))

TTS_FALLBACK_BIN = os.getenv("TTS_FALLBACK_BIN", "/usr/bin/espeak-ng")

APP_HOST = os.getenv("APP_HOST", "0.0.0.0")
APP_PORT = os.getenv("APP_PORT", "8000")
