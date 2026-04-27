# Assistant Pi

## 1. Project Overview

Assistant Pi is a lightweight local AI assistant for Raspberry Pi 3 that includes:

- Web UI dashboard
- Voice interaction (Whisper STT + Piper TTS)
- Sensor integration (gyro + light)
- Gyroscope mini-games
- Remote LLM routing via Ollama

All model downloads happen through setup commands in this README. The Python code never downloads models.

## 2. Raspberry Pi Setup

Install system dependencies:

```bash
sudo apt update
sudo apt install git python3 python3-pip ffmpeg espeak-ng
```

## 3. Install whisper.cpp

```bash
git clone https://github.com/ggerganov/whisper.cpp
cd whisper.cpp
make
```

Download tiny English model:

```bash
bash ./models/download-ggml-model.sh tiny.en
```

## 4. Install Piper TTS

```bash
pip install piper-tts
```

Download the en_US-lessac-low voice model:

```bash
mkdir -p models
cd models
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/low/en_US-lessac-low.onnx
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/low/en_US-lessac-low.onnx.json
```

## 5. Environment Configuration

Create a `.env` file at the repo root with these values:

```env
WHISPER_BIN=./whisper.cpp/build/bin/whisper-cli
WHISPER_MODEL=./whisper.cpp/models/ggml-tiny.en.bin

PIPER_BIN=piper
PIPER_MODEL=./models/en_US-lessac-low.onnx

TTS_FALLBACK_BIN=/usr/bin/espeak-ng
```

## 6. Running the Backend

```bash
pip install -r requirements.txt
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

## 7. Voice Testing

Transcribe (multipart form upload with `audio` file):

```bash
curl -X POST http://localhost:8000/voice/transcribe \
  -F "audio=@/path/to/sample.wav"
```

Speak (JSON body with `text`):

```bash
curl -X POST http://localhost:8000/voice/speak \
  -H "Content-Type: application/json" \
  -d '{"text": "hello from pi"}' \
  --output tts.wav
```

## 8. Performance Notes for Raspberry Pi 3

- Whisper tiny keeps STT fast and CPU-friendly.
- Piper lessac-low reduces memory and latency for TTS.
- STT and TTS services are preloaded at startup to avoid per-request overhead.
