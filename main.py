import argparse
import os
import sys
import time

# Prevent optional TensorFlow docgen conflict with protobuf on certain Python installs
if "tensorflow" not in sys.modules:
    sys.modules["tensorflow"] = None

import cv2
import numpy as np
from scipy.spatial import distance

try:
    import serial
    import serial.tools.list_ports
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False

try:
    import mediapipe as mp
    from mediapipe.tasks import python
    from mediapipe.tasks.python import vision
    MEDIAPIPE_AVAILABLE = True
except Exception as e:
    MEDIAPIPE_AVAILABLE = False
    print(f"Notice: MediaPipe import note: {e}")


def find_available_ports():
    if not SERIAL_AVAILABLE:
        return []
    try:
        return [port.device for port in serial.tools.list_ports.comports()]
    except Exception:
        return []


def open_serial_port(port_name, label):
    if not SERIAL_AVAILABLE or not port_name:
        return None
    try:
        port = serial.Serial(port_name, 9600, timeout=1)
        print(f"[{label}] Connected on {port_name}")
        time.sleep(1)
        return port
    except Exception as exc:
        print(f"[{label}] Could not open {port_name}: {exc} (using simulation)")
        return None


# MediaPipe Face Landmark indices for left and right eyes (478 mesh)
LEFT_EYE_LANDMARKS = [33, 160, 158, 133, 153, 144]
RIGHT_EYE_LANDMARKS = [362, 385, 387, 263, 373, 380]


def calculate_ear(eye_points, landmarks, width, height):
    """
    Computes Eye Aspect Ratio (EAR):
        EAR = (|p2 - p6| + |p3 - p5|) / (2 * |p1 - p4|)
    """
    points = []
    for idx in eye_points:
        px = int(landmarks[idx].x * width)
        py = int(landmarks[idx].y * height)
        points.append((px, py))

    vertical_1 = distance.euclidean(points[1], points[5])
    vertical_2 = distance.euclidean(points[2], points[4])
    horizontal = distance.euclidean(points[0], points[3])

    if horizontal == 0:
        return 0.0, points

    ear = (vertical_1 + vertical_2) / (2.0 * horizontal)
    return ear, points


def draw_hud(frame, ear, threshold, closed_seconds, min_interval, max_interval,
             arduino_triggered, esp_triggered, hardware_status):
    """
    Renders status HUD, timer, and interval progress bar on the video frame.
    """
    h, w, _ = frame.shape
    overlay = frame.copy()

    # Top status bar background
    cv2.rectangle(overlay, (0, 0), (w, 100), (20, 20, 20), -1)

    # Determine alert level
    if closed_seconds >= max_interval:
        status_text = f"CRITICAL ALERT: SLEEP > {max_interval:.1f}s!"
        status_color = (0, 0, 255)  # Red
        alert_bg = (0, 0, 180)
    elif closed_seconds >= min_interval:
        status_text = f"DROWSINESS WARNING ({min_interval:.1f}s - {max_interval:.1f}s Interval)"
        status_color = (0, 165, 255)  # Orange
        alert_bg = (0, 120, 200)
    elif closed_seconds > 0.3:
        status_text = f"EYES CLOSED ({closed_seconds:.1f}s)"
        status_color = (0, 255, 255)  # Yellow
        alert_bg = None
    else:
        status_text = "DRIVER AWAKE & ALERT"
        status_color = (0, 255, 0)  # Green
        alert_bg = None

    if alert_bg and (int(time.time() * 4) % 2 == 0):
        # Flashing alert banner
        cv2.rectangle(overlay, (0, 0), (w, 100), alert_bg, -1)

    cv2.addWeighted(overlay, 0.75, frame, 0.25, 0, frame)

    # Title & State
    cv2.putText(frame, status_text, (20, 38), cv2.FONT_HERSHEY_DUPLEX, 0.85, status_color, 2)

    # EAR and Hardware info
    ear_str = f"EAR: {ear:.2f}" if ear is not None else "EAR: N/A"
    cv2.putText(frame, f"{ear_str} (Threshold: {threshold:.2f})", (20, 75),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (220, 220, 220), 1)

    # Hardware status
    hw_text = f"Arduino: {hardware_status['arduino']} | ESP32: {hardware_status['esp32']}"
    cv2.putText(frame, hw_text, (w - 420, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (180, 180, 180), 1)

    # Interval Progress Bar at the bottom
    bar_x = 30
    bar_y = h - 45
    bar_w = w - 60
    bar_h = 22

    # Background bar
    cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h), (50, 50, 50), -1)

    # Fill ratio up to max_interval
    fill_ratio = min(closed_seconds / max(max_interval, 0.1), 1.0)
    fill_w = int(bar_w * fill_ratio)

    if closed_seconds >= max_interval:
        fill_color = (0, 0, 255)  # Red
    elif closed_seconds >= min_interval:
        fill_color = (0, 165, 255)  # Orange
    else:
        fill_color = (0, 255, 0)  # Green

    if fill_w > 0:
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + fill_w, bar_y + bar_h), fill_color, -1)

    # Marker for 3s (min_interval)
    min_marker_x = bar_x + int(bar_w * (min_interval / max_interval))
    cv2.line(frame, (min_marker_x, bar_y - 4), (min_marker_x, bar_y + bar_h + 4), (255, 255, 255), 2)

    # Labels below bar
    cv2.putText(frame, f"0s", (bar_x, bar_y - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1)
    cv2.putText(frame, f"Stage 1 ({min_interval:.1f}s)", (min_marker_x - 45, bar_y - 8),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 200, 255), 1)
    cv2.putText(frame, f"Stage 2 ({max_interval:.1f}s)", (bar_x + bar_w - 90, bar_y - 8),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 100, 255), 1)

    # Timer string inside/near bar
    timer_str = f"Closed: {closed_seconds:.2f}s"
    cv2.putText(frame, timer_str, (bar_x + 10, bar_y + 16), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)
    cv2.putText(frame, timer_str, (bar_x + 10, bar_y + 16), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)


