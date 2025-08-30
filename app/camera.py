import os
import time
from datetime import datetime
from typing import Optional
from flask import current_app
from PIL import Image, ImageDraw, ImageFont


class CameraService:
    def __init__(self, source: str) -> None:
        self.source = source
        self._picam2 = None
        self._cv2 = None
        if source == "picamera2":
            try:
                from picamera2 import Picamera2  # type: ignore
                self._picam2 = Picamera2()
                self._picam2.configure(self._picam2.create_still_configuration())
                self._picam2.start()
                time.sleep(0.5)
            except Exception as exc:
                self.source = "mock"
        elif source == "opencv":
            try:
                import cv2  # type: ignore
                self._cv2 = cv2
                self._cap = cv2.VideoCapture(0)
                if not self._cap.isOpened():
                    self.source = "mock"
            except Exception:
                self.source = "mock"

    def capture_image(self) -> str:
        image_dir = current_app.config["IMAGE_DIR"]
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = os.path.join(image_dir, f"capture_{ts}.jpg")

        if self.source == "picamera2" and self._picam2 is not None:
            self._picam2.capture_file(file_path)
            return file_path

        if self.source == "opencv" and self._cv2 is not None:
            ret, frame = self._cap.read()
            if ret:
                self._cv2.imwrite(file_path, frame)
                return file_path

        # Mock image
        img = Image.new("RGB", (640, 480), color=(60, 120, 60))
        draw = ImageDraw.Draw(img)
        text = f"Mock Leaf\n{ts}"
        draw.text((20, 20), text, fill=(255, 255, 255))
        img.save(file_path, format="JPEG", quality=90)
        return file_path


_camera_instance: Optional[CameraService] = None


def get_camera() -> CameraService:
    global _camera_instance
    if _camera_instance is None:
        _camera_instance = CameraService(current_app.config["CAMERA_SOURCE"])
    return _camera_instance 