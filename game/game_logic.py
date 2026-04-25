from dataclasses import dataclass
from time import time
from typing import Dict


@dataclass
class GameState:
    running: bool = False
    started_at: float = 0.0
    high_score: int = 0
    last_score: int = 0

    def start(self) -> Dict[str, str]:
        self.running = True
        self.started_at = time()
        return {
            "status": "started",
            "title": "Highway Escape",
            "narration": "Starting Highway Escape. Tilt left or right to steer.",
        }

    def end(self, score: int) -> Dict[str, str]:
        self.running = False
        self.last_score = score
        if score > self.high_score:
            self.high_score = score
            return {"status": "ended", "summary": f"New high score: {score}."}
        return {"status": "ended", "summary": f"You scored {score}."}

    def comment(self, event: str, score: int) -> str:
        if event == "near_miss":
            return "Nice dodge."
        if event == "danger":
            return "Careful. Obstacle ahead."
        if event == "game_over":
            return f"Game over. You lasted {score} points."
        if score > 0 and score % 40 == 0:
            return f"Great run. Score {score}."
        return ""
