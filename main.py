import RPi.GPIO as GPIO
import time
import subprocess
import cv2
from picamera2 import Picamera2
from ultralytics import YOLO


# Disable GPIO warnings
GPIO.setwarnings(False)


# GPIO Pin Setup - BUTTON ONLY FOR OBJECT DETECTION/CAMERA
TRIG = 23          # Ultrasonic trigger pin
ECHO = 24          # Ultrasonic echo pin
LED = 17           # Status LED indicator
VIBRATION1 = 22    # Left vibration motor
VIBRATION2 = 27    # Right vibration motor
OBJECT_BUTTON = 18 # Button ONLY for object detection (camera functions)


# Configure GPIO pins
GPIO.setmode(GPIO.BCM)
GPIO.setup(TRIG, GPIO.OUT)
GPIO.setup(ECHO, GPIO.IN)
GPIO.setup(LED, GPIO.OUT)
GPIO.setup(VIBRATION1, GPIO.OUT)
GPIO.setup(VIBRATION2, GPIO.OUT)
GPIO.setup(OBJECT_BUTTON, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)


# Initialize camera
picam2 = Picamera2()
config = picam2.create_preview_configuration(main={"format": "XRGB8888", "size": (640, 480)})
picam2.configure(config)
picam2.start()


# Initialize YOLO model
print("Loading YOLO model...")
model = YOLO('yolov8n.pt')  # Downloads automatically on first run
print("YOLO model loaded successfully!")


# System variables - SIMPLIFIED
last_speech_time = 0

# Button control variables - IMMEDIATE EXECUTION
last_button_state = GPIO.LOW
button_debounce = 0.3  # 300ms debounce


def speak(text):
    """Simple text-to-speech function"""
    try:
        subprocess.run(['espeak', text], check=True)
    except:
        print(f"Speech: {text}")  # Fallback if espeak not available


def get_distance():
    """Measure distance using ultrasonic sensor"""
    try:
        # Send trigger pulse
        GPIO.output(TRIG, True)
        time.sleep(0.00001)
        GPIO.output(TRIG, False)
        
        # Measure echo time
        pulse_start = time.time()
        pulse_end = time.time()
        
        # Wait for echo start
        timeout = time.time() + 0.5  # 0.5 second timeout
        while GPIO.input(ECHO) == 0 and time.time() < timeout:
            pulse_start = time.time()
        
        # Wait for echo end
        timeout = time.time() + 0.5  # 0.5 second timeout
        while GPIO.input(ECHO) == 1 and time.time() < timeout:
            pulse_end = time.time()
        
        # Calculate distance
        pulse_duration = pulse_end - pulse_start
        distance = pulse_duration * 17150  # Convert to cm
        return round(distance, 2)
    except:
        return 999  # Return max distance if error


def detect_obstacles_position(frame):
    """Detect obstacles and their positions using YOLO"""
    # Run YOLO detection with lower confidence for better detection
    results = model(frame, conf=0.25, verbose=False)
    
    frame_width = frame.shape[1]
    left_boundary = frame_width // 3
    right_boundary = 2 * frame_width // 3
    
    detected_positions = []
    
    for result in results:
        if result.boxes is not None:
            for box in result.boxes:
                # Get bounding box coordinates
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)
                
                # Calculate center of detected object
                object_center_x = (x1 + x2) // 2
                
                # Determine position
                if object_center_x < left_boundary:
                    position = "left"
                elif object_center_x > right_boundary:
                    position = "right"
                else:
                    position = "front"
                
                # Get object class name
                class_id = int(box.cls[0])
                class_name = model.names[class_id]
                confidence = float(box.conf[0])
                
                detected_positions.append({
                    'position': position,
                    'class': class_name,
                    'confidence': confidence,
                    'center_x': object_center_x
                })
    
    return detected_positions


