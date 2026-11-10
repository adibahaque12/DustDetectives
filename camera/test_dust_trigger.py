#!/usr/bin/env python3
"""Test 3: simulated PM2.5 spike detection and optional camera/servo response.

Laptop (no Raspberry Pi needed):
    python test_dust_trigger.py

On Raspberry Pi after wiring and motor checks:
    python test_dust_trigger.py --record-on-trigger

Uses synthetic readings, NOT the SPS30 sensor yet. No laser control.
"""
import argparse
import csv
import statistics
import time
from collections import deque
from datetime import datetime
from pathlib import Path

# Made-up PM2.5 readings in ug/m^3 for a proof-of-concept test.
DEMO_PM25 = [12, 11, 12, 12, 13, 12, 13, 14, 42, 48, 17, 12]


def detect_event(readings):
    """Yield (reading, baseline, is_event) for each synthetic sample."""
    quiet = deque(maxlen=5)
    consecutive_high = 0

    for reading in readings:
        baseline = statistics.mean(quiet) if len(quiet) >= 5 else None
        if baseline is None:
            quiet.append(reading)
            yield reading, None, False
            continue

        # A spike must be substantially above the recent quiet baseline.
        high = reading >= baseline + 15 and reading >= baseline * 2
        if high:
            consecutive_high += 1
        else:
            consecutive_high = 0
            quiet.append(reading)

        # Require two consecutive high samples to reduce false alarms.
        event = consecutive_high >= 2
        yield reading, baseline, event
        if event:
            return


def record_sweep():
    """Start camera recording only when triggered; make a small pan sweep."""
    from adafruit_servokit import ServoKit
    from picamera2 import Picamera2
    from picamera2.encoders import H264Encoder
    from picamera2.outputs import PyavOutput

    # Verify clearance and servo/controller wiring before running this.
    kit = ServoKit(channels=16, address=0x40, frequency=50)
    PAN_CHANNEL = 1
    TILT_CHANNEL = 0
    for channel in (PAN_CHANNEL, TILT_CHANNEL):
        kit.servo[channel].set_pulse_width_range(500, 2500)

    folder = Path.home() / "dust-detectives" / "videos"
    folder.mkdir(parents=True, exist_ok=True)
    filename = folder / f"triggered_{datetime.now():%Y%m%d_%H%M%S}.mp4"

    camera = Picamera2()
    recording = False
    try:
        camera.configure(camera.create_video_configuration(
            main={"size": (1280, 720), "format": "YUV420"},
            controls={"FrameRate": 30},
        ))
        # The camera is not recording before the event.
        # These initial commands may cause immediate physical movement.
        kit.servo[PAN_CHANNEL].angle = 90
        kit.servo[TILT_CHANNEL].angle = 90
        time.sleep(1)

        camera.start_recording(
            H264Encoder(bitrate=4_000_000), PyavOutput(str(filename))
        )
        recording = True
        print(f"EVENT DETECTED: recording started -> {filename}")

        position = 90
        for target in (80, 100, 90):
            step = 1 if target > position else -1
            for angle in range(position + step, target + step, step):
                kit.servo[PAN_CHANNEL].angle = angle
                time.sleep(0.08)
            position = target
            time.sleep(1)
    finally:
        if recording:
            camera.stop_recording()
        camera.close()
        # Servos continue holding their final position.

    print(f"Recording saved: {filename}")


def main(record_on_trigger=False):
    log_folder = Path.cwd() / "test_logs"
    log_folder.mkdir(exist_ok=True)
    log_path = log_folder / f"dust_trigger_{datetime.now():%Y%m%d_%H%M%S}.csv"

    triggered = False
    with log_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["sample", "pm25_ug_m3", "baseline_ug_m3", "trigger"])
        for index, (reading, baseline, event) in enumerate(detect_event(DEMO_PM25), 1):
            writer.writerow([index, reading, "" if baseline is None else round(baseline, 2), int(event)])
            print(f"Sample {index:02d}: PM2.5={reading:5.1f} | baseline={baseline} | event={event}")
            if event:
                triggered = True
                print("PASS: dust spike triggered the event after two high samples.")
                if record_on_trigger:
                    record_sweep()
                else:
                    print("Simulation only: video and motor would start NOW.")
                break

    print(f"Log saved: {log_path}")
    if not triggered:
        raise RuntimeError("FAIL: demo spike did not trigger detection.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--record-on-trigger", action="store_true",
                        help="Use the Pi camera and servo after a simulated dust event")
    args = parser.parse_args()
    main(args.record_on_trigger)
