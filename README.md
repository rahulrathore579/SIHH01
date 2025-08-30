# Intelligence Sprinkle Pesticide System

A Raspberry Pi project that captures plant leaf images, detects disease (mock/TFLite/external API/Gemini), decides spraying action, and controls a sprayer via GPIO. Includes a simple web UI to trigger and view logs.

## Features
- Capture via Pi Camera (`picamera2`) or USB cam (`opencv`) or mock
- Detection backends: mock (default), Plant.id API, Gemini (image understanding), or TFLite placeholder
- Decision rules based on severity thresholds
- GPIO control for relay-driven sprayer (BCM pin configurable)
- SQLite logging: captures, detections, actions
- Web UI dashboard at `http://<pi-ip>:5000`

## Hardware
- Raspberry Pi with CSI camera or USB webcam
- Relay module controlling pump/sprayer
- Default sprayer pin: BCM 17 (configurable)

## Setup (Raspberry Pi OS)
```bash
sudo apt update
sudo apt install -y python3-pip python3-venv python3-picamera2
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
# Optional for GPIO
pip install RPi.GPIO
```

If using USB webcam:
```bash
sudo apt install -y v4l-utils
```

## Configure
Copy and edit `.env`:
```bash
cp .env.example .env
# edit as needed
```
Key variables:
- `CAMERA_SOURCE`: `picamera2` | `opencv` | `mock`
- `DETECTION_BACKEND`: `mock` | `plantid` | `gemini` | `tflite`
- `PLANT_ID_API_KEY`: API key for Plant.id (if used)
- `GEMINI_API_KEY`: Google AI Studio API key
- `GEMINI_MODEL`: Recommended `gemini-1.5-pro` for best vision accuracy on disease detection prompts; `gemini-1.5-flash` is faster/cheaper with slightly lower accuracy
- Thresholds and durations: `SEVERITY_LOW_THRESHOLD`, `SEVERITY_HIGH_THRESHOLD`, `SPRAY_DURATION_LOW_MS`, `SPRAY_DURATION_HIGH_MS`
- `GPIO_PIN_SPRAYER`: BCM pin for relay

## Run
```bash
source .venv/bin/activate
python run.py
# visit http://<pi-ip>:5000
```

## API
- `POST /api/capture_detect`: Captures image, runs detection, actuates sprayer, logs results.
- `GET /images/<filename>`: Serves captured images.

## Service (optional)
Create a systemd service `/etc/systemd/system/sprinkle.service`:
```ini
[Unit]
Description=Intelligence Sprinkle Pesticide System
After=network.target

[Service]
WorkingDirectory=/home/pi/sprinkle_system
Environment="PYTHONUNBUFFERED=1"
ExecStart=/home/pi/sprinkle_system/.venv/bin/python run.py
Restart=always
User=pi

[Install]
WantedBy=multi-user.target
```
```bash
sudo systemctl daemon-reload
sudo systemctl enable sprinkle --now
```

## Notes
- Default detection is mock. To use Gemini, set `DETECTION_BACKEND=gemini` and add `GEMINI_API_KEY` (and optional `GEMINI_MODEL`).
- Recommended Gemini versions: `gemini-1.5-pro` (accuracy) or `gemini-1.5-flash` (speed/cost). Use `pro` if you want better detection reliability.
- TFLite path is a placeholder; integrate your model in `app/detection.py`.
- On non-Pi machines, GPIO actions are simulated (no-op with sleep). 