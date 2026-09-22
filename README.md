# Driver Sleep Detection

A Python and Arduino-based system that detects driver drowsiness and sends alerts.

## Requirements

- Python 3.11+
- OpenCV
- NumPy
- SciPy
- PySerial
- Arduino Uno
- ESP32

## Installation

```bash
pip install opencv-python numpy scipy pyserial
```

## Run

```bash
python main.py --arduino-port COM3 --esp32-port COM6
```

For a software-only test:

```bash
python main.py --demo
```

Use `--skip-serial` to disable Arduino and ESP32 communication. The hardware
sketches use a 9600-baud serial connection.

## Hardware

- Upload `Arduino Uno/sleep-detection.ino` to the Arduino Uno.
- Upload `ESP32/notification.ino` to the ESP32.
- Configure the ESP32 Wi-Fi and Telegram bot credentials before uploading.

