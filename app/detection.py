import json
import random
from typing import Dict, Tuple
from flask import current_app
import requests


def detect_disease(image_path: str) -> Tuple[str, float, Dict]:
    backend = current_app.config["DETECTION_BACKEND"]
    if backend == "plantid":
        return _detect_with_plantid(image_path)
    elif backend == "tflite":
        return _detect_with_tflite(image_path)
    elif backend == "gemini":
        return _detect_with_gemini(image_path)
    else:
        return _detect_mock(image_path)


def _detect_mock(image_path: str) -> Tuple[str, float, Dict]:
    diseases = ["healthy", "blight", "rust", "mildew", "leaf spot"]
    disease = random.choice(diseases)
    severity = 0.0 if disease == "healthy" else round(random.uniform(20, 90), 1)
    data = {"backend": "mock", "image_path": image_path}
    return disease, severity, data


def _detect_with_plantid(image_path: str) -> Tuple[str, float, Dict]:
    api_key = current_app.config.get("PLANT_ID_API_KEY", "")
    if not api_key:
        return _detect_mock(image_path)
    url = "https://api.plant.id/v3/health_assessment"
    files = {"images": open(image_path, "rb")}
    payload = {"similar_images": False}
    headers = {"Api-Key": api_key}
    try:
        resp = requests.post(url, headers=headers, files=files, data={"data": json.dumps(payload)}, timeout=30)
        resp.raise_for_status()
        result = resp.json()
        # Simplify mapping; adapt as per actual API response structure
        disease = result.get("result", {}).get("disease", "unknown")
        severity = float(result.get("result", {}).get("severity", 0))
        return disease, severity, result
    except Exception as exc:
        return _detect_mock(image_path)


def _detect_with_tflite(image_path: str) -> Tuple[str, float, Dict]:
    # Placeholder: implement TFLite inference if model is available
    return _detect_mock(image_path)


def _detect_with_gemini(image_path: str) -> Tuple[str, float, Dict]:
    api_key = current_app.config.get("GEMINI_API_KEY", "")
    model_name = current_app.config.get("GEMINI_MODEL", "gemini-1.5-pro")
    if not api_key:
        return _detect_mock(image_path)
    try:
        import google.generativeai as genai  # type: ignore
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name)
        prompt = (
            "You are an agricultural plant disease assistant. Given a plant leaf image, "
            "respond with a compact JSON object with keys 'disease' (string) and 'severity' (number 0-100). "
            "If healthy, set disease='healthy' and severity=0."
        )
        with open(image_path, "rb") as f:
            image_bytes = f.read()
        result = model.generate_content([
            {"mime_type": "image/jpeg", "data": image_bytes},
            prompt,
        ])
        text = result.text or "{}"
        # Try to find JSON in the response
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            parsed = json.loads(text[start:end+1])
            disease = str(parsed.get("disease", "unknown"))
            sev = parsed.get("severity", 0)
            try:
                severity = float(sev)
            except Exception:
                severity = 0.0
            severity = max(0.0, min(100.0, severity))
            return disease, severity, {"backend": "gemini", "raw": text}
        return _detect_mock(image_path)
    except Exception as exc:
        return _detect_mock(image_path) 