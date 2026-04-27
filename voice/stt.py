import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from backend.config import WHISPER_BIN, WHISPER_MODEL


class WhisperSTT:
    """Wrapper for whisper.cpp binary."""

    def __init__(self) -> None:
        self.binary = WHISPER_BIN
        self.model = WHISPER_MODEL
        self._validate_paths()

    def _validate_paths(self) -> None:
        if not Path(self.binary).exists():
            raise FileNotFoundError(f"whisper binary not found: {self.binary}")
        if not Path(self.model).exists():
            raise FileNotFoundError(f"whisper model not found: {self.model}")

    def transcribe(self, audio_path: str) -> str:
        input_path = Path(audio_path)
        if not input_path.exists():
            raise FileNotFoundError(f"audio file not found: {audio_path}")
        wav_path = str(input_path)

        if input_path.suffix.lower() != ".wav":
            ffmpeg = shutil.which("ffmpeg")
            if not ffmpeg:
                raise RuntimeError("ffmpeg not found for audio conversion")
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_wav:
                wav_path = tmp_wav.name
            try:
                subprocess.run(
                    [ffmpeg, "-y", "-i", str(input_path), "-ar", "16000", "-ac", "1", wav_path],
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE,
                )
            except Exception as exc:
                raise RuntimeError(f"ffmpeg conversion failed: {exc}") from exc

        out_prefix = tempfile.NamedTemporaryFile(delete=False).name
        cmd = [
            self.binary,
            "-m",
            self.model,
            "-f",
            wav_path,
            "-otxt",
            "-of",
            out_prefix,
            "--language",
            "en",
            "--threads",
            "2",
        ]
        try:
            proc = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            out_path = f"{out_prefix}.txt"
            if Path(out_path).exists():
                with open(out_path, "r", encoding="utf-8") as handle:
                    return handle.read().strip()
            stderr_text = proc.stderr.decode("utf-8", errors="ignore").strip()
            raise RuntimeError(f"whisper output missing: {stderr_text}")
        except subprocess.CalledProcessError as exc:
            stderr_text = exc.stderr.decode("utf-8", errors="ignore").strip()
            raise RuntimeError(f"whisper failed: {stderr_text or exc}") from exc
        finally:
            if wav_path != str(input_path):
                try:
                    os.remove(wav_path)
                except OSError:
                    pass
            try:
                Path(f"{out_prefix}.txt").unlink(missing_ok=True)
                Path(out_prefix).unlink(missing_ok=True)
            except OSError:
                pass
        raise RuntimeError("whisper returned empty output")
