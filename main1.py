import RPi.GPIO as GPIO
import time
import subprocess
import cv2
from picamera2 import Picamera2
from ultralytics import YOLO

# Disable GPIO warnings
GPIO.setwarnings(False)

# GPIO Pin Setup
TRIG = 23          # Ultrasonic trigger pin
ECHO = 24          # Ultrasonic echo pin
VIBRATION1 = 22    # Left vibration motor
VIBRATION2 = 27    # Right vibration motor
TOGGLE_BUTTON = 18 # Enable/disable button

# Configure GPIO pins
GPIO.setmode(GPIO.BCM)
GPIO.setup(TRIG, GPIO.OUT)
GPIO.setup(ECHO, GPIO.IN)
GPIO.setup(VIBRATION1, GPIO.OUT)
GPIO.setup(VIBRATION2, GPIO.OUT)
GPIO.setup(TOGGLE_BUTTON, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# Initialize camera
picam2 = Picamera2()
config = picam2.create_preview_configuration(main={"format": "XRGB8888", "size": (640, 480)})
picam2.configure(config)
picam2.start()

# Initialize YOLO model
print("Loading YOLO model...")
model = YOLO('yolov8n.pt')  # Downloads automatically on first run
print("YOLO model loaded successfully!")

# System variables
detection_enabled = True
last_speech_time = 0
last_button_time = 0

def speak(text):
    """Simple text-to-speech function"""
    try:
        subprocess.run(['espeak', text], check=True)
    except:
        print(f"Speech: {text}")  # Fallback if espeak not available

def get_distance():
    """Measure distance using ultrasonic sensor"""
    # Send trigger pulse
    GPIO.output(TRIG, True)
    time.sleep(0.00001)
    GPIO.output(TRIG, False)
    
    # Measure echo time
    while GPIO.input(ECHO) == 0:
        pulse_start = time.time()
    while GPIO.input(ECHO) == 1:
        pulse_end = time.time()
    
    # Calculate distance
    pulse_duration = pulse_end - pulse_start
    distance = pulse_duration * 17150  # Convert to cm
    return round(distance, 2)

def detect_obstacles_position(frame):
    """Detect obstacles and their positions using YOLO"""
    # Run YOLO detection with lower confidence for better detection
    results = model(frame, conf=0.25, verbose=False)  # Lowered from 0.5 to 0.25
    
    frame_width = frame.shape[1]
    left_boundary = frame_width // 3      # Left third
    right_boundary = 2 * frame_width // 3  # Right third starts here
    
    detected_positions = []
    
    print(f"Camera frame size: {frame.shape}")  # Debug frame info
    print(f"Position boundaries - Left: 0-{left_boundary}, Front: {left_boundary}-{right_boundary}, Right: {right_boundary}-{frame_width}")
    
    for result in results:
        if result.boxes is not None:
            print(f"YOLO detected {len(result.boxes)} objects")  # Debug detection count
            for box in result.boxes:
                # Get bounding box coordinates
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)
                
                # Calculate center of detected object
                object_center_x = (x1 + x2) // 2
                
                # Determine position (left, front, or right) with detailed debugging
                if object_center_x < left_boundary:
                    position = "left"
                    print(f"Object center {object_center_x} < {left_boundary} = LEFT")
                elif object_center_x > right_boundary:
                    position = "right"
                    print(f"Object center {object_center_x} > {right_boundary} = RIGHT")
                else:
                    position = "front"
                    print(f"Object center {object_center_x} between {left_boundary}-{right_boundary} = FRONT")
                
                # Get object class name
                class_id = int(box.cls[0])
                class_name = model.names[class_id]
                confidence = float(box.conf[0])
                
                print(f"Detected: {class_name} at {position} (confidence: {confidence:.2f}, center_x: {object_center_x})")  # Debug each detection
                
                detected_positions.append({
                    'position': position,
                    'class': class_name,
                    'confidence': confidence,
                    'center_x': object_center_x
                })
        else:
            print("No objects detected by YOLO")  # Debug when nothing detected
    
    return detected_positions

