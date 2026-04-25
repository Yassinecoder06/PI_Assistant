import os
import shutil
import subprocess
from pathlib import Path


class PiperTTS:
    """Wrapper for piper executable."""

    def __init__(self) -> None:
        self.binary = os.getenv("PIPER_BIN", "piper")
        self.model = os.getenv("PIPER_MODEL", "./models/en_US-lessac-medium.onnx")
        self.last_error = ""

    def _resolve_binary(self) -> str:
        if os.path.isabs(self.binary) or self.binary.startswith("."):
            return self.binary if Path(self.binary).exists() else ""

        resolved = shutil.which(self.binary)
        if resolved:
            return resolved

        # Debian images may expose piper as piper-tts.
        fallback = shutil.which("piper-tts")
        return fallback or ""

    def speak(self, text: str, wav_path: str = "/tmp/piper_out.wav", playback: bool = False) -> str:
        self.last_error = ""
        if not text.strip():
            self.last_error = "empty text"
            return ""

        binary = self._resolve_binary()
        if not binary:
            self.last_error = f"piper binary not found (PIPER_BIN={self.binary})"
            return ""

        if not Path(self.model).exists():
            self.last_error = f"piper model not found (PIPER_MODEL={self.model})"
            return ""

        try:
            cmd = [binary, "--model", self.model, "--output_file", wav_path]
            proc = subprocess.run(
                cmd,
                input=text.encode("utf-8"),
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            if proc.returncode != 0:
                stderr_text = proc.stderr.decode("utf-8", errors="ignore").strip()
                self.last_error = stderr_text or f"piper exited with code {proc.returncode}"
                return ""

            if playback:
                subprocess.run(["aplay", wav_path], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            return wav_path if Path(wav_path).exists() else ""
        except Exception as exc:
            self.last_error = str(exc)
            return ""