def detect_objects_for_identification(frame):
    """Detect objects for identification mode - SINGLE CAPTURE"""
    results = model(frame, conf=0.3, verbose=False)
    
    detected_objects = []
    
    for result in results:
        if result.boxes is not None:
            for box in result.boxes:
                # Get object class name
                class_id = int(box.cls[0])
                class_name = model.names[class_id]
                confidence = float(box.conf[0])
                
                detected_objects.append({
                    'class': class_name,
                    'confidence': confidence
                })
    
    return detected_objects


def set_positional_alerts(vibration_on, position, led_on=False):
    """Control positional vibration alerts and LED based on obstacle position"""
    if vibration_on and position:
        # LED indication for obstacle detected
        GPIO.output(LED, GPIO.HIGH if led_on else GPIO.LOW)
        
        if position == "left":
            GPIO.output(VIBRATION1, GPIO.HIGH)
            GPIO.output(VIBRATION2, GPIO.LOW)
        elif position == "right":
            GPIO.output(VIBRATION1, GPIO.LOW)
            GPIO.output(VIBRATION2, GPIO.HIGH)
        elif position == "front":
            GPIO.output(VIBRATION1, GPIO.HIGH)
            GPIO.output(VIBRATION2, GPIO.HIGH)
        else:
            GPIO.output(VIBRATION1, GPIO.LOW)
            GPIO.output(VIBRATION2, GPIO.LOW)
    else:
        GPIO.output(LED, GPIO.LOW)
        GPIO.output(VIBRATION1, GPIO.LOW)
        GPIO.output(VIBRATION2, GPIO.LOW)


def get_warning_message(distance, positions):
    """Get appropriate warning message based on distance and positions"""
    if distance <= 100:
        distance_level = "Very close obstacle"
    elif distance <= 200:
        distance_level = "Close obstacle"
    elif distance <= 300:
        distance_level = "Far obstacle"
    else:
        return None, None
    
    # Get primary position
    if not positions:
        # If no camera detection, use front as default
        return f"{distance_level} at front", "front"
    
    # Use first detected position
    main_position = positions[0]['position']
    return f"{distance_level} at {main_position}", main_position


def get_primary_position(positions):
    """Get the primary position from detected objects"""
    if not positions:
        return None
    
    # Count positions
    left_count = sum(1 for pos in positions if pos['position'] == 'left')
    front_count = sum(1 for pos in positions if pos['position'] == 'front')
    right_count = sum(1 for pos in positions if pos['position'] == 'right')
    
    # Return the side with most detections (front takes priority if tied)
    if front_count >= left_count and front_count >= right_count:
        return 'front'
    elif left_count > right_count:
        return 'left'
    else:
        return 'right'


def execute_object_detection_immediately(frame):
    """IMMEDIATE object detection execution when button is pressed"""
    print("🔍 BUTTON PRESSED! Executing object detection...")
    
    # Turn off all obstacle alerts immediately
    set_positional_alerts(False, None)
    
    # LED blink pattern for object detection
    speak("Object detection mode")
    for i in range(3):
        GPIO.output(LED, GPIO.HIGH)
        time.sleep(0.1)
        GPIO.output(LED, GPIO.LOW)
        time.sleep(0.1)
    
    # Detect objects
    detected_objects = detect_objects_for_identification(frame)
    
    if detected_objects:
        # Get unique objects with highest confidence
        unique_objects = {}
        for obj in detected_objects:
            class_name = obj['class']
            if class_name not in unique_objects or obj['confidence'] > unique_objects[class_name]['confidence']:
                unique_objects[class_name] = obj
        
        # Announce detected objects
        for class_name, obj in unique_objects.items():
            message = f"Detected {class_name}"
            speak(message)
            print(f"✅ Object detected: {message} (confidence: {obj['confidence']:.2f})")
            time.sleep(0.5)  # Brief pause between announcements
        
        # Summary if multiple objects
        if len(unique_objects) > 1:
            speak(f"Total {len(unique_objects)} objects detected")
    else:
        # NO OBJECTS DETECTED
        speak("No objects detected")
        print("❌ No objects detected in frame")
    
    # Signal processing complete
    speak("Returning to obstacle detection")
    print("🔙 Object detection complete, returning to obstacle mode")


