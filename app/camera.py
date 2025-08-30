import os
import time
import platform
from datetime import datetime
from typing import Optional
from flask import current_app
from PIL import Image, ImageDraw

class CameraService:
    def __init__(self, source: Optional[str] = None) -> None:
        """
        Initialize Camera Service
        Priority:
          1. Config-specified source
          2. Auto-detect (PiCamera2 → OpenCV → Mock)
        """
        self._picam2 = None
        self._cv2 = None
        self._cap = None
        self.source = source or "auto"

        # Detect if we are on Raspberry Pi
        is_raspberry_pi = platform.machine().startswith("arm") and platform.system() == "Linux"

        # Try PiCamera2 on Raspberry Pi
        if self.source in ("auto", "picamera2") and is_raspberry_pi:
            try:
                from picamera2 import Picamera2  # type: ignore
                self._picam2 = Picamera2()
                self._picam2.configure(self._picam2.create_still_configuration())
                self._picam2.start()
                time.sleep(0.5)
                self.source = "picamera2"
                print("[CameraService] Using PiCamera2")
                return
            except Exception as exc:
                print(f"[CameraService] PiCamera2 unavailable: {exc}")
                if self.source == "picamera2":
                    self.source = "mock"

        # Try OpenCV webcam
        if self.source in ("auto", "opencv"):
            try:
                import cv2  # type: ignore
                self._cv2 = cv2
                self._cap = cv2.VideoCapture(0)
                if self._cap is not None and self._cap.isOpened():
                    self.source = "opencv"
                    print("[CameraService] Using OpenCV webcam")
                    return
                else:
                    print("[CameraService] OpenCV camera not available")
                    self.source = "mock"
            except Exception as exc:
                print(f"[CameraService] OpenCV unavailable: {exc}")
                self.source = "mock"

        # Fallback to Mock
        self.source = "mock"
        print("[CameraService] Using mock camera")

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
            try:
                self._picam2.capture_file(file_path)
                return file_path
            except Exception as exc:
                print(f"[CameraService] PiCamera2 capture failed: {exc}")

        # OpenCV webcam
        if self.source == "opencv" and self._cv2 is not None and self._cap is not None:
            try:
                ret, frame = self._cap.read()
                if ret:
                    self._cv2.imwrite(file_path, frame)
                    return file_path
                else:
                    print("[CameraService] OpenCV capture failed")
            except Exception as exc:
                print(f"[CameraService] OpenCV capture exception: {exc}")

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


# Optional: Video feed generator for Flask streaming
def generate_video():
    camera = get_camera()
    while True:
        frame_path = camera.capture_image()
        with open(frame_path, "rb") as f:
            frame_bytes = f.read()
        yield (b"--frame\r\n"
               b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n")
        time.sleep(0.1)  # Limit FPS
