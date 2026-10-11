"""Offline garment-only colour evaluation from manually cropped garment photos.

This is a quality-control tool, NOT an automatic clothing segmenter. Input
photos must be manually cropped so that no skin, hair or background remains.
No images or reports are uploaded or committed.

Usage:
  python scripts/evaluate_garment_crops.py /private/crops /private/labels.json

labels.json example:
  [{"file":"shirt.jpg","expected_family":"blue"}]

The report never asserts garment image verification without a manual crop.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

from PIL import Image, ImageOps

from audit_matterhorn_colours import coarse_colour

SUPPORTED = {".jpg", ".jpeg", ".png", ".webp"}


def classify_crop(path: Path) -> dict:
    with Image.open(path) as original:
        image = ImageOps.exif_transpose(original).convert("RGB")
        image.thumbnail((250, 250))
        width, height = image.size
        if width < 12 or height < 12:
            raise ValueError("Crop too small")
        # Trim edges to reduce remaining backdrop; this cannot remove skin.
        pixels = [
            image.getpixel((x, y))
            for y in range(height // 10, height * 9 // 10, 3)
            for x in range(width // 10, width * 9 // 10, 3)
        ]
        families = Counter(coarse_colour(pixel) for pixel in pixels)
        winner, count = families.most_common(1)[0]
        return {
            "candidate_family": winner,
            "dominance": round(count / len(pixels), 3),
            "image_colour_verified": False,
            "requires_manual_crop_review": True,
        }


def evaluate(folder: Path, labels: list[dict]) -> dict:
    results = []
    for row in labels:
        name = row["file"]
        if Path(name).name != name or Path(name).suffix.lower() not in SUPPORTED:
            raise ValueError("Only simple JPEG/PNG/WebP filenames are accepted")
        prediction = classify_crop(folder / name)
        expected = row["expected_family"].strip().lower()
        results.append({
            "file": name,
            "expected_family": expected,
            **prediction,
            "match": prediction["candidate_family"] == expected,
        })
    return {
        "evaluated": len(results),
        "correct": sum(x["match"] for x in results),
        "accuracy": round(sum(x["match"] for x in results) / len(results), 3) if results else None,
        "results": results,
        "limitation": "Only manually cropped garment regions; not proof of automated segmentation or demographic fairness.",
    }


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("Usage: evaluate_garment_crops.py PRIVATE_CROP_FOLDER PRIVATE_LABELS_JSON")
    folder = Path(sys.argv[1])
    labels = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
    report = evaluate(folder, labels)
    print(json.dumps(report, indent=2))
