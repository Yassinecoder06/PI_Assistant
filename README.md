# Assistant Pi

Lightweight local AI assistant platform for Raspberry Pi 3 with:

- local LLM chat through Ollama
- live sensor integration (gyro + light)
- voice pipeline (Whisper STT + local TTS)
- gyroscope racing mini-game
- web dashboard hosted on the Pi

This README is aligned to the current project state in this repository.

## Project Layout

```text
assistant/
  backend/
    main.py
    router.py
  sensors/
    gyro.py
    light.py
  voice/
    stt.py
    tts.py
  game/
    game_logic.py
  frontend/
    index.html
    chat.html
    sensors.html
    arcade.html
    game.js
  docker/
    docker-compose.yml
  .env
  .env.example
  requirements.txt
```

## 1) System Requirements

- Raspberry Pi 3 (arm64 recommended)
- Python 3.9+
- Network access for model downloads
- I2C enabled if using physical MPU sensor

Install OS packages:

```bash
sudo apt update
sudo apt install -y \
  python3-pip python3-venv git i2c-tools \
  ffmpeg cmake build-essential \
  portaudio19-dev sox libatlas-base-dev \
  espeak-ng
```

Optional but useful:

```bash
sudo apt install -y piper
```

Enable I2C:

```bash
sudo raspi-config
# Interface Options -> I2C -> Enable
sudo reboot
```

## 2) Python Environment

From repo root:

```bash
cd /home/berry/assistant
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## 3) Configure Environment Variables

Copy and edit:

```bash
cp .env.example .env
```

Recommended .env values:

```env
OLLAMA_BASE_URL=http://127.0.0.1:11434

MODEL_PRIMARY_CHAT=tinyllama:latest
MODEL_FAST=qwen2.5:0.5b
MODEL_REASONING=qwen3:0.6b
MODEL_HEAVY=qwen3.5:0.8b

WHISPER_BIN=./whisper.cpp/build/bin/whisper-cli
WHISPER_MODEL=./whisper.cpp/models/ggml-base.en.bin

PIPER_BIN=piper
PIPER_MODEL=./models/en_US-lessac-medium.onnx
TTS_FALLBACK_BIN=/usr/bin/espeak-ng

APP_HOST=0.0.0.0
APP_PORT=6002
```

Notes:

- The router reads model names from .env. Changing .env updates runtime behavior after restart.
- TTS auto-falls back to espeak-ng if Piper fails.

## 4) Install and Pull Ollama Models

Install Ollama:

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

Pull models used by routing:

```bash
ollama pull tinyllama:latest
ollama pull qwen2.5:0.5b
ollama pull qwen3:0.6b
ollama pull qwen3.5:0.8b
```

Optional heavier model:

```bash
ollama pull qwen3.5:2b
```

## 5) Whisper.cpp STT Setup

```bash
cd /home/berry/assistant
if [ ! -d whisper.cpp ]; then git clone https://github.com/ggerganov/whisper.cpp; fi
cd whisper.cpp
make -j2
if [ ! -f ./models/ggml-base.en.bin ]; then bash ./models/download-ggml-model.sh base.en; fi
```

Quick check:

```bash
/home/berry/assistant/whisper.cpp/build/bin/whisper-cli --help | head -n 2
```

## 6) TTS Setup (Piper + Fallback)

Place a Piper voice model at:

```text
/home/berry/assistant/models/en_US-lessac-medium.onnx
```

Current behavior in this project:

- first try Piper
- if Piper is unavailable/broken, auto-fallback to espeak-ng

Manual checks:

```bash
command -v piper || true
command -v espeak-ng
```

If Piper errors about missing libs, fallback still allows TTS to work.

## 7) Run the App

```bash
cd /home/berry/assistant
source .venv/bin/activate
set -a && source .env && set +a
uvicorn backend.main:app --host "$APP_HOST" --port "$APP_PORT"
```

Open:

- http://raspberrypi:6002
- http://<pi-ip>:6002

## 8) HTTPS for Browser Microphone

Important: microphone capture in browsers requires secure context.

- works on localhost
- or works on HTTPS URL
- often blocked on plain HTTP IP addresses

For LAN HTTPS, Caddy is recommended.

Install Caddy:

```bash
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update
sudo apt install -y caddy
```

Create /etc/caddy/Caddyfile (replace PI_IP):

```text
https://PI_IP.nip.io {
    reverse_proxy 127.0.0.1:6002
    tls internal
}
```

Apply and verify:

```bash
sudo caddy validate --config /etc/caddy/Caddyfile
sudo systemctl restart caddy
sudo systemctl status caddy
```

Open:

- https://PI_IP.nip.io

Accept/trust the certificate in browser if prompted.

## 9) API Endpoints

- GET /gyro
- GET /light
- WS /sensor-stream
- POST /chat
- POST /game/start
- POST /voice/transcribe
- POST /voice/speak
- POST /game/comment

## 10) Quick Health Tests

Backend listening:

```bash
ss -ltnp | grep 6002
```

Voice end-to-end self-test:

```bash
cd /home/berry/assistant
set -a && source .env && set +a
source .venv/bin/activate
python - <<'PY'
from pathlib import Path
from voice.tts import PiperTTS
from voice.stt import WhisperSTT

wav = '/tmp/assistant_voice_test.wav'
tts = PiperTTS()
out = tts.speak('hello this is a local voice test', wav_path=wav, playback=False)
print('TTS_OUT=', out)
print('TTS_ERR=', tts.last_error)
print('TTS_FILE=', Path(wav).exists(), Path(wav).stat().st_size if Path(wav).exists() else 0)

stt = WhisperSTT()
print('WHISPER_BIN=', stt.binary)
print('WHISPER_MODEL_EXISTS=', Path(stt.model).exists())
print('STT_TEXT=', stt.transcribe(wav)[:160])
PY
```

## 11) Troubleshooting

No microphone input from browser:

- use HTTPS URL instead of HTTP IP URL
- allow microphone permission in browser
- test with a modern Chromium/Chrome/Edge build

TTS returns 500:

- check response detail from /voice/speak
- verify model file exists at PIPER_MODEL
- if Piper libs missing, fallback espeak-ng should still work

STT returns empty:

- verify ffmpeg is installed (webm to wav conversion)
- verify WHISPER_BIN and WHISPER_MODEL in .env
- restart backend after changing .env

Ollama unreachable:

- verify OLLAMA_BASE_URL in .env
- ensure ollama service is running
- pull missing models listed above

## 12) Optional Docker

```bash
cd /home/berry/assistant/docker
docker compose up -d
```

Host-native run is usually lighter and faster on Raspberry Pi 3.
