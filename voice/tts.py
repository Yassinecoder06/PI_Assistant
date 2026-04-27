import shutil
import subprocess
from pathlib import Path

from backend.config import PIPER_BIN, PIPER_MODEL, TTS_FALLBACK_BIN


class PiperTTS:
    """Wrapper for piper executable with optional espeak-ng fallback."""

    def __init__(self) -> None:
        self.binary = PIPER_BIN
        self.model = PIPER_MODEL
        self.fallback_binary = TTS_FALLBACK_BIN
        self.last_error = ""
        self._resolved_piper = self._resolve_binary(self.binary)
        self._piper_error = self._validate_piper()

    @staticmethod
    def _resolve_binary(binary: str) -> str:
        if Path(binary).is_absolute() or binary.startswith("."):
            return binary if Path(binary).exists() else ""

        resolved = shutil.which(binary)
        if resolved:
            return resolved

        # Debian images may expose piper as piper-tts.
        fallback = shutil.which("piper-tts")
        return fallback or ""

    @staticmethod
    def _is_espeak_binary(binary: str) -> bool:
        name = Path(binary).name.lower()
        return "espeak" in name

    def _try_command(self, cmd: list[str], text: str) -> tuple[bool, str]:
        proc = subprocess.run(
            cmd,
            input=text.encode("utf-8"),
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if proc.returncode == 0:
            return True, ""
        stderr_text = proc.stderr.decode("utf-8", errors="ignore").strip()
        return False, stderr_text or f"command exited with code {proc.returncode}"

    def _validate_piper(self) -> str:
        if not self._resolved_piper:
            return f"piper binary not found (PIPER_BIN={self.binary})"
        if not Path(self.model).exists():
            return f"piper model not found (PIPER_MODEL={self.model})"
        return ""

    def speak(self, text: str, wav_path: str = "/tmp/piper_out.wav", playback: bool = False) -> str:
        self.last_error = ""
        if not text.strip():
            raise ValueError("text cannot be empty")

        piper_error = self._piper_error
        try:
            if not piper_error:
                ok, err = self._try_command(
                    [self._resolved_piper, "--model", self.model, "--output_file", wav_path],
                    text,
                )
                if not ok:
                    piper_error = err

            if not Path(wav_path).exists() or Path(wav_path).stat().st_size == 0:
                fallback = self._resolve_binary(self.fallback_binary)
                if not fallback:
                    raise FileNotFoundError(
                        f"espeak-ng fallback binary not found (TTS_FALLBACK_BIN={self.fallback_binary}); "
                        f"piper error: {piper_error}"
                    )
                ok, err = self._try_command([fallback, "-w", wav_path], text)
                if not ok:
                    raise RuntimeError(
                        f"piper error: {piper_error}; espeak fallback error: {err}"
                    )

            if playback:
                subprocess.run(["aplay", wav_path], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            return wav_path
        except Exception as exc:
            self.last_error = str(exc)
            raise
