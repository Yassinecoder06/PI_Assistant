import math
import time
from threading import Lock
from typing import Dict, List


class LightReader:
    """Reads digital light sensor pins; falls back to simulated signal if unavailable."""

    def __init__(self, pins: List[int] = None) -> None:
        self._lock = Lock()
        self._simulated = True
        self._pins = pins or [18]
        self._start = time.time()

        try:
            import RPi.GPIO as GPIO  # type: ignore

            GPIO.setwarnings(False)
            GPIO.setmode(GPIO.BCM)
            for pin in self._pins:
                GPIO.setup(pin, GPIO.IN)
            self._gpio = GPIO
            self._simulated = False
        except Exception:
            self._gpio = None
            self._simulated = True

    def read(self) -> Dict[str, float]:
        with self._lock:
            if self._simulated:
                t = time.time() - self._start
                value = 0.5 + 0.45 * math.sin(t * 0.2)
                normalized = round(max(0.0, min(1.0, value)), 3)
                pin_states = {str(pin): int(normalized > 0.5) for pin in self._pins}
                return {"value": normalized, "pins": pin_states, "mode": "simulated"}
            try:
                pin_states = {str(pin): int(self._gpio.input(pin)) for pin in self._pins}
                active = sum(1 for state in pin_states.values() if state == 1)
                value = round(active / max(1, len(self._pins)), 3)
                return {"value": value, "pins": pin_states, "mode": "hardware"}
            except Exception:
                self._simulated = True
                return {"value": 0.5, "pins": {}, "mode": "simulated"}
