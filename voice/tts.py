import os
import shutil
import subprocess
from pathlib import Path


class PiperTTS:
    """Wrapper for piper executable with optional espeak-ng fallback."""

    def __init__(self) -> None:
        self.binary = os.getenv("PIPER_BIN", "piper")
        self.model = os.getenv("PIPER_MODEL", "./models/en_US-lessac-medium.onnx")
        self.fallback_binary = os.getenv("TTS_FALLBACK_BIN", "espeak-ng")
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

    def speak(self, text: str, wav_path: str = "/tmp/piper_out.wav", playback: bool = False) -> str:
        self.last_error = ""
        if not text.strip():
            self.last_error = "empty text"
            return ""

        binary = self._resolve_binary()
        piper_error = ""

        try:
            if binary and self._is_espeak_binary(binary):
                ok, err = self._try_command([binary, "-w", wav_path], text)
                if not ok:
                    piper_error = err
            elif binary and Path(self.model).exists():
                ok, err = self._try_command([binary, "--model", self.model, "--output_file", wav_path], text)
                if not ok:
                    piper_error = err
            elif not binary:
                piper_error = f"piper binary not found (PIPER_BIN={self.binary})"
            else:
                piper_error = f"piper model not found (PIPER_MODEL={self.model})"

            if not Path(wav_path).exists() or Path(wav_path).stat().st_size == 0:
                fallback = shutil.which(self.fallback_binary) if not Path(self.fallback_binary).exists() else self.fallback_binary
                if fallback:
                    proc_fb = subprocess.run(
                        [fallback, "-w", wav_path, text],
                        check=False,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                    )
                    if proc_fb.returncode != 0:
                        fb_err = proc_fb.stderr.decode("utf-8", errors="ignore").strip()
                        self.last_error = f"piper error: {piper_error or 'unknown'}; espeak fallback error: {fb_err or proc_fb.returncode}"
                        return ""
                else:
                    self.last_error = f"piper error: {piper_error or 'unknown'}; espeak fallback binary not found"
                    return ""

            if playback:
                subprocess.run(["aplay", wav_path], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            return wav_path if Path(wav_path).exists() else ""
        except Exception as exc:
            self.last_error = str(exc)
            return ""
