import os
import shutil
import subprocess
import tempfile
from pathlib import Path


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
        input_path = Path(audio_path)
        wav_path = str(input_path)

        if input_path.suffix.lower() != ".wav":
            ffmpeg = shutil.which("ffmpeg")
            if not ffmpeg:
                return ""
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_wav:
                wav_path = tmp_wav.name
            try:
                subprocess.run(
                    [ffmpeg, "-y", "-i", str(input_path), "-ar", "16000", "-ac", "1", wav_path],
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            except Exception:
                return ""

        cmd = [self.binary, "-m", self.model, "-f", wav_path, "-otxt", "-of", "/tmp/whisper_out"]
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            out_path = "/tmp/whisper_out.txt"
            if os.path.exists(out_path):
                with open(out_path, "r", encoding="utf-8") as f:
                    return f.read().strip()
        except Exception:
            return ""
        finally:
            if wav_path != str(input_path):
                try:
                    os.remove(wav_path)
                except OSError:
                    pass
        return ""