def parse_args():
    parser = argparse.ArgumentParser(description="Driver Sleep Detection with 3 to 5 Second Intervals")
    parser.add_argument("--arduino-port", default=os.getenv("ARDUINO_PORT", "COM3"), help="Serial port for Arduino Uno")
    parser.add_argument("--esp32-port", default=os.getenv("ESP32_PORT", "COM6"), help="Serial port for ESP32")
    parser.add_argument("--skip-serial", action="store_true", help="Force software simulation without serial devices")
    parser.add_argument("--demo", action="store_true", help="Run simulated test mode without webcam")
    parser.add_argument("--threshold", type=float, default=0.23, help="Eye Aspect Ratio (EAR) closure threshold (default: 0.23)")
    parser.add_argument("--min-interval", type=float, default=3.0, help="Initial alert threshold in seconds (default: 3.0)")
    parser.add_argument("--max-interval", type=float, default=5.0, help="Critical alert threshold in seconds (default: 5.0)")
    return parser.parse_args()


def main():
    args = parse_args()
    print("=" * 60)
    print(" Driver Sleep Detection System")
    print(f" - Warning Interval Threshold:  {args.min_interval:.1f}s (Stage 1 -> Arduino)")
    print(f" - Critical Interval Threshold: {args.max_interval:.1f}s (Stage 2 -> ESP32)")
    print(f" - EAR Threshold:               {args.threshold:.2f}")
    print("=" * 60)

    # Initialize Hardware Serial Connections
    available_ports = find_available_ports()
    arduino = None
    esp32 = None

    if not args.skip_serial:
        if args.arduino_port in available_ports:
            arduino = open_serial_port(args.arduino_port, "Arduino")
        if args.esp32_port in available_ports:
            esp32 = open_serial_port(args.esp32_port, "ESP32")

    hw_status = {
        "arduino": f"Connected ({args.arduino_port})" if arduino else "Simulated",
        "esp32": f"Connected ({args.esp32_port})" if esp32 else "Simulated"
    }
    print(f"Hardware Status: Arduino -> {hw_status['arduino']}, ESP32 -> {hw_status['esp32']}")

    # Setup MediaPipe FaceLandmarker
    landmarker = None
    if MEDIAPIPE_AVAILABLE:
        model_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "face_landmarker.task")
        if os.path.exists(model_path):
            try:
                base_options = python.BaseOptions(model_asset_path=model_path)
                options = vision.FaceLandmarkerOptions(
                    base_options=base_options,
                    running_mode=vision.RunningMode.VIDEO,
                    num_faces=1
                )
                landmarker = vision.FaceLandmarker.create_from_options(options)
                print(f"Loaded MediaPipe FaceLandmarker ({model_path})")
            except Exception as e:
                print(f"Could not initialize MediaPipe FaceLandmarker: {e}")
        else:
            print(f"Model file not found: {model_path}")

    # Fallback to Haar cascade if MediaPipe is not available
    face_cascade = None
    eye_cascade = None
    if landmarker is None:
        print("Using OpenCV Haar Cascade fallback for face/eye detection...")
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_eye_tree_eyeglasses.xml")

    # Webcam initialization
    cap = None
    if not args.demo:
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("Webcam could not be opened. Falling back to demo mode.")
            args.demo = True

    # State variables for 3 to 5 second interval detection
    eyes_closed_start = None
    arduino_triggered = False
    esp_triggered = False
    frame_timestamp_ms = 0

    print("\nStarting detection loop... Press 'q' to exit.")

    while True:
        loop_start_time = time.time()

        if args.demo:
            # Create synthetic canvas with toggle simulation instructions
            frame = np.ones((480, 720, 3), dtype=np.uint8) * 40
            cv2.putText(frame, "DEMO MODE (No webcam required)", (40, 160),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
            cv2.putText(frame, "Hold SPACE to simulate closing eyes", (40, 210),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 220, 255), 2)
            cv2.putText(frame, "Release SPACE to simulate waking up", (40, 250),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 120), 2)
            cv2.putText(frame, "Press 'q' to quit", (40, 290),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 1)

            # In demo mode, check if space key is pressed
            key = cv2.waitKey(30) & 0xFF
            if key == ord('q'):
                break
            simulated_closed = (key == 32)  # Spacebar

            ear = 0.15 if simulated_closed else 0.35
            eyes_closed = simulated_closed
        else:
            ret, frame = cap.read()
            if not ret:
                print("Webcam read failed. Exiting.")
                break

            h, w, _ = frame.shape
            eyes_closed = False
            ear = None

            if landmarker is not None:
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
                frame_timestamp_ms += int(1000 / 30)

                detection_result = landmarker.detect_for_video(mp_image, frame_timestamp_ms)

                if detection_result.face_landmarks:
                    for landmarks in detection_result.face_landmarks:
                        left_ear, left_points = calculate_ear(LEFT_EYE_LANDMARKS, landmarks, w, h)
                        right_ear, right_points = calculate_ear(RIGHT_EYE_LANDMARKS, landmarks, w, h)

                        ear = (left_ear + right_ear) / 2.0
                        eyes_closed = ear < args.threshold

                        # Draw bounding rectangles around eyes
                        for eye_pts in [left_points, right_points]:
                            xs = [p[0] for p in eye_pts]
                            ys = [p[1] for p in eye_pts]
                            box_color = (0, 0, 255) if eyes_closed else (0, 255, 0)
                            cv2.rectangle(frame, (min(xs) - 2, min(ys) - 2),
                                          (max(xs) + 2, max(ys) + 2), box_color, 2)
                else:
                    # No face detected
                    eyes_closed = False
            else:
                # Haar cascade fallback
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)
                for (fx, fy, fw, fh) in faces[:1]:
                    face_roi = gray[fy:fy + fh // 2, fx:fx + fw]
                    detected_eyes = eye_cascade.detectMultiScale(face_roi, scaleFactor=1.1, minNeighbors=8)
                    eyes_closed = len(detected_eyes) < 2
                    for (ex, ey, ew, eh) in detected_eyes[:2]:
                        cv2.rectangle(frame, (fx + ex, fy + ey), (fx + ex + ew, fy + ey + eh),
                                      (0, 255, 0), 2)
                    cv2.rectangle(frame, (fx, fy), (fx + fw, fy + fh), (255, 200, 0), 2)

        # -------------------------------------------------------------
        # 3 to 5 Second Interval Timing Logic
        # -------------------------------------------------------------
        now = time.time()

        if eyes_closed:
            if eyes_closed_start is None:
                eyes_closed_start = now
            closed_duration = now - eyes_closed_start

            # Stage 1 Trigger: 3 Seconds (Arduino -> Buzzer ON, Stop Motor)
            if closed_duration >= args.min_interval and not arduino_triggered:
                print(f"\n[ALERT] [{closed_duration:.1f}s] Stage 1 Threshold Reached! Triggering Arduino...")
                if arduino:
                    arduino.write(b'S')
                    print(" -> Sent 'S' to Arduino (Stop motor, Buzzer ON)")
                else:
                    print(" -> [SIMULATED] Sent 'S' to Arduino (Stop motor, Buzzer ON)")
                arduino_triggered = True

            # Stage 2 Trigger: 5 Seconds (ESP32 -> Telegram Alert)
            if closed_duration >= args.max_interval and not esp_triggered:
                print(f"\n[CRITICAL] [{closed_duration:.1f}s] Stage 2 Threshold Reached! Triggering ESP32...")
                if esp32:
                    esp32.write(b'S')
                    print(" -> Sent 'S' to ESP32 (Telegram notification dispatched)")
                else:
                    print(" -> [SIMULATED] Sent 'S' to ESP32 (Telegram notification dispatched)")
                esp_triggered = True

        else:
            # Eyes are open: check if recovery from alert state is needed
            if arduino_triggered:
                print(f"\n[RECOVERY] Driver Awake after sleep! Sending 'A' to Arduino...")
                if arduino:
                    arduino.write(b'A')
                    print(" -> Sent 'A' to Arduino (Motor reactivated, Buzzer OFF)")
                else:
                    print(" -> [SIMULATED] Sent 'A' to Arduino (Motor reactivated, Buzzer OFF)")

            # Reset timer and trigger flags
            eyes_closed_start = None
            closed_duration = 0.0
            arduino_triggered = False
            esp_triggered = False

        # Render display overlay
        draw_hud(frame, ear, args.threshold, closed_duration,
                 args.min_interval, args.max_interval,
                 arduino_triggered, esp_triggered, hw_status)

        cv2.imshow("Driver Sleep Detection (3s - 5s Interval)", frame)

        if not args.demo:
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    # Cleanup resources
    print("\nShutting down system...")
    if cap:
        cap.release()
    if landmarker:
        landmarker.close()
    if arduino:
        arduino.close()
    if esp32:
        esp32.close()
    cv2.destroyAllWindows()
    print("Done.")


if __name__ == "__main__":
    main()
