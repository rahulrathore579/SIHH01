# MobileNet-SSD Model for Leaf Detection

This directory contains the MobileNet-SSD model files for automatic leaf detection.

## Files Required

1. **MobileNetSSD_deploy.prototxt** - Model architecture definition (already included)
2. **MobileNetSSD_deploy.caffemodel** - Pre-trained model weights (you need to download this)

## Getting the Model Weights

### Option 1: Download Pre-trained Model
```bash
# Download the pre-trained MobileNet-SSD model
wget https://github.com/chuanqi305/MobileNet-SSD/raw/master/deploy.caffemodel -O MobileNetSSD_deploy.caffemodel
```

### Option 2: Use OpenCV's Built-in Model
The system will automatically fall back to OpenCV's built-in MobileNet-SSD if the custom model is not available.

### Option 3: Train Custom Model
For better leaf detection accuracy, you can train a custom model on your specific leaf dataset.

## Model Configuration

The current configuration is set up for:
- **Input size**: 300x300 pixels
- **Classes**: 2 (background, leaf)
- **Confidence threshold**: 0.25
- **NMS threshold**: 0.45

## Performance Notes

- **Raspberry Pi**: The model runs at ~2-5 FPS depending on Pi model
- **Detection interval**: Set to 3 seconds to balance accuracy and performance
- **Fallback**: If MobileNet-SSD fails, the system uses contour-based detection

## Customization

To customize the model for your specific use case:
1. Modify the prototxt file for different input sizes
2. Adjust confidence thresholds in the code
3. Change detection intervals for different performance requirements 