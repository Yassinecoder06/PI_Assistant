import asyncio
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List

from fastapi import BackgroundTasks, FastAPI, File, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from backend.router import ModelRouter, OllamaClient, detect_start_game_intent
from game.game_logic import GameState
from sensors.gyro import GyroReader
from sensors.light import LightReader
from voice.stt import WhisperSTT
from voice.tts import PiperTTS

BASE_DIR = Path(__file__).resolve().parents[1]
FRONTEND_DIR = BASE_DIR / "frontend"

app = FastAPI(title="assistant_pi", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

router = ModelRouter()
ollama = OllamaClient(base_url=os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434"))
gyro = GyroReader()
light = LightReader()
game = GameState()
stt_engine = WhisperSTT()
tts_engine = PiperTTS()


class ChatRequest(BaseModel):
    message: str
    history: List[Dict[str, str]] = []


class ChatResponse(BaseModel):
    reply: str
    model: str
    task: str
    start_game: bool = False


class GameCommentRequest(BaseModel):
    event: str = ""
    score: int = 0


async def read_sensor_snapshot() -> Dict[str, Any]:
    return {
        "gyro": gyro.read(),
        "light": light.read(),
    }


@app.get("/")
async def root() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/chat")
async def chat_page() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "chat.html")


@app.get("/sensors")
async def sensors_page() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "sensors.html")


@app.get("/arcade")
async def arcade_page() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "arcade.html")


@app.get("/gyro")
async def get_gyro() -> Dict[str, float]:
    return gyro.read()


@app.get("/light")
async def get_light() -> Dict[str, float]:
    return light.read()


@app.websocket("/sensor-stream")
async def sensor_stream(websocket: WebSocket) -> None:
    await websocket.accept()
    try:
        while True:
            payload = await read_sensor_snapshot()
            await websocket.send_text(json.dumps(payload))
            await asyncio.sleep(0.1)
    except WebSocketDisconnect:
        return


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    text = req.message.strip()
    if not text:
        raise HTTPException(status_code=400, detail="message cannot be empty")

    if detect_start_game_intent(text):
        return ChatResponse(
            reply="Starting Highway Escape. Tilt the device to steer.",
            model="local-rule",
            task="game_start",
            start_game=True,
        )

    route_decision = router.route(text)

    sensor_ctx = await read_sensor_snapshot()
    system_prompt = (
        "You are a local assistant. Keep replies concise. "
        "When relevant, use this live sensor state: "
        f"{sensor_ctx}."
    )

    try:
        reply = await ollama.generate(
            model=route_decision.model,
            prompt=text,
            system_prompt=system_prompt,
        )
    except Exception:
        reply = (
            "I can still help locally, but Ollama is unreachable right now. "
            "Check if Ollama is running and models are pulled."
        )

    return ChatResponse(
        reply=reply,
        model=route_decision.model,
        task=route_decision.task,
        start_game=False,
    )


@app.post("/game/start")
async def game_start() -> Dict[str, str]:
    return game.start()


@app.post("/game/comment")
async def game_comment(req: GameCommentRequest) -> Dict[str, str]:
    text = game.comment(req.event, req.score)
    return {"comment": text}


@app.post("/voice/transcribe")
async def voice_transcribe(audio: UploadFile = File(...)) -> Dict[str, str]:
    suffix = Path(audio.filename or "voice.wav").suffix or ".wav"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await audio.read()
        tmp.write(content)
        temp_path = tmp.name

    text = stt_engine.transcribe(temp_path)
    try:
        os.remove(temp_path)
    except OSError:
        pass

    return {"text": text}


@app.post("/voice/speak")
async def voice_speak(payload: Dict[str, str], background_tasks: BackgroundTasks) -> FileResponse:
    text = payload.get("text", "")
    if not text.strip():
        raise HTTPException(status_code=400, detail="text cannot be empty")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_wav:
        wav_path = tmp_wav.name

    wav = tts_engine.speak(text, wav_path=wav_path, playback=False)
    if not wav:
        raise HTTPException(status_code=500, detail=f"tts failed: {tts_engine.last_error or 'unknown error'}")

    background_tasks.add_task(os.remove, wav)
    return FileResponse(wav, media_type="audio/wav", filename="tts.wav")


app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")
