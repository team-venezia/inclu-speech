"""
Capture neutral webcam frames and upload them to Azure Custom Vision as the Negative tag.

This teaches the model to output low confidence when no sign is being made,
fixing the false-positive spam problem.

Usage:
    cd backend
    source .venv/bin/activate
    pip install opencv-python-headless  # if not already installed
    python ../scripts/capture_negative_frames.py

Controls during capture:
    SPACE  — start/pause capture
    Q      — stop and upload

Azure credentials (read from backend/.env):
    AZURE_CUSTOM_VISION_TRAINING_ENDPOINT
    AZURE_CUSTOM_VISION_TRAINING_KEY
    AZURE_CUSTOM_VISION_PROJECT_ID
"""

import os
import sys
import time
from pathlib import Path

# Load backend/.env
env_file = Path(__file__).parent.parent / "backend" / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())

TRAINING_ENDPOINT = os.environ.get("AZURE_CUSTOM_VISION_TRAINING_ENDPOINT", "")
TRAINING_KEY = os.environ.get("AZURE_CUSTOM_VISION_TRAINING_KEY", "")
PROJECT_ID = os.environ.get("AZURE_CUSTOM_VISION_PROJECT_ID", "")

if not all([TRAINING_ENDPOINT, TRAINING_KEY, PROJECT_ID]):
    print("❌  Missing env vars. Set in backend/.env:")
    print("    AZURE_CUSTOM_VISION_TRAINING_ENDPOINT")
    print("    AZURE_CUSTOM_VISION_TRAINING_KEY")
    print("    AZURE_CUSTOM_VISION_PROJECT_ID")
    sys.exit(1)

try:
    import cv2
except ImportError:
    print("❌  opencv not found. Run: pip install opencv-python-headless")
    sys.exit(1)

from azure.cognitiveservices.vision.customvision.training import CustomVisionTrainingClient
from azure.cognitiveservices.vision.customvision.training.models import (
    ImageFileCreateBatch,
    ImageFileCreateEntry,
)
from msrest.authentication import ApiKeyCredentials

TARGET_FRAMES = 80
CAPTURE_INTERVAL = 0.5  # seconds between frames


def get_or_create_negative_tag(trainer, project_id: str):
    tags = trainer.get_tags(project_id)
    for tag in tags:
        if tag.name.lower() == "negative" or (hasattr(tag, "type") and str(tag.type).lower() == "negative"):
            print(f"Found existing Negative tag: {tag.id}")
            return tag
    print("Creating Negative tag...")
    from azure.cognitiveservices.vision.customvision.training.models import TagType
    tag = trainer.create_tag(project_id, "Negative", type=TagType.negative)
    print(f"Created Negative tag: {tag.id}")
    return tag


def upload_frames(frames: list[bytes], trainer, project_id: str, tag_id: str) -> None:
    batch_size = 64
    total = len(frames)
    uploaded = 0
    for i in range(0, total, batch_size):
        batch = frames[i:i + batch_size]
        entries = [
            ImageFileCreateEntry(name=f"negative_{i + j:04d}.jpg", contents=img_bytes, tag_ids=[tag_id])
            for j, img_bytes in enumerate(batch)
        ]
        result = trainer.create_images_from_files(project_id, ImageFileCreateBatch(images=entries))
        if not result.is_batch_successful:
            for img in result.images:
                if img.status != "OK":
                    print(f"  ⚠️  Image {img.source_url}: {img.status}")
        uploaded += len(batch)
        print(f"  Uploaded {uploaded}/{total}...")


def main():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("❌  Cannot open webcam.")
        sys.exit(1)

    print("\n=== Negative Frame Capture ===")
    print(f"Target: {TARGET_FRAMES} frames")
    print("Instructions:")
    print("  - Sit naturally in front of the camera, NO signing")
    print("  - Move around, change hand positions, look different directions")
    print("  - Press SPACE to start capturing")
    print("  - Press Q when done (or when target is reached)\n")

    frames: list[bytes] = []
    capturing = False
    last_capture = 0.0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        display = frame.copy()
        count = len(frames)

        # Status overlay
        status = "CAPTURING" if capturing else "PAUSED — press SPACE to start"
        color = (0, 200, 0) if capturing else (0, 140, 255)
        cv2.putText(display, status, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        cv2.putText(display, f"Frames: {count}/{TARGET_FRAMES}", (10, 65),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(display, "Q = stop & upload", (10, display.shape[0] - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (180, 180, 180), 1)

        cv2.imshow("Negative Frame Capture — IncluSpeech", display)

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q") or key == ord("Q"):
            break
        elif key == ord(" "):
            capturing = not capturing
            print("Capturing..." if capturing else "Paused.")

        now = time.time()
        if capturing and (now - last_capture) >= CAPTURE_INTERVAL:
            _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            frames.append(buf.tobytes())
            last_capture = now
            if count % 10 == 0 and count > 0:
                print(f"  {count} frames captured...")
            if len(frames) >= TARGET_FRAMES:
                print(f"\n✅  Reached {TARGET_FRAMES} frames — stopping capture.")
                break

    cap.release()
    cv2.destroyAllWindows()

    if not frames:
        print("No frames captured — exiting.")
        sys.exit(0)

    print(f"\nCaptured {len(frames)} frames. Uploading to Custom Vision...")

    credentials = ApiKeyCredentials(in_headers={"Training-key": TRAINING_KEY})
    trainer = CustomVisionTrainingClient(TRAINING_ENDPOINT, credentials)

    negative_tag = get_or_create_negative_tag(trainer, PROJECT_ID)
    upload_frames(frames, trainer, PROJECT_ID, negative_tag.id)

    print(f"\n✅  Done — {len(frames)} negative frames uploaded.")
    print("Next step: go to customvision.ai and retrain the model.")


if __name__ == "__main__":
    main()
