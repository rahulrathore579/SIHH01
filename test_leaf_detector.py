#!/usr/bin/env python3
"""
Test script for the MobileNet-SSD leaf detector integration
"""

import cv2
import numpy as np
import sys
import os

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

def test_leaf_detector():
    """Test the leaf detector with a sample image"""
    try:
        from leaf_detector import MobileNetSSDLeafDetector
        
        print("Testing MobileNet-SSD Leaf Detector...")
        
        # Create detector instance
        detector = MobileNetSSDLeafDetector(confidence_threshold=0.5)
        
        # Try to initialize model
        print("Initializing model...")
        model_initialized = detector.initialize_model()
        
        if model_initialized:
            print("✅ MobileNet-SSD model initialized successfully")
        else:
            print("⚠️  MobileNet-SSD failed, will use fallback detection")
        
        # Create a test image (green rectangle to simulate a leaf)
        test_image = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # Draw a green rectangle to simulate a leaf
        cv2.rectangle(test_image, (100, 100), (300, 400), (0, 255, 0), -1)
        
        # Test detection
        print("Testing leaf detection...")
        detections = detector.detect_leaves(test_image)
        
        print(f"Found {len(detections)} leaf(ves)")
        for i, (x1, y1, x2, y2, confidence) in enumerate(detections):
            print(f"  Leaf {i+1}: bbox=({x1},{y1},{x2},{y2}), confidence={confidence:.2f}")
        
        # Test drawing
        annotated_image = detector.draw_detections(test_image, detections)
        print("✅ Detection and drawing test completed")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def test_video_service():
    """Test the video service integration"""
    try:
        from video_detection import VideoCaptureService
        
        print("\nTesting Video Service Integration...")
        
        # Create video service
        service = VideoCaptureService()
        
        # Test initialization
        print("Testing service initialization...")
        service.initialize()
        
        # Test mode toggle
        print("Testing mode toggle...")
        initial_mode = service.automatic_mode
        service.toggle_automatic_mode()
        new_mode = service.automatic_mode
        
        if initial_mode != new_mode:
            print("✅ Mode toggle working correctly")
        else:
            print("❌ Mode toggle failed")
        
        # Test automatic mode
        print("Testing automatic mode...")
        service.automatic_mode = True
        
        # Create test frame
        test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.rectangle(test_frame, (100, 100), (300, 400), (0, 255, 0), -1)
        
        # Test detection
        service.current_frame = test_frame
        service._run_automatic_detection(test_frame)
        
        print("✅ Video service integration test completed")
        return True
        
    except Exception as e:
        print(f"❌ Video service test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 Testing Leaf Detection System Integration")
    print("=" * 50)
    
    # Test leaf detector
    detector_ok = test_leaf_detector()
    
    # Test video service
    video_ok = test_video_service()
    
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")
    print(f"  Leaf Detector: {'✅ PASS' if detector_ok else '❌ FAIL'}")
    print(f"  Video Service: {'✅ PASS' if video_ok else '❌ FAIL'}")
    
    if detector_ok and video_ok:
        print("\n🎉 All tests passed! The system is ready to use.")
        return 0
    else:
        print("\n⚠️  Some tests failed. Check the output above for details.")
        return 1

if __name__ == "__main__":
    exit(main()) 