import argparse
import time
from datetime import datetime
from pathlib import Path

from adafruit_servokit import ServoKit
from picamera2 import Picamera2
from picamera2.encoders import H264Encoder
from picamera2.outputs import PyavOutput

# Arducam controller channels
PAN = 1                       # Left/right motor
TILT = 0                      # Up/down motor

CENTER = 90
PAN_MIN, PAN_MAX = 80, 100     # Small initial sweep
STEP_DELAY = 0.08             # Seconds per one-degree command


def move_pan(kit: ServoKit, current: int, target: int) -> int:
    """Move gradually within the configured test range."""
    if not PAN_MIN <= current <= PAN_MAX:
        raise ValueError("Starting angle is outside the test range.")
    if not PAN_MIN <= target <= PAN_MAX:
        raise ValueError("Target angle is outside the test range.")

    step = 1 if target > current else -1

    for angle in range(current + step, target + step, step):
        kit.servo[PAN].angle = angle
        time.sleep(STEP_DELAY)

    return target


def main(servo_only: bool = False) -> None:
    camera = None
    recording = False
    filename = None

    try:
        kit = ServoKit(channels=16, address=0x40, frequency=50)

        for channel in (PAN, TILT):
            kit.servo[channel].set_pulse_width_range(500, 2500)

        if not servo_only:
            camera = Picamera2()
            camera.configure(
                camera.create_video_configuration(
                    main={
                        "size": (1280, 720),
                        "format": "YUV420",
                    },
                    controls={"FrameRate": 30},
                )
            )

            folder = Path.home() / "dust-detectives" / "videos"
            folder.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            filename = folder / f"scan_{timestamp}.mp4"

        # These first commands may move the mount immediately.
        kit.servo[PAN].angle = CENTER
        kit.servo[TILT].angle = CENTER
        time.sleep(1)

        if camera is not None:
            camera.start_recording(
                H264Encoder(bitrate=4_000_000),
                PyavOutput(str(filename)),
            )
            recording = True
            print(f"Recording: {filename}")
        else:
            print("Servo-only test; no video will be recorded.")

        time.sleep(2)
        position = CENTER

        # Center -> one side -> other side -> center
        for target in (PAN_MIN, PAN_MAX, CENTER):
            print(f"Moving pan to nominal {target} degrees")
            position = move_pan(kit, position, target)
            time.sleep(2)

    except KeyboardInterrupt:
        print("\nSweep stopped; closing the video if recording.")

    finally:
        if camera is not None:
            try:
                if recording:
                    camera.stop_recording()
            finally:
                camera.close()

        # Leave the mount holding its position.
        # Do not automatically release a loaded camera mount.

    if recording and filename is not None and filename.is_file():
        print(f"Saved: {filename}")

    print("Servos remain at their last commanded positions.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--servo-only",
        action="store_true",
        help="Test the motors without recording video",
    )
    args = parser.parse_args()

    try:
        main(servo_only=args.servo_only)
    except (OSError, RuntimeError, ValueError) as error:
        raise SystemExit(f"Test failed: {error}") from error