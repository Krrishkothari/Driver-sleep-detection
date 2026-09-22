import argparse
import os
import time

import cv2
import numpy as np
import serial
from scipy.spatial import distance

def find_available_ports():
    try:
        return [port.device for port in serial.tools.list_ports.comports()]
    except Exception:
        return []


def open_serial_port(port_name, label):
    if not port_name:
        print(f"{label}: port not configured; skipping serial output.")
        return None

    try:
        port = serial.Serial(port_name, 9600, timeout=1)
        print(f"{label}: connected on {port_name}")
        time.sleep(2)
        return port
    except Exception as exc:
        print(f"{label}: could not open {port_name}: {exc}")
        return None


parser = argparse.ArgumentParser(description="Driver drowsiness detection")
parser.add_argument("--arduino-port", default=os.getenv("ARDUINO_PORT", "COM3"), help="Serial port for Arduino")
parser.add_argument("--esp32-port", default=os.getenv("ESP32_PORT", "COM6"), help="Serial port for ESP32")
parser.add_argument("--skip-serial", action="store_true", help="Disable serial communication entirely")
parser.add_argument("--demo", action="store_true", help="Run in demo mode without hardware or webcam")
args = parser.parse_args()

available_ports = find_available_ports()
if args.skip_serial:
    arduino = None
    esp32 = None
else:
    arduino = open_serial_port(args.arduino_port if args.arduino_port in available_ports else None, "Arduino")
    esp32 = open_serial_port(args.esp32_port if args.esp32_port in available_ports else None, "ESP32")

    if not arduino and not esp32:
        print(f"No configured serial device found. Available ports: {available_ports or 'none'}")

face_detector = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)
eye_detector = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_eye_tree_eyeglasses.xml"
)

cap = None
if not args.demo:
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Unable to open webcam. Try running with --demo to test without a camera.")
        cap = None

LEFT_EYE = [33, 160, 158, 133, 153, 144]
RIGHT_EYE = [362, 385, 387, 263, 373, 380]


def EAR(eye_points, landmarks, w, h):
    points = []
    for point in eye_points:
        x = int(landmarks[point].x * w)
        y = int(landmarks[point].y * h)
        points.append((x, y))

    A = distance.euclidean(points[1], points[5])
    B = distance.euclidean(points[2], points[4])
    C = distance.euclidean(points[0], points[3])

    return (A + B) / (2.0 * C), points


THRESHOLD = 0.23
FPS = 20
FRAME_LIMIT_3SEC = FPS * 3
FRAME_LIMIT_5SEC = FPS * 5

counter = 0
arduino_triggered = False
esp_triggered = False

if args.demo:
    print("Demo mode enabled. No camera or serial device is required.")
    while True:
        frame = 255 * np.ones((480, 640, 3), dtype=np.uint8)
        cv2.putText(frame, "Demo mode: driver sleep detection", (80, 210), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
        cv2.putText(frame, "Press 'q' to quit", (180, 270), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
        cv2.imshow("Driver Drowsiness Detection", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    cv2.destroyAllWindows()
    raise SystemExit(0)

if cap is None:
    print("Unable to start live detection. Check Windows camera permissions or use --demo.")
    raise SystemExit(0)

while cap is not None:
    ret, frame = cap.read()
    if not ret:
        print("Failed to read from webcam.")
        break

    h, w, _ = frame.shape
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_detector.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)

    for x, y, face_width, face_height in faces[:1]:
        face_gray = gray[y:y + face_height // 2, x:x + face_width]
        eyes = eye_detector.detectMultiScale(face_gray, scaleFactor=1.1, minNeighbors=8)
        eyes = sorted(eyes, key=lambda eye: eye[0])[:2]
        eyes_closed = len(eyes) < 2

        for eye_x, eye_y, eye_width, eye_height in eyes:
            color = (0, 0, 255) if eyes_closed else (0, 255, 0)
            cv2.rectangle(frame,
                          (x + eye_x, y + eye_y),
                          (x + eye_x + eye_width, y + eye_y + eye_height),
                          color, 2)

        if eyes_closed:
            counter += 1

            if counter > FRAME_LIMIT_3SEC and not arduino_triggered and arduino is not None:
                print("3 sec -> Sending S to Arduino")
                arduino.write(b'S')
                arduino_triggered = True

            if counter > FRAME_LIMIT_5SEC and not esp_triggered and esp32 is not None:
                print("5 sec -> Sending S to ESP32")
                esp32.write(b'S')
                esp_triggered = True

            cv2.putText(frame, "SLEEP DETECTED!", (50, 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        else:
            counter = 0

            if arduino_triggered and arduino is not None:
                print("Driver Awake -> Sending A")
                arduino.write(b'A')

            arduino_triggered = False
            esp_triggered = False

        cv2.rectangle(frame, (x, y), (x + face_width, y + face_height),
                      (255, 255, 0), 2)
        cv2.putText(frame, "Eyes closed" if eyes_closed else "Eyes open",
                    (30, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                    (0, 0, 255) if eyes_closed else (0, 255, 0), 2)

    cv2.imshow("Driver Drowsiness Detection", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

if cap is not None:
    cap.release()
if arduino is not None:
    arduino.close()
if esp32 is not None:
    esp32.close()
cv2.destroyAllWindows()
