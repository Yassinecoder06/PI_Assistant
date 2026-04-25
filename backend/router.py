import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import httpx


def _load_local_env() -> None:
    """Load KEY=VALUE pairs from project .env into process environment."""
    env_path = Path(__file__).resolve().parents[1] / ".env"
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


@dataclass
class RouteDecision:
    model: str
    task: str


class ModelRouter:
    """Tiny heuristic router to keep inference cheap on Raspberry Pi 3."""

    def __init__(self) -> None:
        self.primary_chat_model = os.getenv("MODEL_PRIMARY_CHAT", "tinyllama:latest")
        self.fast_model = os.getenv("MODEL_FAST", "qwen2.5:0.5b")
        self.reasoning_model = os.getenv("MODEL_REASONING", "qwen3.5:0.8b")
        self.heavy_model = os.getenv("MODEL_HEAVY", "qwen3.5:2b")

    def route(self, user_text: str) -> RouteDecision:
        text = user_text.lower()

        sensor_keywords = ["sensor", "gyro", "gyroscope", "light", "button", "temperature", "reading"]
        reasoning_keywords = ["classify", "categorize", "summarize", "why", "explain", "compare"]
        heavy_keywords = ["step by step", "deep reasoning", "proof", "derive", "long analysis"]

        if any(k in text for k in sensor_keywords):
            return RouteDecision(model=self.fast_model, task="sensor_query")

        if any(k in text for k in heavy_keywords):
            return RouteDecision(model=self.heavy_model, task="heavy_reasoning")

        if any(k in text for k in reasoning_keywords):
            return RouteDecision(model=self.reasoning_model, task="light_reasoning")

        if len(text.split()) < 8:
            return RouteDecision(model=self.fast_model, task="quick_reply")

        return RouteDecision(model=self.primary_chat_model, task="chat")


def detect_start_game_intent(user_text: str) -> bool:
    text = user_text.lower().strip()
    patterns = [
        r"start( a)? game",
        r"launch( the)? game",
        r"play( a)? race",
        r"open( the)? arcade",
        r"let'?s play",
    ]
    return any(re.search(p, text) for p in patterns)


class OllamaClient:
    def __init__(self, base_url: str = "http://127.0.0.1:11434") -> None:
        self.base_url = base_url.rstrip("/")

    async def generate(self, model: str, prompt: str, system_prompt: Optional[str] = None) -> str:
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_ctx": 1024,
                "temperature": 0.4,
                "num_predict": 180,
            },
        }
        if system_prompt:
            payload["system"] = system_prompt

        async with httpx.AsyncClient(timeout=35.0) as client:
            response = await client.post(f"{self.base_url}/api/generate", json=payload)
            response.raise_for_status()
            data = response.json()
            return data.get("response", "").strip()
