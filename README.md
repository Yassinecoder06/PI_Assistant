# assistant_pi

Lightweight local AI assistant platform for Raspberry Pi 3 with sensor integration, voice pipeline, and gyroscope racing game.

## Features

- Local chat assistant using Ollama small models
- Model router for low-latency task selection
- Sensor endpoints (`/gyro`, `/light`) + real-time stream (`/sensor-stream`)
- Voice pipeline: Whisper.cpp STT + Piper TTS
- Arcade mini-game controlled by MPU6500 gyroscope tilt
- Web dashboard hosted locally on port `8080`

## Project Layout

```text
assistant_pi/
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
  requirements.txt
```

## 1) Raspberry Pi 3 Setup (Python 3.9+)

```bash
sudo apt update
sudo apt install -y python3-pip python3-venv git i2c-tools portaudio19-dev sox libatlas-base-dev ffmpeg
```

Enable I2C:

```bash
sudo raspi-config
# Interface Options -> I2C -> Enable
sudo reboot
```

Create env and install Python deps:

```bash
cd assistant_pi
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## 2) Install Ollama + Pull Small Models

Install Ollama (official install script):

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

Pull models (required):

```bash
ollama pull tinyllama:latest
ollama pull qwen2.5:0.5b
ollama pull gemma3:270m
```

Optional:

```bash
ollama pull deepseek-r1:1.5b
```

## 3) Whisper.cpp (STT)

```bash
cd ~/assistant_pi
git clone https://github.com/ggerganov/whisper.cpp
cd whisper.cpp
make -j2
bash ./models/download-ggml-model.sh base.en
```

Set environment variable if model path differs:

```bash
export WHISPER_BIN=~/assistant_pi/whisper.cpp/main
export WHISPER_MODEL=~/assistant_pi/whisper.cpp/models/ggml-base.en.bin

Note: browser microphone recordings are uploaded as WebM. The backend uses `ffmpeg`
to convert to WAV before Whisper.cpp transcription.
```

## 4) Piper (TTS)

Install Piper (package name may vary by OS image):

```bash
sudo apt install -y piper
```

Download a small voice model to `~/assistant_pi/models` and set:

```bash
export PIPER_BIN=piper
export PIPER_MODEL=~/assistant_pi/models/en_US-lessac-medium.onnx
```

## 5) Run the Platform

From project root:

```bash
cd ~/assistant_pi
source .venv/bin/activate
uvicorn backend.main:app --host 0.0.0.0 --port 8080
```

Open:

- `http://raspberrypi:8080`
- `http://<pi-ip>:8080`

## API Endpoints

- `GET /gyro` -> current gyroscope values
- `GET /light` -> light sensor value
- `WebSocket /sensor-stream` -> live gyro + light + button stream
- `POST /chat` -> assistant chat + model routing
- `POST /game/start` -> start racing game

Additional voice/game helpers:

- `POST /voice/transcribe`
- `POST /voice/speak`
- `POST /game/comment`

## Model Routing Logic

Current routing (`backend/router.py`):

- Sensor queries -> `qwen2.5:0.5b`
- Simple reasoning/classification -> `gemma3:270m`
- Regular chat -> `tinyllama:1.1b`
- Heavy reasoning prompt keywords -> `deepseek-r1:1.5b` (optional)

## Performance Notes for Pi 3

- Keep `num_ctx` small (1024) and answer length limited
- Use one request at a time for best responsiveness
- Prefer quantized smallest available model variants in Ollama
- Run without Docker for lowest RAM overhead
- Sensor stream runs at ~10Hz to balance CPU and responsiveness

## Optional Docker Run

```bash
cd assistant_pi/docker
docker compose up -d
```

For Pi 3, host-native execution is typically better than Docker.
