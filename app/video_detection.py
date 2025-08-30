import cv2
import numpy as np
import time
from typing import List, Tuple, Optional
import os
from flask import current_app
import requests
import json
from .leaf_detector import leaf_detection_service


class LightweightLeafSelector:
    """Lightweight leaf selector for Raspberry Pi - user clicks to select leaf regions"""
    
    def __init__(self):
        self.region_size = 150  # Fixed region size for consistency
        self.last_click_time = 0
        self.click_cooldown = 1.0  # Prevent rapid clicks
        
    def create_region_from_click(self, frame: np.ndarray, click_x: int, click_y: int) -> Optional[Tuple[int, int, int, int]]:
        """Create a bounding box region around the clicked point"""
        current_time = time.time()
        
        # Prevent rapid clicking
        if current_time - self.last_click_time < self.click_cooldown:
            return None
        
        self.last_click_time = current_time
        
        frame_height, frame_width = frame.shape[:2]
        half_size = self.region_size // 2
        
        # Calculate region bounds
        x1 = max(0, click_x - half_size)
        y1 = max(0, click_y - half_size)
        x2 = min(frame_width, click_x + half_size)
        y2 = min(frame_height, click_y + half_size)
        
        # Ensure minimum size
        if (x2 - x1) < 100 or (y2 - y1) < 100:
            return None
            
        return (x1, y1, x2, y2)
    
    def crop_leaf(self, frame: np.ndarray, bbox: Tuple[int, int, int, int]) -> np.ndarray:
        """Crop leaf region from frame based on bounding box"""
        x1, y1, x2, y2 = bbox
        return frame[y1:y2, x1:x2]


