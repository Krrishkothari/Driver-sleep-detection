import os
import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
# import serial  # Commented out — no hardware connected
import time
from scipy.spatial import distance

# Setup FaceLandmarker using the new Tasks API
model_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'face_landmarker.task')
base_options = python.BaseOptions(model_asset_path=model_path)
options = vision.FaceLandmarkerOptions(
    base_options=base_options,
    running_mode=vision.RunningMode.VIDEO,
    num_faces=1
)

landmarker = vision.FaceLandmarker.create_from_options(options)

cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("Error: Could not open webcam.")
    exit(1)

# Same landmark indices as the original (MediaPipe face mesh 478 landmarks)
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

# setting
THRESHOLD = 0.23
FPS = 20

FRAME_LIMIT_3SEC = FPS * 3
FRAME_LIMIT_5SEC = FPS * 5

counter = 0
arduino_triggered = False
esp_triggered = False
frame_timestamp_ms = 0

while True:
    ret, frame = cap.read()
    if not ret:
        print("Failed to capture frame from webcam")
        break
    h, w, _ = frame.shape
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # Convert to mediapipe Image
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
    frame_timestamp_ms += int(1000 / FPS)

    # Detect face landmarks
    results = landmarker.detect_for_video(mp_image, frame_timestamp_ms)

    if results.face_landmarks:
        for face_landmarks_list in results.face_landmarks:
            landmarks = face_landmarks_list  # list of NormalizedLandmark

            left_ear, left_points = EAR(LEFT_EYE, landmarks, w, h)
            right_ear, right_points = EAR(RIGHT_EYE, landmarks, w, h)

            ear = (left_ear + right_ear) / 2

            # square eyes
            for eye in [left_points, right_points]:
                x_vals = [p[0] for p in eye]
                y_vals = [p[1] for p in eye]

                x_min, x_max = min(x_vals), max(x_vals)
                y_min, y_max = min(y_vals), max(y_vals)

                color = (0, 255, 0)  # Green

                if ear < THRESHOLD:
                    color = (0, 0, 255)  # Red if sleepy

                cv2.rectangle(frame,
                              (x_min, y_min),
                              (x_max, y_max),
                              color, 2)

            # main logic
            if ear < THRESHOLD:
                counter += 1

                # 3 seconds = Arduino (simulated)
                if counter > FRAME_LIMIT_3SEC and not arduino_triggered:
                    print("3 sec -> [SIMULATED] Would send 'S' to Arduino")
                    # arduino.write(b'S')
                    arduino_triggered = True

                # 5 seconds = ESP32 (simulated)
                if counter > FRAME_LIMIT_5SEC and not esp_triggered:
                    print("5 sec -> [SIMULATED] Would send 'S' to ESP32")
                    # esp32.write(b'S')
                    esp_triggered = True

                cv2.putText(frame,
                            "SLEEP DETECTED!",
                            (50, 50),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            1,
                            (0, 0, 255),
                            2)

            else:
                counter = 0

                if arduino_triggered:
                    print("Driver Awake -> [SIMULATED] Would send 'A' to Arduino")
                    # arduino.write(b'A')

                arduino_triggered = False
                esp_triggered = False

            # ear value
            cv2.putText(frame,
                        f"EAR: {ear:.2f}",
                        (30, 90),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.8,
                        (255, 255, 0),
                        2)

    cv2.imshow("Driver Drowsiness Detection", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
landmarker.close()
# arduino.close()
# esp32.close()
cv2.destroyAllWindows()