# Dust Detectives – additional prototype tests

These are two additional tests after the existing `servo_video.py` movement-and-recording test.
**The dust readings in Test 3 are simulated; no SPS30 integration is claimed.**
Keep the laser disconnected for these early tests.

## Test 2: stationary camera recording

On a Raspberry Pi with a camera connected and Picamera2 installed:

```bash
python test_camera_record.py --seconds 10
```

Expected: an MP4 in `~/dust-detectives/videos/`. Play it back and check focus, lighting, and stability. A successful file write alone does not prove image quality.

## Test 3: event-triggered recording and servo sweep

Run the algorithm-only version on Windows, macOS, or Linux (no extra packages):

```bash
python test_dust_trigger.py
```

Expected: a simulated PM2.5 event is detected after two consecutive high samples; a CSV is written in `test_logs/`. The camera and servo are NOT operated in this mode.

After your Pi camera/controller are wired and tested:

```bash
python test_dust_trigger.py --record-on-trigger
```

Expected: the *simulated* dust event causes the camera to start an MP4 recording and the servo to perform a narrow (80–100 degree nominal) pan sweep.

## Raspberry Pi prerequisites

```bash
sudo raspi-config   # enable I2C, then reboot
sudo apt update
sudo apt install -y python3-picamera2 python3-venv python3-pip i2c-tools
cd ~/dust-detectives
python3 -m venv --system-site-packages .venv
source .venv/bin/activate
python -m pip install adafruit-circuitpython-servokit
```

Confirm `rpicam-hello --list-cameras` identifies the camera and `i2cdetect -y 1` shows the motor controller at `0x40` first. Verify the servo channel wiring and mechanical clearance; test without laser power.
