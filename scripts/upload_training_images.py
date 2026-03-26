"""
Upload ASL training images from a Roboflow COCO JSON dataset to Azure Custom Vision.

Usage:
    pip install azure-cognitiveservices-vision-customvision msrest
    python scripts/upload_training_images.py --dataset-dir /path/to/roboflow/download

Expected dataset structure (COCO JSON export from Roboflow):
    <dataset-dir>/
        train/
            _annotations.coco.json
            image1.jpg
            ...
        valid/
            _annotations.coco.json
            ...
        test/
            _annotations.coco.json
            ...

Azure credentials are read from environment variables (same .env as the app):
    AZURE_CUSTOM_VISION_TRAINING_ENDPOINT  <-- endpoint from veneziacvinstance (training resource)
    AZURE_CUSTOM_VISION_TRAINING_KEY       <-- key from veneziacvinstance (training resource)
    AZURE_CUSTOM_VISION_PROJECT_ID         <-- project ID from customvision.ai
"""

import argparse
import json
import os
import sys
from pathlib import Path

from azure.cognitiveservices.vision.customvision.training import CustomVisionTrainingClient
from azure.cognitiveservices.vision.customvision.training.models import (
    ImageFileCreateBatch,
    ImageFileCreateEntry,
)
from msrest.authentication import ApiKeyCredentials

# Signs to upload — keys are names to use in Custom Vision,
# values are lists of aliases that may appear in the dataset class names.
# Edit this mapping to match the exact class names in your downloaded dataset.
SIGN_ALIASES: dict[str, list[str]] = {
    "hello":            ["hello", "Hello"],
    "thank_you":        ["thankyou", "thank you", "thank_you", "Thank You"],
    "please":           ["please", "Please"],
    "yes":              ["yes", "Yes"],
    "no":               ["no", "No"],
    "help":             ["help", "help", "Help", "need help"],
    "sorry":            ["sorry"],
    "good":             ["good", "good-asl-"],
    "bad":              ["bad-asl-", "bad-bsl-"],
    "understand":       ["understand", "i understand"],
    "goodbye":          ["goodbye", "bye", "Bye"],
    "my_name":          ["name", "Name"],
    "how_are_you":      ["how are you-", "how are you"],
    # "again" and "dont_understand" not found in any dataset — skip for now
}

SPLITS = ["train", "valid", "test"]
BATCH_SIZE = 64


def build_alias_map(sign_aliases: dict[str, list[str]]) -> dict[str, str]:
    """Returns a flat map from each alias (lowercased) to the canonical sign name."""
    result = {}
    for canonical, aliases in sign_aliases.items():
        for alias in aliases:
            result[alias.lower()] = canonical
    return result


def load_split(dataset_dir: Path, split: str) -> tuple[dict[str, str], dict[int, str]]:
    """
    Returns:
        image_map: image_id (str) -> absolute file path
        label_map: image_id (str) -> class name (lowercased)
    """
    annotations_file = dataset_dir / split / "_annotations.coco.json"
    if not annotations_file.exists():
        return {}, {}

    with open(annotations_file) as f:
        coco = json.load(f)

    id_to_file = {img["id"]: dataset_dir / split / img["file_name"] for img in coco["images"]}
    id_to_cat = {cat["id"]: cat["name"].lower() for cat in coco["categories"]}

    label_map = {}
    for ann in coco["annotations"]:
        image_id = ann["image_id"]
        if image_id not in label_map:  # take first annotation per image
            label_map[image_id] = id_to_cat[ann["category_id"]]

    return id_to_file, label_map


