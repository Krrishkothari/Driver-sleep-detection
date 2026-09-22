# Driver-sleep-detection
A smart safety system that detects eye closure using OpenCV and triggers hardware alerts and Telegram notifications.

[Youtube Video](https://youtu.be/Ro1PGaYQGAA?si=fOacbK1fvZLjC9Ne) 

# Used 

- Python 3.11
- OpenCV
- MediaPipe
- SciPy

- PySerial

- Arduino UNO

- ESP32

- Telegram Bot API

# Setup

Install the Python dependencies:

```bash
pip install opencv-python numpy mediapipe scipy pyserial
```

Run the detector with a webcam:

```bash
python main.py --arduino-port COM3 --esp32-port COM6
```

Use `--skip-serial` to run without connected hardware, or `--demo` to test the
application without a webcam or serial devices. The Arduino and ESP32 sketches
communicate with the Python application at 9600 baud.



# Circuit Diagram 
![Circuit](/circuit_image.png) 
https://app.cirkitdesigner.com/project/30748c38-c57c-428b-a3e8-32bdcb254925
 
 # Telegram Bot Setup for ESP32 Notification

 1. Create bot using BotFather

2. Get Bot Token

3. Get Chat ID using @userinfobot

4. Add credentials in ESP32 code

