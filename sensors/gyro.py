import math
import time
from threading import Lock
from typing import Dict


class GyroReader:
    """Reads MPU6500/MPU6050 gyroscope values over I2C with simulation fallback."""

    MPU6500_ADDR = 0x68
    PWR_MGMT_1 = 0x6B
    GYRO_XOUT_H = 0x43

    def __init__(self, bus_id: int = 1) -> None:
        self._lock = Lock()
        self._simulated = True
        self._bus = None
        self._start = time.time()
        self._face_index = 0
        self._faces = ["front", "right", "back", "left"]
        self._last_trigger = 0.0
        self._trigger_cooldown = 0.6
        self._velocity_threshold = 100.0

        try:
            try:
                from smbus import SMBus  # type: ignore
            except Exception:
                from smbus2 import SMBus  # type: ignore

            self._bus = SMBus(bus_id)
            self._bus.write_byte_data(self.MPU6500_ADDR, self.PWR_MGMT_1, 0)
            self._simulated = False
        except Exception:
            self._simulated = True

    @staticmethod
    def _to_signed(high: int, low: int) -> int:
        value = (high << 8) | low
        if value > 32767:
            value -= 65536
        return value

    def _read_hardware(self) -> Dict[str, float]:
        assert self._bus is not None
        raw = self._bus.read_i2c_block_data(self.MPU6500_ADDR, self.GYRO_XOUT_H, 6)
        x = self._to_signed(raw[0], raw[1]) / 131.0
        y = self._to_signed(raw[2], raw[3]) / 131.0
        z = self._to_signed(raw[4], raw[5]) / 131.0
        return self._annotate_with_orientation(x, y, z)

    def _read_simulated(self) -> Dict[str, float]:
        t = time.time() - self._start
        x = 0.2 * math.sin(t * 0.7)
        y = 0.7 * math.sin(t * 1.3)
        z = 0.1 * math.cos(t * 0.5)
        return self._annotate_with_orientation(x, y, z)

    def _annotate_with_orientation(self, x: float, y: float, z: float) -> Dict[str, float]:
        raw_velocity = x
        now = time.time()
        if now - self._last_trigger >= self._trigger_cooldown:
            if raw_velocity > self._velocity_threshold:
                self._face_index = (self._face_index + 1) % len(self._faces)
                self._last_trigger = now
            elif raw_velocity < -self._velocity_threshold:
                self._face_index = (self._face_index - 1) % len(self._faces)
                self._last_trigger = now

        return {
            "x": round(x, 3),
            "y": round(y, 3),
            "z": round(z, 3),
            "orientation": self._faces[self._face_index],
            "raw_velocity": round(raw_velocity, 3),
        }

    def read(self) -> Dict[str, float]:
        with self._lock:
            if self._simulated:
                return self._read_simulated()
            try:
                return self._read_hardware()
            except Exception:
                self._simulated = True
                return self._read_simulated()
