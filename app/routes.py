from flask import Blueprint, current_app, jsonify, render_template, request, send_from_directory, Response
from .camera import get_camera
from .detection import detect_disease
from .gpio_control import get_sprayer
from .db import insert_capture, insert_detection, insert_action, get_recent
from .video_detection import video_service
import json
import os
import uuid
import cv2
import time

bp = Blueprint("routes", __name__)


@bp.route("/")
def index():
    captures, detections, actions = get_recent(limit=20)
    return render_template(
        "index.html",
        captures=captures,
        detections=detections,
        actions=actions,
        low=current_app.config["SEVERITY_LOW_THRESHOLD"],
        high=current_app.config["SEVERITY_HIGH_THRESHOLD"],
    )


@bp.route('/images/<path:filename>')
def serve_image(filename: str):
    image_dir = current_app.config["IMAGE_DIR"]
    return send_from_directory(image_dir, filename)


@bp.route("/video_feed")
def video_feed():
    """Video streaming route"""
    def generate():
        while True:
            frame = video_service.get_frame()
            if frame is not None:
                # Encode frame to JPEG
                ret, buffer = cv2.imencode('.jpg', frame)
                if ret:
                    frame_bytes = buffer.tobytes()
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            time.sleep(0.1)  # 10 FPS
    
    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')


@bp.route("/api/start_video", methods=["POST"])
def start_video():
    """Start video capture"""
    try:
        camera_index = request.json.get('camera_index', 0)
        if video_service.start_camera(camera_index):
            return jsonify({"status": "success", "message": "Video started"})
        else:
            return jsonify({"status": "error", "message": "Failed to start camera"}), 500
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@bp.route("/api/stop_video", methods=["POST"])
def stop_video():
    """Stop video capture"""
    try:
        video_service.stop_camera()
        return jsonify({"status": "success", "message": "Video stopped"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@bp.route("/api/toggle_automatic_mode", methods=["POST"])
def toggle_automatic_mode():
    """Toggle between manual and automatic detection modes"""
    try:
        is_automatic = video_service.toggle_automatic_mode()
        mode_name = "automatic" if is_automatic else "manual"
        return jsonify({
            "status": "success", 
            "message": f"Switched to {mode_name} mode",
            "automatic_mode": is_automatic
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@bp.route("/api/video_click", methods=["POST"])
def video_click():
    """Handle click on video to create leaf region (manual mode only)"""
    try:
        if video_service.automatic_mode:
            return jsonify({"error": "Manual selection disabled in automatic mode"}), 400
            
        data = request.json
        x = data.get('x')
        y = data.get('y')
        
        if x is None or y is None:
            return jsonify({"error": "Missing x or y coordinates"}), 400
        
        # Add click region to video service
        region = video_service.add_click_region(x, y)
        if region:
            return jsonify({
                "status": "success", 
                "message": "Region created",
                "region": region,
                "region_count": len(video_service.selected_regions)
            })
        else:
            return jsonify({"error": "Failed to create region (try again in 1 second)"}), 400
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/api/detect_leaf", methods=["POST"])
def detect_leaf():
    """Detect disease in a specific leaf region (manual mode only)"""
    try:
        if video_service.automatic_mode:
            return jsonify({"error": "Manual detection disabled in automatic mode"}), 400
            
        data = request.json
        region_index = data.get('region_index', 0)
        
        result = video_service.detect_and_classify_leaf(region_index)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/api/get_automatic_detections", methods=["GET"])
def get_automatic_detections():
    """Get results from automatic leaf detection"""
    try:
        if not video_service.automatic_mode:
            return jsonify({"error": "Automatic mode not enabled"}), 400
            
        detections = video_service.get_automatic_detections()
        return jsonify({
            "status": "success",
            "detections": detections,
            "count": len(detections)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/api/capture_detect", methods=["POST"]) 
def capture_detect():
    camera = get_camera()
    image_path = camera.capture_image()
    capture_id = insert_capture(image_path)

    disease, severity, raw = detect_disease(image_path)
    detection_id = insert_detection(capture_id, disease, severity, json.dumps(raw))

    action, duration_ms = decide_action(severity)
    if duration_ms > 0:
        sprayer = get_sprayer()
        sprayer.spray_for_ms(duration_ms)
    insert_action(detection_id, action, duration_ms)

    # Expose image URL from filename
    filename = os.path.basename(image_path)
    image_url = f"/images/{filename}"

    return jsonify(
        {
            "image_path": image_path,
            "image_url": image_url,
            "disease": disease,
            "severity": severity,
            "action": action,
            "duration_ms": duration_ms,
        }
    )


@bp.route("/api/upload_detect", methods=["POST"]) 
def upload_detect():
    if "image" not in request.files:
        return jsonify({"error": "No image file provided"}), 400
    file = request.files["image"]
    if file.filename == "":
        return jsonify({"error": "Empty filename"}), 400
    # Save upload
    ext = os.path.splitext(file.filename)[1].lower() or ".jpg"
    filename = f"upload_{uuid.uuid4().hex}{ext}"
    image_dir = current_app.config["IMAGE_DIR"]
    os.makedirs(image_dir, exist_ok=True)
    save_path = os.path.join(image_dir, filename)
    file.save(save_path)

    # Log capture
    capture_id = insert_capture(save_path)

    # Detect
    disease, severity, raw = detect_disease(save_path)
    detection_id = insert_detection(capture_id, disease, severity, json.dumps(raw))

    # Do NOT actuate GPIO in PC upload flow
    action = "none"
    duration_ms = 0
    insert_action(detection_id, action, duration_ms)

    return jsonify(
        {
            "image_url": f"/images/{filename}",
            "disease": disease,
            "severity": severity,
            "class": "healthy" if (severity or 0) <= current_app.config["SEVERITY_LOW_THRESHOLD"] and (disease or "").lower() == "healthy" else "infected",
            "action": action,
            "duration_ms": duration_ms,
        }
    )


def decide_action(severity: float):
    low = current_app.config["SEVERITY_LOW_THRESHOLD"]
    high = current_app.config["SEVERITY_HIGH_THRESHOLD"]
    if severity < low:
        return "none", 0
    if severity < high:
        return "spray_short", int(current_app.config["SPRAY_DURATION_LOW_MS"])
    return "spray_long", int(current_app.config["SPRAY_DURATION_HIGH_MS"]) 