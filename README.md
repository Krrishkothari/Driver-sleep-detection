# Driver Sleep Detection

A Python-based driver drowsiness detection system that uses a webcam and MediaPipe Face Mesh landmarks to monitor Eye Aspect Ratio (EAR) in real time.

If the driver's eyes remain closed continuously within the **3 to 5-second interval**, progressive multi-stage alerts are triggered for hardware safety devices (Arduino motor kill-switch / buzzer and ESP32 emergency Telegram notifications).

## Features

- **MediaPipe FaceLandmarker**: High-precision 478 face landmark mesh tracking.
- **Accurate Eye Aspect Ratio (EAR)**: Computes Euclidean EAR independently for both eyes.
- **3 to 5-Second Alert Interval**:
  - **< 3.0s**: Ignored as natural blinking / brief gaze shift. On-screen timer tracks closure duration.
  - **3.0s (Stage 1 Warning)**: Sends `'S'` to Arduino to stop the motor relay and sound the buzzer.
  - **5.0s (Stage 2 Critical)**: Sends `'S'` to ESP32 to dispatch an emergency Telegram notification.
  - **Recovery**: Sends `'A'` to Arduino when the driver opens their eyes to restore motor power and silence the buzzer.
- **Real-Time Visual HUD**: Live EAR readout, dynamic 0s–5s interval progress bar, and stage alert indicators.
- **Graceful Hardware Simulation**: Runs in simulated mode if physical Arduino or ESP32 boards are not connected.

## Requirements

- Python 3.9+
- OpenCV (`cv2`)
- MediaPipe (`mediapipe`)
- SciPy (`scipy`)
- PySerial (`pyserial`)

Install dependencies:

```bash
pip install opencv-python mediapipe scipy pyserial
```

## Running the Project

Run with automatic hardware detection or simulation:

```bash
python main.py
```

### Custom Hardware Ports & Interval Thresholds

```bash
python main.py --arduino-port COM3 --esp32-port COM6 --min-interval 3.0 --max-interval 5.0
```

### Options

| Flag | Default | Description |
| --- | --- | --- |
| `--min-interval` | `3.0` | Seconds of continuous eye closure before Stage 1 alert (Arduino) |
| `--max-interval` | `5.0` | Seconds of continuous eye closure before Stage 2 critical alert (ESP32) |
| `--threshold` | `0.23` | EAR threshold below which eyes are considered closed |
| `--arduino-port` | `COM3` | Serial COM port for Arduino Uno |
| `--esp32-port` | `COM6` | Serial COM port for ESP32 |
| `--skip-serial` | `False` | Force simulation mode without attempting COM connection |
| `--demo` | `False` | Run simulated UI mode without webcam (Hold SPACE to test sleep) |

Press **`q`** inside the webcam window to exit.

## Hardware Configuration

- **Arduino Uno** (`Arduino Uno/sleep-detection.ino`): Controls a motor relay (pin 7) and buzzer (pin 8). Receives `'S'` to stop motor and sound alarm; receives `'A'` to resume normal driving.
- **ESP32** (`ESP32/notification.ino`): Connects to Wi-Fi and dispatches a Telegram bot alert when `'S'` is received after 5 seconds of sleep.