print("EyeKnow system starting...")
print("OBJECT_BUTTON (pin 18) = Object detection trigger")
print("  - DEFAULT: Obstacle detection mode (continuous)")  
print("  - BUTTON PRESS: Immediate object detection, then back to obstacle mode")
print("Ultrasonic sensor (pins 23/24) = Distance measurement")
print("VIBRATION1 (pin 22) = LEFT motor")
print("VIBRATION2 (pin 27) = RIGHT motor")
print("LED (pin 17) = Status indicator")

# Initial status announcement
speak("EyeKnow system activated. Obstacle detection mode active")
print("🚧 SYSTEM READY: OBSTACLE MODE active")


try:
    while True:
        current_time = time.time()
        
        # Get camera frame
        frame = picam2.capture_array()
        frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        
        # BUTTON DETECTION - IMMEDIATE EXECUTION
        current_button_state = GPIO.input(OBJECT_BUTTON)
        
        # Detect button press (rising edge) and EXECUTE IMMEDIATELY
        if current_button_state == GPIO.HIGH and last_button_state == GPIO.LOW:
            time.sleep(button_debounce)  # Debounce delay
            
            # Check if button is still pressed after debounce
            if GPIO.input(OBJECT_BUTTON) == GPIO.HIGH:
                # EXECUTE OBJECT DETECTION IMMEDIATELY
                execute_object_detection_immediately(frame_bgr)
                
                # Wait for button release to prevent multiple triggers
                print("Waiting for button release...")
                while GPIO.input(OBJECT_BUTTON) == GPIO.HIGH:
                    time.sleep(0.1)
                print("Button released - Ready for next press")
        
        last_button_state = current_button_state
        
        # OBSTACLE DETECTION MODE (Default) - CONTINUOUS
        print("🚧 OBSTACLE MODE: Checking for obstacles...", end='\r')
        
        # Get distance from ultrasonic sensor
        distance = get_distance()
        
        # Detect objects and their positions for obstacle avoidance
        detected_positions = detect_obstacles_position(frame_bgr)
        
        if distance >= 301:
            # Safe distance - no alerts
            print(f"Distance: {distance} cm - Safe", end='\r')
            set_positional_alerts(False, None)
        else:
            # Obstacle detected - get warning message and position
            warning_result = get_warning_message(distance, detected_positions)
            if warning_result:
                warning_message, obstacle_position = warning_result
            else:
                warning_message, obstacle_position = None, None
            
            # Console output with position info
            position_info = ""
            if detected_positions:
                primary_pos = get_primary_position(detected_positions)
                position_info = f" (Camera: {primary_pos})"
            
            if distance <= 100:
                print(f"Distance: {distance} cm - VERY CLOSE WARNING{position_info}")
                set_positional_alerts(True, obstacle_position, led_on=True)
            elif distance <= 200:
                print(f"Distance: {distance} cm - CLOSE WARNING{position_info}")
                set_positional_alerts(True, obstacle_position, led_on=True)
            else:  # 201-300
                print(f"Distance: {distance} cm - FAR WARNING{position_info}")
                set_positional_alerts(True, obstacle_position, led_on=False)
            
            # Speak warning every 5 seconds
            if current_time - last_speech_time >= 5.0:
                if warning_message:
                    speak(warning_message)
                    last_speech_time = current_time
        
        time.sleep(0.1)  # Responsive loop


except KeyboardInterrupt:
    print("\nStopping system...")
    speak("EyeKnow system shutting down")


finally:
    # Cleanup
    picam2.stop()
    GPIO.cleanup()
    print("System stopped.")
