# Driver Sleep Detection

A Python-based driver drowsiness detection system that uses a webcam and MediaPipe face landmarks to monitor eye aspect ratio (EAR). If the driver's eyes remain closed beyond a defined threshold, the system flags potential sleepiness and can trigger alerts for connected hardware such as Arduino or ESP32 devices.

## Features

- Real-time face detection using MediaPipe
- Eye landmark tracking
- Eye aspect ratio (EAR) monitoring
- Drowsiness detection based on eye closure threshold
- Visual alert overlay on the webcam feed
- Simulated trigger messages for Arduino/ESP32 integration

## Requirements

- Python 3.9+
- OpenCV (`cv2`)
- MediaPipe
- SciPy

Install dependencies:

```bash
pip install opencv-python mediapipe scipy
```

## Run the project

```bash
python main.py
```

- Press `q` to quit the webcam window.
- The program checks for sleepy behavior based on eye closure and prints simulated hardware alerts when thresholds are crossed.

## Project structure

- `main.py` — main detection logic
- `face_landmarker.task` — MediaPipe face landmark model
- `circuit_image.png` — diagram or reference image for the hardware setup
- `Arduino Uno/` and `ESP32/` — hardware-related folders

## Notes

This project is intended as a prototype for driver safety monitoring and can be extended with real serial communication to an Arduino or ESP32 board.
