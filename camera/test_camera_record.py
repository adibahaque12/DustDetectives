#!/usr/bin/env python3
"""Test 2: record a stationary 10-second camera clip on a Raspberry Pi.

Usage on the Raspberry Pi:
    python test_camera_record.py
    python test_camera_record.py --seconds 15

Requires Raspberry Pi OS, Picamera2 and a connected Pi camera.
Keep any laser disconnected during setup and camera testing.
"""
import argparse
import time
from datetime import datetime
from pathlib import Path


def record(seconds: float) -> Path:
    # Import on the Pi only, so --help still works on a laptop.
    from picamera2 import Picamera2
    from picamera2.encoders import H264Encoder
    from picamera2.outputs import PyavOutput

    folder = Path.home() / "dust-detectives" / "videos"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"camera_only_{datetime.now():%Y%m%d_%H%M%S}.mp4"

    camera = Picamera2()
    started = False
    try:
        camera.configure(camera.create_video_configuration(
            main={"size": (1280, 720), "format": "YUV420"},
            controls={"FrameRate": 30},
        ))
        camera.start_recording(
            H264Encoder(bitrate=4_000_000), PyavOutput(str(path))
        )
        started = True
        print(f"Recording a stationary shot for {seconds:g} seconds...")
        time.sleep(seconds)
    finally:
        if started:
            camera.stop_recording()
        camera.close()

    if not path.exists() or path.stat().st_size == 0:
        raise RuntimeError("No video was saved; check the camera setup.")
    print(f"Saved: {path} ({path.stat().st_size:,} bytes)")
    print("Review the video manually for focus, lighting, and stable frames.")
    return path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seconds", type=float, default=10)
    args = parser.parse_args()
    if args.seconds <= 0:
        parser.error("--seconds must be greater than zero")
    record(args.seconds)
