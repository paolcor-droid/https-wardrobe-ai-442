"""Audit supplier image colours for manual review; never claim image verification.

Install optional foreground isolation: python -m pip install "rembg[cpu]" Pillow
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
    image.thumbnail((320, 320))
    try:
        from rembg import remove, new_session
    except ImportError:
        return {"isolation_status": "unavailable", "review_required": True,
                "image_colour_verified": False, "reason": "Install rembg[cpu] for optional foreground isolation"}
    foreground = remove(image.convert("RGBA"), session=new_session("u2netp"))
    if not isinstance(foreground, Image.Image):
        foreground = Image.open(io.BytesIO(foreground)).convert("RGBA")
    alpha = foreground.getchannel("A")
    w, h = foreground.size
    # Conservative body region reduces background and face contamination,
    # but this is not semantic garment segmentation.
    pixels = [image.getpixel((x, y))
              for y in range(int(h * .32), int(h * .85), 2)
              for x in range(int(w * .20), int(w * .80), 2)
              if alpha.getpixel((x, y)) >= 220]
    if len(pixels) < 150:
        return {"isolation_status": "insufficient_foreground",
                "candidate_pixels": len(pixels),
                "review_required": True, "image_colour_verified": False}
    counts = Counter(coarse_colour(pixel) for pixel in pixels)
    total = sum(counts.values())
    return {"isolation_status": "foreground_central_body_candidate",
            "candidate_region_colour_families": [
                {"family": name, "fraction": round(count / total, 3)}
                for name, count in counts.most_common(5)],
            "candidate_pixels": total, "review_required": True,
            "image_colour_verified": False,
            "limitation": "Foreground isolation is not garment segmentation; skin, hair and accessories may remain."}


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