def upload_images(
    trainer: CustomVisionTrainingClient,
    project_id: str,
    tag_map: dict[str, object],
    alias_map: dict[str, str],
    image_paths: dict[str, list[Path]],
) -> None:
    for canonical_name, paths in image_paths.items():
        if not paths:
            continue
        tag_id = tag_map[canonical_name].id
        entries = []
        for p in paths:
            if not p.exists():
                print(f"  WARNING: file not found, skipping: {p}")
                continue
            entries.append(
                ImageFileCreateEntry(
                    name=p.name,
                    contents=p.read_bytes(),
                    tag_ids=[tag_id],
                )
            )

        uploaded = 0
        for i in range(0, len(entries), BATCH_SIZE):
            batch = entries[i : i + BATCH_SIZE]
            result = trainer.create_images_from_files(
                project_id, ImageFileCreateBatch(images=batch)
            )
            if not result.is_batch_successful:
                for img in result.images:
                    if img.status != "OK":
                        print(f"  ERROR uploading {img.source_url}: {img.status}")
            uploaded += len(batch)

        print(f"  {canonical_name}: {uploaded} images uploaded")


def main() -> None:
    parser = argparse.ArgumentParser(description="Upload Roboflow COCO dataset to Azure Custom Vision")
    parser.add_argument("--dataset-dir", required=True, help="Path to the extracted Roboflow download folder")
    parser.add_argument("--dry-run", action="store_true", help="Print what would be uploaded without actually uploading")
    args = parser.parse_args()

    dataset_dir = Path(args.dataset_dir).expanduser().resolve()
    if not dataset_dir.exists():
        print(f"ERROR: dataset directory not found: {dataset_dir}")
        sys.exit(1)

    endpoint = os.environ.get("AZURE_CUSTOM_VISION_TRAINING_ENDPOINT", "").rstrip("/")
    training_key = os.environ.get("AZURE_CUSTOM_VISION_TRAINING_KEY", "")
    project_id = os.environ.get("AZURE_CUSTOM_VISION_PROJECT_ID", "")

    if not all([endpoint, training_key, project_id]):
        print("ERROR: set AZURE_CUSTOM_VISION_TRAINING_ENDPOINT, AZURE_CUSTOM_VISION_TRAINING_KEY, and AZURE_CUSTOM_VISION_PROJECT_ID")
        sys.exit(1)

    alias_map = build_alias_map(SIGN_ALIASES)

    # Collect images per canonical sign across all splits
    images_by_sign: dict[str, list[Path]] = {name: [] for name in SIGN_ALIASES}
    skipped_classes: set[str] = set()

    for split in SPLITS:
        id_to_file, label_map = load_split(dataset_dir, split)
        if not id_to_file:
            continue
        for image_id, class_name in label_map.items():
            canonical = alias_map.get(class_name)
            if canonical:
                images_by_sign[canonical].append(id_to_file[image_id])
            else:
                skipped_classes.add(class_name)

    print("Images found per sign:")
    for name, paths in images_by_sign.items():
        print(f"  {name}: {len(paths)}")

    if skipped_classes:
        print(f"\nSkipped classes (not in SIGN_ALIASES): {sorted(skipped_classes)}")
        print("Edit SIGN_ALIASES in the script to include them if needed.\n")

    if args.dry_run:
        print("\nDry run — no images uploaded.")
        return

    credentials = ApiKeyCredentials(in_headers={"Training-key": training_key})
    trainer = CustomVisionTrainingClient(endpoint, credentials)

    # Create tags (skip if already exist)
    existing_tags = {t.name: t for t in trainer.get_tags(project_id)}
    tag_map = {}
    for canonical_name in SIGN_ALIASES:
        if canonical_name in existing_tags:
            tag_map[canonical_name] = existing_tags[canonical_name]
            print(f"Tag already exists: {canonical_name}")
        else:
            tag_map[canonical_name] = trainer.create_tag(project_id, canonical_name)
            print(f"Created tag: {canonical_name}")

    print("\nUploading images...")
    upload_images(trainer, project_id, tag_map, alias_map, images_by_sign)
    print("\nDone. Go to customvision.ai and click Train.")


if __name__ == "__main__":
    main()