def set_positional_alerts(vibration_on, position):
    """Control positional vibration alerts based on obstacle position"""
    
    print(f"Setting alerts: vibration_on={vibration_on}, position={position}")  # Debug
    
    if vibration_on and position:
        # Turn on appropriate vibration motor(s) based on position
        if position == "left":
            GPIO.output(VIBRATION1, GPIO.HIGH)  # Left motor on
            GPIO.output(VIBRATION2, GPIO.LOW)   # Right motor off
            print(f"Haptic: LEFT motor vibrating (position: {position})")
        elif position == "right":
            GPIO.output(VIBRATION1, GPIO.LOW)   # Left motor off
            GPIO.output(VIBRATION2, GPIO.HIGH)  # Right motor on
            print(f"Haptic: RIGHT motor vibrating (position: {position})")
        elif position == "front":
            GPIO.output(VIBRATION1, GPIO.HIGH)  # Both motors on
            GPIO.output(VIBRATION2, GPIO.HIGH)  # Both motors on
            print(f"Haptic: BOTH motors vibrating (position: {position})")
        else:
            # If position is unknown, turn off both motors
            GPIO.output(VIBRATION1, GPIO.LOW)
            GPIO.output(VIBRATION2, GPIO.LOW)
            print(f"Haptic: No vibration (unknown position: {position})")
    else:
        # Turn off both vibration motors
        GPIO.output(VIBRATION1, GPIO.LOW)
        GPIO.output(VIBRATION2, GPIO.LOW)
        if not vibration_on:
            print("Haptic: All vibrations OFF")
        else:
            print("Haptic: No position provided, vibrations OFF")

def get_warning_message(distance, positions):
    """Get appropriate warning message based on distance and positions"""
    # Determine distance level
    if distance <= 100:
        distance_level = "Very close obstacle"
    elif distance <= 200:
        distance_level = "Close obstacle"
    elif distance <= 300:
        distance_level = "Far obstacle"
    else:
        return None  # No warning needed
    
    # If no camera detections, cycle through test positions for debugging
    if not positions:
        import time
        # Cycle through positions every 6 seconds for testing
        cycle_time = int(time.time() // 6) % 3
        test_positions = ['left', 'front', 'right']
        test_position = test_positions[cycle_time]
        print(f"No YOLO detection - using test position: {test_position} (cycle: {cycle_time})")
        return f"{distance_level} at {test_position}", test_position
    
    # Find the most prominent position (closest to center or highest confidence)
    main_position = positions[0]['position']  # Take first detection
    print(f"Using camera detected position: {main_position}")
    
    # Create message with position
    return f"{distance_level} at {main_position}", main_position

def get_primary_position(positions):
    """Get the primary position from detected objects"""
    if not positions:
        return None
    
    # Count left vs front vs right detections
    left_count = sum(1 for pos in positions if pos['position'] == 'left')
    front_count = sum(1 for pos in positions if pos['position'] == 'front')
    right_count = sum(1 for pos in positions if pos['position'] == 'right')
    
    print(f"Position counts - Left: {left_count}, Front: {front_count}, Right: {right_count}")
    
    # Return the side with most detections (front takes priority if tied)
    if front_count >= left_count and front_count >= right_count:
        return 'front'
    elif left_count > right_count:
        return 'left'
    else:
        return 'right'

print("EyeKnow system starting with 3-zone positional haptic feedback...")
print("VIBRATION1 (pin 22) = LEFT motor")
print("VIBRATION2 (pin 27) = RIGHT motor")
print("Position zones: LEFT | FRONT (both motors) | RIGHT")
print("Test mode: If no YOLO detection, cycles through LEFT->FRONT->RIGHT every 6 seconds")
speak("EyeKnow system activated")

try:
    while True:
        current_time = time.time()
        
        # Check toggle button (with debounce)
        if GPIO.input(TOGGLE_BUTTON) == GPIO.LOW:
            if current_time - last_button_time > 0.5:  # 0.5 second debounce
                detection_enabled = not detection_enabled
                last_button_time = current_time
                
                if detection_enabled:
                    speak("Detection enabled")
                    print("Detection: ENABLED")
                else:
                    speak("Detection disabled")
                    print("Detection: DISABLED")
                    set_positional_alerts(False, None)  # Turn off all alerts
        
        # Obstacle detection (only if enabled)
        if detection_enabled:
            # Get distance from ultrasonic sensor
            distance = get_distance()
            
            # Get camera frame and detect objects
            frame = picam2.capture_array()
            frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            detected_positions = detect_obstacles_position(frame_bgr)
            
            if distance >= 301:
                # Safe distance - no alerts
                print(f"Distance: {distance} cm - Safe")
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
                elif distance <= 200:
                    print(f"Distance: {distance} cm - CLOSE WARNING{position_info}")
                else:  # 201-300
                    print(f"Distance: {distance} cm - FAR WARNING{position_info}")
                
                # Activate positional alerts
                set_positional_alerts(True, obstacle_position)
                
                # Speak warning every 5 seconds
                if current_time - last_speech_time >= 5.0:
                    if warning_message:
                        speak(warning_message)
                        last_speech_time = current_time
        
        else:
            # Detection disabled - no alerts
            set_positional_alerts(False, None)
        
        time.sleep(0.2)  # Slightly longer delay for camera processing

except KeyboardInterrupt:
    print("\nStopping system...")
    speak("EyeKnow system shutting down")

finally:
    # Cleanup
    picam2.stop()
    GPIO.cleanup()
    print("System stopped.")
