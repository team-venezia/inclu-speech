"""
Capture neutral webcam frames and upload them to Azure Custom Vision as the Negative tag.

This teaches the model to output low confidence when no sign is being made,
fixing the false-positive spam problem.

Usage:
    cd backend
    source .venv/bin/activate
    pip install opencv-python-headless  # if not already installed
    python ../scripts/capture_negative_frames.py

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


COUNTDOWN = 5  # seconds before capture starts


def main():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("❌  Cannot open webcam.")
        sys.exit(1)

    # Warm up the camera (first few frames are often dark/blurry)
    for _ in range(10):
        cap.read()

    print("\n=== Negative Frame Capture ===")
    print(f"Target: {TARGET_FRAMES} frames at {CAPTURE_INTERVAL}s intervals "
          f"(~{int(TARGET_FRAMES * CAPTURE_INTERVAL)}s total)")
    print("\nInstructions:")
    print("  - Sit naturally in front of the camera, NO signing")
    print("  - Move around slightly, change hand positions, look different directions")
    print("  - Stay still enough that the webcam can see you\n")

    print(f"Starting in {COUNTDOWN} seconds — get ready...")
    for i in range(COUNTDOWN, 0, -1):
        print(f"  {i}...")
        time.sleep(1)
    print("  GO — capturing now\n")

    frames: list[bytes] = []
    last_capture = time.time() - CAPTURE_INTERVAL  # capture immediately on first iteration

    while len(frames) < TARGET_FRAMES:
        ret, frame = cap.read()
        if not ret:
            print("❌  Lost camera feed.")
            break

        now = time.time()
        if (now - last_capture) >= CAPTURE_INTERVAL:
            _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            frames.append(buf.tobytes())
            last_capture = now
            count = len(frames)
            bar = "█" * (count * 20 // TARGET_FRAMES) + "░" * (20 - count * 20 // TARGET_FRAMES)
            print(f"\r  [{bar}] {count}/{TARGET_FRAMES}", end="", flush=True)

    cap.release()
    print(f"\n\n✅  Captured {len(frames)} frames.")

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
