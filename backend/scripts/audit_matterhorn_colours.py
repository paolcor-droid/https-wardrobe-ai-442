"""Audit supplier image colours for manual review; never claim image verification.

Run after installing Pillow: python -m pip install Pillow
Then: python backend/scripts/audit_matterhorn_colours.py
Images contain backgrounds, models and patterns: pixel sampling is NOT garment
segmentation and must never be used to confirm skin-palette matches automatically.
"""
from __future__ import annotations

import colorsys
import io
import json
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

import requests
from PIL import Image, ImageOps

CATALOGUE = Path(__file__).resolve().parents[1] / ".lumiere-private-catalogue" / "matterhorn_products.json"
OUTPUT = CATALOGUE.parent / "colour_image_audit.json"
MAX_BYTES = 5_000_000
MAX_ITEMS = 12


def coarse_colour(rgb):
    r, g, b = rgb
    h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
    if v < 0.19:
        return "black"
    if s < 0.12:
        return "white" if v > 0.84 else "grey"
    if s < 0.23 and 0.19 < v < 0.72:
        return "muted neutral"
    if 0.53 < h < 0.74:
        return "blue"
    if 0.25 < h < 0.53:
        return "green"
    if h < 0.06 or h > 0.95:
        return "red"
    if h < 0.17:
        return "orange / brown"
    if h < 0.25:
        return "yellow / beige"
    if 0.74 < h < 0.95:
        return "purple / pink"
    return "other"


def inspect(url):
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname:
        return {"error": "non-HTTPS image URL"}
    # Avoid redirect-based requests to unexpected destinations.
    response = requests.get(url, timeout=12, stream=True, allow_redirects=False)
    response.raise_for_status()
    if response.is_redirect:
        return {"error": "redirect not inspected"}
    raw = bytearray()
    for chunk in response.iter_content(65536):
        raw.extend(chunk)
        if len(raw) > MAX_BYTES:
            return {"error": "image exceeds 5 MB audit limit"}
    image = ImageOps.exif_transpose(Image.open(io.BytesIO(raw))).convert("RGB")
    image.thumbnail((120, 120))
    w, h = image.size
    # Centre sampling is a heuristic, not proof of garment colour.
    pixels = [image.getpixel((x, y)) for y in range(h // 4, max(h // 4 + 1, 3 * h // 4), 3)
              for x in range(w // 4, max(w // 4 + 1, 3 * w // 4), 3)]
    counts = Counter(coarse_colour(pixel) for pixel in pixels)
    return {"centre_region_colour_families": counts.most_common(4),
            "image_colour_verified": False,
            "review_required": True,
            "limitation": "Model, background, pattern and lighting may contaminate centre pixels."}


def main():
    products = json.loads(CATALOGUE.read_text(encoding="utf-8"))
    # Sample diverse source labels from actual products, not fabricated examples.
    seen = set()
    samples = []
    for product in products:
        colour = str((product.get("colour_names") or [""])[0]).strip().lower()
        if not colour or colour in seen or not product.get("image_url"):
            continue
        seen.add(colour)
        samples.append(product)
        if len(samples) >= MAX_ITEMS:
            break
    report = []
    for product in samples:
        try:
            audit = inspect(product["image_url"])
        except (requests.RequestException, OSError, ValueError) as exc:
            audit = {"error": str(exc)[:160]}
        report.append({"product_id": product["external_id"], "name": product["name"],
                       "supplier_colour": product.get("colour_names"),
                       "image_url": product["image_url"], "audit": audit})
        print(product["external_id"], product.get("colour_names"), audit)
    OUTPUT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print("Audit saved locally:", OUTPUT, "(never publish supplier data)")


if __name__ == "__main__":
    main()
