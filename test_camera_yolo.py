from ultralytics import YOLO
from picamera2 import Picamera2
import cv2
import time

# Initialize camera
picam2 = Picamera2()
config = picam2.create_preview_configuration(main={"size": (640, 480)})
picam2.configure(config)
picam2.start()

# Load YOLOv8 model
print("Loading YOLOv8 model...")
model = YOLO('yolov8n.pt')  # This will download the model automatically
print("Model loaded successfully!")

try:
    for i in range(10):  # Test 10 frames
        # Capture frame
        frame = picam2.capture_array()
        
        # Run detection
        results = model(frame, conf=0.5)
        
        # Print detections
        for result in results:
            boxes = result.boxes
            if boxes is not None:
                for box in boxes:
                    class_id = int(box.cls[0])
                    confidence = float(box.conf[0])
                    class_name = model.names[class_id]
                    print(f"Detected: {class_name} ({confidence:.2f})")
        
        time.sleep(1)
        print(f"Frame {i+1}/10 processed")

except KeyboardInterrupt:
    print("Test stopped by user")

finally:
    picam2.stop()
    print("Camera test complete!")
