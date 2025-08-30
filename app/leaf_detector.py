import cv2
import numpy as np
import time
from typing import List, Tuple, Optional
import os
import requests
import json
from flask import current_app


class MobileNetSSDLeafDetector:
    """MobileNet-SSD based leaf detector for automatic leaf detection in video frames"""
    
    def __init__(self, confidence_threshold: float = 0.5):
        self.confidence_threshold = confidence_threshold
        self.net = None
        self.class_names = ['background', 'leaf']  # Simplified for leaf detection
        self.is_initialized = False
        
    def initialize_model(self, model_path: str = None, config_path: str = None):
        """Initialize MobileNet-SSD model"""
        try:
            # Try to load pre-trained model if available
            if model_path and os.path.exists(model_path):
                self.net = cv2.dnn.readNetFromCaffe(config_path, model_path)
                print("Loaded custom MobileNet-SSD model")
            else:
                # Use OpenCV's pre-trained MobileNet-SSD
                self.net = cv2.dnn.readNetFromCaffe(
                    'models/MobileNetSSD_deploy.prototxt',
                    'models/MobileNetSSD_deploy.caffemodel'
                )
                print("Loaded OpenCV MobileNet-SSD model")
            
            self.is_initialized = True
            return True
        except Exception as e:
            print(f"Failed to initialize MobileNet-SSD: {e}")
            # Fallback to basic contour detection
            self.is_initialized = False
            return False
    
    def detect_leaves(self, frame: np.ndarray) -> List[Tuple[int, int, int, int, float]]:
        """Detect leaves in frame and return bounding boxes with confidence scores"""
        if not self.is_initialized or self.net is None:
            # Fallback to basic contour detection
            return self._fallback_leaf_detection(frame)
        
        try:
            # Prepare input blob
            blob = cv2.dnn.blobFromImage(
                cv2.resize(frame, (300, 300)), 
                0.007843, 
                (300, 300), 
                127.5
            )
            
            # Forward pass
            self.net.setInput(blob)
            detections = self.net.forward()
            
            # Process detections
            leaves = []
            height, width = frame.shape[:2]
            
            for i in range(detections.shape[2]):
                confidence = detections[0, 0, i, 2]
                
                if confidence > self.confidence_threshold:
                    class_id = int(detections[0, 0, i, 1])
                    
                    # Filter for leaf class (assuming class_id 1 is leaf)
                    if class_id == 1:  # Adjust based on your model's class mapping
                        # Get bounding box coordinates
                        x1 = int(detections[0, 0, i, 3] * width)
                        y1 = int(detections[0, 0, i, 4] * height)
                        x2 = int(detections[0, 0, i, 5] * width)
                        y2 = int(detections[0, 0, i, 6] * height)
                        
                        # Ensure coordinates are within frame bounds
                        x1 = max(0, x1)
                        y1 = max(0, y1)
                        x2 = min(width, x2)
                        y2 = min(height, y2)
                        
                        # Only add if bounding box is large enough
                        if (x2 - x1) > 50 and (y2 - y1) > 50:
                            leaves.append((x1, y1, x2, y2, confidence))
            
            return leaves
            
        except Exception as e:
            print(f"Error in MobileNet-SSD detection: {e}")
            return self._fallback_leaf_detection(frame)
    
    def _fallback_leaf_detection(self, frame: np.ndarray) -> List[Tuple[int, int, int, int, float]]:
        """Fallback method using basic image processing for leaf detection"""
        try:
            # Convert to HSV for better leaf detection
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            
            # Define green color range for leaves
            lower_green = np.array([35, 50, 50])
            upper_green = np.array([85, 255, 255])
            
            # Create mask for green regions
            mask = cv2.inRange(hsv, lower_green, upper_green)
            
            # Apply morphological operations to clean up mask
            kernel = np.ones((5, 5), np.uint8)
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
            
            # Find contours
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            leaves = []
            for contour in contours:
                # Filter contours by area
                area = cv2.contourArea(contour)
                if area > 1000:  # Minimum area threshold
                    # Get bounding rectangle
                    x, y, w, h = cv2.boundingRect(contour)
                    
                    # Calculate confidence based on area and aspect ratio
                    aspect_ratio = w / h if h > 0 else 0
                    confidence = min(0.8, area / 10000)  # Cap confidence at 0.8
                    
                    # Only add if aspect ratio is reasonable for leaves
                    if 0.3 < aspect_ratio < 3.0:
                        leaves.append((x, y, x + w, y + h, confidence))
            
            return leaves
            
        except Exception as e:
            print(f"Error in fallback detection: {e}")
            return []
    
    def crop_leaf(self, frame: np.ndarray, bbox: Tuple[int, int, int, int]) -> np.ndarray:
        """Crop leaf region from frame based on bounding box"""
        x1, y1, x2, y2 = bbox
        return frame[y1:y2, x1:x2]
    
    def resize_leaf(self, leaf_crop: np.ndarray, target_size: Tuple[int, int] = (224, 224)) -> np.ndarray:
        """Resize cropped leaf to target size for API compatibility"""
        return cv2.resize(leaf_crop, target_size)
    
    def draw_detections(self, frame: np.ndarray, detections: List[Tuple[int, int, int, int, float]]) -> np.ndarray:
        """Draw detection bounding boxes on frame"""
        annotated_frame = frame.copy()
        
        for i, (x1, y1, x2, y2, confidence) in enumerate(detections):
            # Draw bounding box
            color = (0, 255, 0) if confidence > 0.7 else (0, 165, 255)
            cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, 2)
            
            # Draw label with confidence
            label = f'Leaf {i+1}: {confidence:.2f}'
            cv2.putText(annotated_frame, label, (x1, y1-10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        
        return annotated_frame


class AutomaticLeafDetectionService:
    """Service for automatic leaf detection and disease classification"""
    
    def __init__(self):
        self.detector = MobileNetSSDLeafDetector()
        self.is_running = False
        self.detection_interval = 2.0  # Detect every 2 seconds
        self.last_detection_time = 0
        self.current_detections = []
        
    def initialize(self):
        """Initialize the detection model"""
        # Try to initialize MobileNet-SSD
        model_initialized = self.detector.initialize_model()
        
        if not model_initialized:
            print("Using fallback contour-based detection")
        
        return True
    
    def detect_leaves_in_frame(self, frame: np.ndarray) -> List[Tuple[int, int, int, int, float]]:
        """Detect leaves in the current frame"""
        return self.detector.detect_leaves(frame)
    
    def process_detections(self, frame: np.ndarray, detections: List[Tuple[int, int, int, int, float]]) -> List[dict]:
        """Process detected leaves and classify diseases"""
        results = []
        
        for i, (x1, y1, x2, y2, confidence) in enumerate(detections):
            try:
                # Crop leaf region
                leaf_crop = self.detector.crop_leaf(frame, (x1, y1, x2, y2))
                
                # Resize for API compatibility
                leaf_resized = self.detector.resize_leaf(leaf_crop)
                
                # Save temporarily for API call
                temp_path = f"temp_leaf_{int(time.time())}_{i}.jpg"
                cv2.imwrite(temp_path, leaf_resized)
                
                try:
                    # Send to disease detection API
                    with open(temp_path, 'rb') as f:
                        files = {'image': f}
                        response = requests.post('http://localhost:5000/api/upload_detect', files=files)
                        
                        if response.status_code == 200:
                            result = response.json()
                            result.update({
                                'bbox': (x1, y1, x2, y2),
                                'confidence': confidence,
                                'leaf_index': i
                            })
                            results.append(result)
                        else:
                            results.append({
                                'error': f"API request failed: {response.status_code}",
                                'bbox': (x1, y1, x2, y2),
                                'confidence': confidence,
                                'leaf_index': i
                            })
                finally:
                    # Clean up temp file
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                        
            except Exception as e:
                results.append({
                    'error': f"Processing failed: {str(e)}",
                    'bbox': (x1, y1, x2, y2),
                    'confidence': confidence,
                    'leaf_index': i
                })
        
        return results
    
    def should_detect(self) -> bool:
        """Check if it's time to run detection"""
        current_time = time.time()
        if current_time - self.last_detection_time >= self.detection_interval:
            self.last_detection_time = current_time
            return True
        return False


# Global instance
leaf_detection_service = AutomaticLeafDetectionService() 