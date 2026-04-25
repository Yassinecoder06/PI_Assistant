import os
import subprocess
from pathlib import Path


class PiperTTS:
    """Wrapper for piper executable."""

    def __init__(self) -> None:
        self.binary = os.getenv("PIPER_BIN", "piper")
        self.model = os.getenv("PIPER_MODEL", "./models/en_US-lessac-medium.onnx")

    def speak(self, text: str, wav_path: str = "/tmp/piper_out.wav", playback: bool = False) -> str:
        if not text.strip():
            return ""

        try:
            cmd = [self.binary, "--model", self.model, "--output_file", wav_path]
            subprocess.run(cmd, input=text.encode("utf-8"), check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            if playback:
                subprocess.run(["aplay", wav_path], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            return wav_path if Path(wav_path).exists() else ""
        except Exception:
            return ""
