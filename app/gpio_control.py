import time
from typing import Optional
from flask import current_app


class SprayerController:
    def __init__(self, pin: int) -> None:
        self.pin = pin
        self._gpio = None
        try:
            import RPi.GPIO as GPIO  # type: ignore
            self._gpio = GPIO
            self._gpio.setmode(GPIO.BCM)
            self._gpio.setup(self.pin, GPIO.OUT)
            self._gpio.output(self.pin, self._gpio.LOW)
        except Exception:
            self._gpio = None

    def spray_for_ms(self, duration_ms: int) -> None:
        if duration_ms <= 0:
            return
        if self._gpio is None:
            # Simulation on non-Pi
            time.sleep(duration_ms / 1000.0)
            return
        self._gpio.output(self.pin, self._gpio.HIGH)
        time.sleep(duration_ms / 1000.0)
        self._gpio.output(self.pin, self._gpio.LOW)


_sprayer_instance: Optional[SprayerController] = None


def get_sprayer() -> SprayerController:
    global _sprayer_instance
    if _sprayer_instance is None:
        _sprayer_instance = SprayerController(current_app.config["GPIO_PIN_SPRAYER"])
    return _sprayer_instance 