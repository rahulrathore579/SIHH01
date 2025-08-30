import os
from dotenv import load_dotenv


def load_config(app):
    load_dotenv()

    base_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    data_dir = os.path.join(base_dir, "data")
    image_dir = os.path.join(data_dir, "images")
    db_dir = os.path.join(data_dir, "db")

    app.config.update(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-secret-key"),
        BASE_DIR=base_dir,
        DATA_DIR=os.environ.get("DATA_DIR", data_dir),
        IMAGE_DIR=os.environ.get("IMAGE_DIR", image_dir),
        DB_DIR=os.environ.get("DB_DIR", db_dir),
        DATABASE_PATH=os.environ.get("DATABASE_PATH", os.path.join(db_dir, "sprinkle.db")),
        CAMERA_SOURCE=os.environ.get("CAMERA_SOURCE", "picamera2"),  # picamera2|opencv|mock
        DETECTION_BACKEND=os.environ.get("DETECTION_BACKEND", "gemini"),  # tflite|plantid|gemini|mock
        PLANT_ID_API_KEY=os.environ.get("PLANT_ID_API_KEY", ""),
        GEMINI_API_KEY=os.environ.get("GEMINI_API_KEY", "AIzaSyDHW3ArABy2ogwl7twkVXT0oqDR4ykioxw"),
        GEMINI_MODEL=os.environ.get("GEMINI_MODEL", "gemini-2.5-flash"),
        SEVERITY_LOW_THRESHOLD=float(os.environ.get("SEVERITY_LOW_THRESHOLD", 30)),
        SEVERITY_HIGH_THRESHOLD=float(os.environ.get("SEVERITY_HIGH_THRESHOLD", 70)),
        SPRAY_DURATION_LOW_MS=int(os.environ.get("SPRAY_DURATION_LOW_MS", 2000)),
        SPRAY_DURATION_HIGH_MS=int(os.environ.get("SPRAY_DURATION_HIGH_MS", 5000)),
        GPIO_PIN_SPRAYER=int(os.environ.get("GPIO_PIN_SPRAYER", 17)),  # BCM pin
        STATIC_URL_PATH=os.environ.get("STATIC_URL_PATH", "/static"),
    ) 