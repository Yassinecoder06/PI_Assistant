import os
import subprocess
from typing import Optional


class WhisperSTT:
    """Wrapper for whisper.cpp binary."""

    def __init__(self) -> None:
        self.binary = os.getenv("WHISPER_BIN", "./whisper.cpp/main")
        self.model = os.getenv("WHISPER_MODEL", "./models/ggml-base.en.bin")

    def transcribe(self, audio_path: str) -> str:
        if not os.path.exists(self.binary):
            return ""
        if not os.path.exists(audio_path):
            return ""

        cmd = [self.binary, "-m", self.model, "-f", audio_path, "-otxt", "-of", "/tmp/whisper_out"]
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            out_path = "/tmp/whisper_out.txt"
            if os.path.exists(out_path):
                with open(out_path, "r", encoding="utf-8") as f:
                    return f.read().strip()
        except Exception:
            return ""
        return ""