class VideoCaptureService:
    def __init__(self):
        self.cap = None
        self.selector = LightweightLeafSelector()
        self.is_running = False
        self.current_frame = None
        self.selected_regions = []  # Store user-selected regions
        self.automatic_mode = False  # Toggle between manual and automatic detection
        self.last_auto_detection_time = 0
        self.auto_detection_interval = 3.0  # Run automatic detection every 3 seconds
        
    def start_camera(self, camera_index: int = 0):
        """Start video capture"""
        try:
            self.cap = cv2.VideoCapture(camera_index)
            if not self.cap.isOpened():
                print(f"Failed to open camera {camera_index}")
                return False
            
            # Set camera properties for Pi optimization
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self.cap.set(cv2.CAP_PROP_FPS, 15)  # Lower FPS for Pi performance
            
            # Initialize leaf detection service
            leaf_detection_service.initialize()
            
            self.is_running = True
            print("Camera started successfully")
            return True
        except Exception as e:
            print(f"Error starting camera: {e}")
            return False
    
    def stop_camera(self):
        """Stop video capture"""
        self.is_running = False
        if self.cap:
            self.cap.release()
            self.cap = None
        self.selected_regions.clear()
        self.current_frame = None
        print("Camera stopped and resources released")
    
    def toggle_automatic_mode(self):
        """Toggle between manual and automatic detection modes"""
        self.automatic_mode = not self.automatic_mode
        if self.automatic_mode:
            print("Switched to automatic leaf detection mode")
        else:
            print("Switched to manual leaf selection mode")
        return self.automatic_mode
    
    def get_frame(self) -> Optional[np.ndarray]:
        """Get current frame with selected regions or automatic detections highlighted"""
        if not self.is_running or not self.cap:
            return None
        
        ret, frame = self.cap.read()
        if not ret:
            return None
        
        # Run automatic detection if enabled and it's time
        if self.automatic_mode and self._should_run_auto_detection():
            self._run_automatic_detection(frame)
        
        # Draw detections on frame
        annotated_frame = frame.copy()
        
        if self.automatic_mode:
            # Draw automatic detections
            annotated_frame = leaf_detection_service.detector.draw_detections(
                annotated_frame, 
                leaf_detection_service.current_detections
            )
        else:
            # Draw manual selections
            for i, bbox in enumerate(self.selected_regions):
                x1, y1, x2, y2 = bbox
                # Draw rectangle around selected region
                cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(annotated_frame, f'Region {i+1}', 
                           (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        self.current_frame = annotated_frame
        return annotated_frame
    
    def _should_run_auto_detection(self) -> bool:
        """Check if it's time to run automatic detection"""
        current_time = time.time()
        if current_time - self.last_auto_detection_time >= self.auto_detection_interval:
            self.last_auto_detection_time = current_time
            return True
        return False
    
    def _run_automatic_detection(self, frame: np.ndarray):
        """Run automatic leaf detection on the current frame"""
        try:
            # Detect leaves in frame
            detections = leaf_detection_service.detect_leaves_in_frame(frame)
            leaf_detection_service.current_detections = detections
            
            # Process detections if any found
            if detections:
                print(f"Detected {len(detections)} leaves automatically")
                # Process detections asynchronously to avoid blocking video feed
                self._process_detections_async(frame, detections)
                
        except Exception as e:
            print(f"Error in automatic detection: {e}")
    
    def _process_detections_async(self, frame: np.ndarray, detections: List[Tuple[int, int, int, int, float]]):
        """Process detections asynchronously to avoid blocking video feed"""
        try:
            # Process detections and get results
            results = leaf_detection_service.process_detections(frame, detections)
            
            # Log results to database
            for result in results:
                if 'error' not in result:
                    self._log_detection_result(result)
                    
        except Exception as e:
            print(f"Error processing detections: {e}")
    
    def _log_detection_result(self, result: dict):
        """Log detection result to database"""
        try:
            # Import here to avoid circular imports
            from .db import insert_capture, insert_detection, insert_action
            
            # Save cropped leaf image
            if self.current_frame is not None:
                bbox = result.get('bbox')
                if bbox:
                    x1, y1, x2, y2 = bbox
                    leaf_crop = self.current_frame[y1:y2, x1:x2]
                    
                    # Save image
                    timestamp = int(time.time())
                    image_path = f"data/db/images/auto_leaf_{timestamp}_{result.get('leaf_index', 0)}.jpg"
                    os.makedirs(os.path.dirname(image_path), exist_ok=True)
                    cv2.imwrite(image_path, leaf_crop)
                    
                    # Log to database
                    capture_id = insert_capture(image_path)
                    detection_id = insert_detection(
                        capture_id, 
                        result.get('disease', 'unknown'), 
                        result.get('severity', 0.0), 
                        json.dumps(result)
                    )
                    
                    # Decide action based on severity
                    severity = result.get('severity', 0.0)
                    action, duration_ms = self._decide_action(severity)
                    
                    # Execute action if needed
                    if duration_ms > 0:
                        from .gpio_control import get_sprayer
                        sprayer = get_sprayer()
                        sprayer.spray_for_ms(duration_ms)
                    
                    # Log action
                    insert_action(detection_id, action, duration_ms)
                    
        except Exception as e:
            print(f"Error logging detection result: {e}")
    
    def _decide_action(self, severity: float) -> Tuple[str, int]:
        """Decide action based on disease severity"""
        try:
            low_threshold = current_app.config.get("SEVERITY_LOW_THRESHOLD", 30.0)
            high_threshold = current_app.config.get("SEVERITY_HIGH_THRESHOLD", 70.0)
            spray_duration_low = current_app.config.get("SPRAY_DURATION_LOW_MS", 1000)
            spray_duration_high = current_app.config.get("SPRAY_DURATION_HIGH_MS", 3000)
            
            if severity < low_threshold:
                return "none", 0
            elif severity < high_threshold:
                return "spray_short", spray_duration_low
            else:
                return "spray_long", spray_duration_high
                
        except Exception:
            return "none", 0
    
    def add_click_region(self, click_x: int, click_y: int) -> Optional[Tuple[int, int, int, int]]:
        """Add a new region based on user click (manual mode only)"""
        if self.automatic_mode:
            return None  # Disabled in automatic mode
            
        if self.current_frame is None:
            return None
        
        region = self.selector.create_region_from_click(self.current_frame, click_x, click_y)
        if region:
            self.selected_regions.append(region)
            return region
        return None
    
    def detect_and_classify_leaf(self, region_index: int) -> dict:
        """Detect disease in selected leaf region and return classification result"""
        if self.automatic_mode:
            return {"error": "Manual detection disabled in automatic mode"}
            
        if not self.selected_regions or region_index >= len(self.selected_regions):
            return {"error": "Invalid region index"}
        
        if self.current_frame is None:
            return {"error": "No frame available"}
        
        # Get the selected region
        bbox = self.selected_regions[region_index]
        
        # Crop leaf region
        leaf_crop = self.selector.crop_leaf(self.current_frame, bbox)
        
        # Save cropped image temporarily
        temp_path = f"temp_leaf_{int(time.time())}.jpg"
        cv2.imwrite(temp_path, leaf_crop)
        
        try:
            # Send to disease detection API
            with open(temp_path, 'rb') as f:
                files = {'image': f}
                response = requests.post('http://localhost:5000/api/upload_detect', files=files)
                
                if response.status_code == 200:
                    result = response.json()
                    # Clean up temp file
                    os.remove(temp_path)
                    return result
                else:
                    return {"error": f"API request failed: {response.status_code}"}
        except Exception as e:
            # Clean up temp file
            if os.path.exists(temp_path):
                os.remove(temp_path)
            return {"error": f"Detection failed: {str(e)}"}
    
    def get_automatic_detections(self) -> List[dict]:
        """Get results from automatic detection"""
        if not self.automatic_mode:
            return []
        
        # Return processed results if available
        return getattr(leaf_detection_service, 'last_results', [])


# Global instance
video_service = VideoCaptureService() 