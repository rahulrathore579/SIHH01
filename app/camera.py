import os
import time
from datetime import datetime
from typing import Optional
from flask import current_app
from PIL import Image, ImageDraw, ImageFont


class CameraService:
    def __init__(self, source: Optional[str] = None) -> None:
        """
        Initialize Camera Service
        - If source is provided in config, use that ("picamera2" | "opencv" | "mock")
        - Otherwise, auto-detect:
            1. Try PiCamera2
            2. Fallback to OpenCV webcam
            3. Fallback to mock image
        """
        self._picam2 = None
        self._cv2 = None
        self._cap = None

        if source:
            self.source = source
        else:
            self.source = "auto"

        if self.source in ("auto", "picamera2"):
            try:
                from picamera2 import Picamera2  # type: ignore
                self._picam2 = Picamera2()
                self._picam2.configure(self._picam2.create_still_configuration())
                self._picam2.start()
                time.sleep(0.5)
                self.source = "picamera2"
                return
            except Exception:
                if self.source == "picamera2":
                    self.source = "mock"

        if self.source in ("auto", "opencv"):
            try:
                import cv2  # type: ignore
                self._cv2 = cv2
                self._cap = cv2.VideoCapture(0)
                if self._cap.isOpened():
                    self.source = "opencv"
                    return
                else:
                    self.source = "mock"
            except Exception:
                self.source = "mock"

        if self.source == "auto":
            self.source = "mock"

    def capture_image(self) -> str:
        """
        Capture image depending on active source.
        """
        image_dir = current_app.config.get("IMAGE_DIR", "images")
        os.makedirs(image_dir, exist_ok=True)

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = os.path.join(image_dir, f"capture_{ts}.jpg")

        # Raspberry Pi camera
        if self.source == "picamera2" and self._picam2 is not None:
            self._picam2.capture_file(file_path)
            return file_path

        # OpenCV webcam
        if self.source == "opencv" and self._cv2 is not None and self._cap is not None:
            ret, frame = self._cap.read()
            if ret:
                self._cv2.imwrite(file_path, frame)
                return file_path

        # Mock image fallback
        img = Image.new("RGB", (640, 480), color=(60, 120, 60))
        draw = ImageDraw.Draw(img)
        text = f"Mock Leaf\n{ts}"
        draw.text((20, 20), text, fill=(255, 255, 255))
        img.save(file_path, format="JPEG", quality=90)
        return file_path


_camera_instance: Optional[CameraService] = None


def get_camera() -> CameraService:
    """
    Singleton accessor for CameraService.
    Source priority:
    - Config["CAMERA_SOURCE"] if set
    - Auto-detect otherwise
    """
    global _camera_instance
    if _camera_instance is None:
        source = current_app.config.get("CAMERA_SOURCE", None)
        _camera_instance = CameraService(source)
    return _camera_instance
