import RPi.GPIO as GPIO
import time
import cv2
from picamera2 import Picamera2
from libcamera import Transform
import subprocess
import threading
import queue
import re


# Disable GPIO warnings for cleaner output
GPIO.setwarnings(False)


# =================================================================
# VOICE CONFIGURATION FOR CRYSTAL CLEAR PRONUNCIATION
# =================================================================


def enhance_text_for_speech(text):
    """
    Advanced text preprocessing for crystal clear pronunciation
    """
    # Step 1: Convert numbers to words for better pronunciation
    number_words = {
        '0': 'zero', '1': 'one', '2': 'two', '3': 'three', '4': 'four',
        '5': 'five', '6': 'six', '7': 'seven', '8': 'eight', '9': 'nine',
        '10': 'ten', '11': 'eleven', '12': 'twelve', '13': 'thirteen',
        '14': 'fourteen', '15': 'fifteen', '16': 'sixteen', '17': 'seventeen',
        '18': 'eighteen', '19': 'nineteen', '20': 'twenty', '30': 'thirty',
        '40': 'forty', '50': 'fifty', '60': 'sixty', '70': 'seventy',
        '80': 'eighty', '90': 'ninety', '100': 'one hundred'
    }
    
    # Replace exact number matches
    for num, word in number_words.items():
        text = re.sub(r'\b' + num + r'\b', word, text)
    
    # Handle two-digit numbers not in dictionary
    def replace_two_digit(match):
        num = int(match.group())
        if num in number_words:
            return number_words[str(num)]
        elif 21 <= num <= 99:
            tens = (num // 10) * 10
            ones = num % 10
            if ones == 0:
                return number_words[str(tens)]
            else:
                return f"{number_words[str(tens)]} {number_words[str(ones)]}"
        return match.group()
    
    text = re.sub(r'\b\d{2}\b', replace_two_digit, text)
    
    # Step 2: Phonetic replacements for crystal clear pronunciation
    phonetic_replacements = {
        # Technical terms
        'centimeters': 'sen-ti-mee-ters',
        'centimeter': 'sen-ti-mee-ter',
        'cm': 'sen-ti-mee-ters',
        'millimeters': 'mil-li-mee-ters',
        'millimeter': 'mil-li-mee-ter',
        'mm': 'mil-li-mee-ters',
        
        # System words
        'obstacle': 'ob-sta-cul',
        'obstacles': 'ob-sta-culs',
        'detection': 'dee-tek-shun',
        'activated': 'ak-ti-vay-ted',
        'enabled': 'en-ay-buld',
        'disabled': 'dis-ay-buld',
        'system': 'sis-tem',
        'warning': 'war-ning',
        'shutting': 'shut-ting',
        
        # Direction and distance words
        'ahead': 'ah-hed',
        'detected': 'dee-tek-ted',
        'very': 'vair-ee',
        'close': 'klohz',
        'distance': 'dis-tans',
        
        # Common mispronunciations
        'EyeKnow': 'Eye-Know',
        'at': 'at',  # Ensure clear pronunciation
        'the': 'thuh',
        'and': 'and'
    }
    
    # Apply phonetic replacements (case insensitive)
    enhanced_text = text
    for word, replacement in phonetic_replacements.items():
        enhanced_text = re.sub(r'\b' + re.escape(word) + r'\b', replacement, enhanced_text, flags=re.IGNORECASE)
    
    # Step 3: Add natural pauses for rhythm and clarity
    enhanced_text = enhanced_text.replace('!', '. ')  # Convert exclamations to periods with pause
    enhanced_text = enhanced_text.replace(',', ' .. ')  # Add pause for commas
    enhanced_text = enhanced_text.replace('.', ' ... ')  # Longer pause for periods
    enhanced_text = enhanced_text.replace('at', ', at,')  # Pause around 'at' for numbers
    
    # Step 4: Ensure proper spacing
    enhanced_text = re.sub(r'\s+', ' ', enhanced_text)  # Remove extra spaces
    enhanced_text = enhanced_text.strip()
    
    return enhanced_text


def speak_with_crystal_clarity(text):
    """
    Use espeak with optimized parameters for crystal clear speech
    """
    try:
        # Enhance the text first
        clear_text = enhance_text_for_speech(text)
        
        print(f"Speaking: {clear_text}")  # Debug output
        
        # Crystal clear espeak parameters:
        # -v en+f4: English female voice variant 4 (clearest)
        # -s 110: Optimal speed for clarity (not too fast, not too slow)
        # -a 200: Maximum amplitude for clear volume
        # -g 15: Longer gaps between words for clarity
        # -p 45: Slightly lower pitch for smoother sound
        # -k 20: Capital letter emphasis
        # --punct: Pronounce punctuation (for pauses)
        
        result = subprocess.run([
            'espeak',
            '-v', 'en+f4',     # Clear female voice
            '-s', '110',       # Optimal speaking speed
            '-a', '200',       # Full volume
            '-g', '15',        # Word gap for clarity
            '-p', '45',        # Smooth pitch
            '-k', '20',        # Capital emphasis
            '--punct=...',     # Pronounce pauses
            clear_text
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            # Fallback to simpler espeak if advanced options fail
            subprocess.run([
                'espeak',
                '-v', 'en+f3',
                '-s', '120',
                '-a', '180',
                clear_text
            ], check=True)
            
    except FileNotFoundError:
        print("espeak not found. Installing espeak is recommended for best voice quality.")
        print("Run: sudo apt install espeak espeak-data")
        # Fallback to basic speech
        speak_basic_fallback(text)
    except Exception as e:
        print(f"Speech error: {e}")
        speak_basic_fallback(text)


def speak_basic_fallback(text):
    """Fallback speech method if espeak fails"""
    try:
        import pyttsx3
        engine = pyttsx3.init()
        
        # Get voices and try to use a female voice
        voices = engine.getProperty('voices')
        if len(voices) > 1:
            engine.setProperty('voice', voices[1].id)
        
        # Optimize for clarity
        engine.setProperty('rate', 100)  # Very slow for maximum clarity
        engine.setProperty('volume', 1.0)
        
        # Use enhanced text
        clear_text = enhance_text_for_speech(text)
        engine.say(clear_text)
        engine.runAndWait()
        
    except Exception as e:
        print(f"Fallback speech failed: {e}")


# Audio queue system for smooth operation
audio_queue = queue.Queue()
audio_thread_running = True


def audio_worker():
    """Background thread for crystal clear audio delivery"""
    while audio_thread_running:
        try:
            text = audio_queue.get(timeout=1)
            if text:
                speak_with_crystal_clarity(text)
            audio_queue.task_done()
        except queue.Empty:
            continue
        except Exception as e:
            print(f"Audio worker error: {e}")


# Start audio worker thread
audio_thread = threading.Thread(target=audio_worker, daemon=True)
audio_thread.start()


def speak_async(text):
    """Add text to speech queue"""
    try:
        audio_queue.put(text, block=False)
    except queue.Full:
        print("Audio queue full - skipping message")


# GPIO Pin Assignments
TRIG = 23
ECHO = 24
LED = 17
VIBRATION1 = 22
VIBRATION2 = 27
SWITCH = 4
TOGGLE_BUTTON = 18


# GPIO Setup
GPIO.setmode(GPIO.BCM)
GPIO.setup(TRIG, GPIO.OUT)
GPIO.setup(ECHO, GPIO.IN)
GPIO.setup(LED, GPIO.OUT)
GPIO.setup(VIBRATION1, GPIO.OUT)
GPIO.setup(VIBRATION2, GPIO.OUT)
GPIO.setup(SWITCH, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(TOGGLE_BUTTON, GPIO.IN, pull_up_down=GPIO.PUD_UP)


def get_distance():
    """Measure distance using ultrasonic sensor"""
    GPIO.output(TRIG, True)
    time.sleep(0.00001)
    GPIO.output(TRIG, False)


    pulse_start = time.time()
    pulse_end = time.time()


    while GPIO.input(ECHO) == 0:
        pulse_start = time.time()
    while GPIO.input(ECHO) == 1:
        pulse_end = time.time()


    pulse_duration = pulse_end - pulse_start
    distance = pulse_duration * 17150
    return round(distance, 2)


# Initialize Pi Camera
picam2 = Picamera2()
config = picam2.create_preview_configuration(
    main={"format": "XRGB8888", "size": (1260, 700)},
    transform=Transform(hflip=1)
)
picam2.configure(config)
picam2.start()


print("EyeKnow system with crystal clear voice starting...")
# Test the enhanced voice
speak_async("EyeKnow system activated")


# System state variables
last_alert_time = 0
last_ultrasonic_check = 0
ultrasonic_check_interval = 0.2
audio_alert_interval = 5.0
obstacle_detection_enabled = True
last_button_press = 0
button_debounce = 0.5


def format_distance_speech(distance):
    """Format distance announcements for maximum clarity"""
    distance_int = int(distance)
    
    if distance <= 10:
        return f"Warning! Very close obstacle at {distance_int} centimeters"
    elif distance <= 30:
        return f"Close obstacle detected at {distance_int} centimeters"
    else:
        return f"Obstacle ahead at {distance_int} centimeters"


try:
    while True:
        frame = picam2.capture_array()
        current_time = time.time()
        
        # Toggle button handling
        if GPIO.input(TOGGLE_BUTTON) == GPIO.LOW:
            if current_time - last_button_press > button_debounce:
                obstacle_detection_enabled = not obstacle_detection_enabled
                last_button_press = current_time
                
                if obstacle_detection_enabled:
                    speak_async("Obstacle detection enabled")
                    print("Obstacle detection: ENABLED")
                else:
                    speak_async("Obstacle detection disabled")
                    print("Obstacle detection: DISABLED")
                    GPIO.output(LED, GPIO.LOW)
                    GPIO.output(VIBRATION1, GPIO.LOW)
                    GPIO.output(VIBRATION2, GPIO.LOW)
        
        # Continuous obstacle detection
        if obstacle_detection_enabled:
            if current_time - last_ultrasonic_check >= ultrasonic_check_interval:
                distance = get_distance()
                last_ultrasonic_check = current_time
                
                if distance > 100:
                    print("MAX REACH: 100cm - No obstacles detected")
                    GPIO.output(LED, GPIO.LOW)
                    GPIO.output(VIBRATION1, GPIO.LOW)
                    GPIO.output(VIBRATION2, GPIO.LOW)
                elif distance <= 50:
                    print(f"Distance: {distance} cm — ALERT")
                    GPIO.output(LED, GPIO.HIGH)
                    GPIO.output(VIBRATION1, GPIO.HIGH)
                    GPIO.output(VIBRATION2, GPIO.HIGH)
                    
                    # Crystal clear audio alert every 5 seconds
                    if current_time - last_alert_time >= audio_alert_interval:
                        speech_text = format_distance_speech(distance)
                        speak_async(speech_text)
                        last_alert_time = current_time
                        
                else:
                    print(f"Distance: {distance} cm - Safe")
                    GPIO.output(LED, GPIO.LOW)
                    GPIO.output(VIBRATION1, GPIO.LOW)
                    GPIO.output(VIBRATION2, GPIO.LOW)
        else:
            GPIO.output(LED, GPIO.LOW)
            GPIO.output(VIBRATION1, GPIO.LOW)
            GPIO.output(VIBRATION2, GPIO.LOW)


        time.sleep(0.05)


except KeyboardInterrupt:
    print("\nProgram stopped by user.")
    speak_async("EyeKnow system shutting down")
    time.sleep(3)
    audio_thread_running = False


finally:
    picam2.stop()
    GPIO.cleanup()
    print("System cleanup completed.")
