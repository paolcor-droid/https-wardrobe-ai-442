"""Trusted, source-backed Stefania handbag references for opt-in AI illustrations.

Only an allowlisted local catalogue photograph may be forwarded to the image
provider. No user-supplied URLs, paths, or arbitrary image data are fetched.
Prices and current stock are not inferred.
"""
from __future__ import annotations

import hashlib
import io
import re
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

ROOT = Path(__file__).resolve().parents[2]
HERO_DIR = ROOT / "frontend" / "assets" / "spc-handbags"
# SKU -> name, labelled colour, labelled material, product size from approved catalogue.
BAGS = {
    "01": ("Velvet Black & Grey", "Black / Medium Grey", "chenille, cotton-polyester, cotton, satin", "21 × 17 cm"),
    "02": ("Blue Night", "Midnight Blue", "chenille, cotton-polyester, cotton, satin", "24 × 16 cm"),
    "03": ("Petali Dorati", "Dusty Rose / Gold", "chenille, cotton-polyester, lurex, satin", "24 × 16 cm"),
    "04": ("Double Queen", "Deep Sea Green", "chenille, cotton-polyester, cotton, satin", "24 × 16 cm"),
    "05": ("Diva Noir", "Black", "chenille, cotton-polyester, cotton, satin", "24 × 16 cm"),
    "06": ("Velvet Black Diamonds", "Black / Medium Grey", "chenille, cotton-polyester, cotton, satin", "21 × 17 cm"),
    "07": ("Notte di Cristallo", "Black", "chenille, cotton-polyester, cotton, satin", "24 × 16 cm"),
    "08": ("Diamond Blue", "Midnight Blue / Olive Green", "chenille, cotton-polyester, cotton, satin", "21 × 17 cm"),
    "09": ("Perla D'Oro", "Beige", "chenille, cotton-polyester, cotton, satin", "24 × 16 cm"),
    "10": ("Velvet Golden Jewel", "Turmeric / Gold", "chenille, cotton-polyester, lurex, satin", "24 × 16 cm"),
    "11": ("Occhio di Tigre", "Turmeric / Caramel", "chenille, cotton-polyester, cotton, satin", "21 × 17 cm"),
    "12": ("Notte Stellata", "Khaki / Caramel / Gold", "chenille, cotton-polyester, lurex, satin", "24 × 16 cm"),
    "13": ("Ambra", "Khaki / Caramel", "chenille, cotton-polyester, cotton, satin", "21 × 17 cm"),
    "14": ("Aurea", "Dark Brown", "duplex leather, satin", "23 × 14 × 3 cm"),
    "15": ("Aura Sposa", "Silk White", "satin", "21 × 14 × 3 cm"),
    "16": ("Rosa D’argento", "Antique Rose / Silver", "cotton, lurex, satin", "23 × 16 × 4 cm"),
    "17": ("Doreé", "Gold", "lurex, satin", "23 × 16 × 4 cm"),
    "18": ("Diamante Rosa", "Antique Rose / Silver", "cotton, lurex, satin", "23 × 16 × 4 cm"),
}

class HandbagReferenceError(ValueError):
    pass


def handbag_reference(sku: str) -> tuple[dict[str, str], bytes]:
    """Return trusted metadata and a small sanitized JPEG reference.

    The original catalogue JPEG is never modified or written by this function.
    Missing/corrupted assets cause an explicit error, never a generic substitute.
    """
    if not isinstance(sku, str) or not re.fullmatch(r"SPC-FW2627-(0[1-9]|1[0-8])", sku):
        raise HandbagReferenceError("Unknown Stefania handbag SKU")
    num = sku[-2:]
    details = BAGS.get(num)
    if not details:
        raise HandbagReferenceError("Handbag SKU is not approved")
    path = HERO_DIR / f"{sku}_hero.jpg"
    try:
        if not path.is_file() or path.stat().st_size > 8_000_000:
            raise HandbagReferenceError("Approved handbag photograph is unavailable")
        raw = path.read_bytes()
        with Image.open(io.BytesIO(raw)) as original:
            if original.format != "JPEG" or original.width * original.height > 30_000_000:
                raise HandbagReferenceError("Unsupported handbag photograph")
            converted = ImageOps.exif_transpose(original).convert("RGB")
            converted.thumbnail((1024, 1024))
            out = io.BytesIO()
            converted.save(out, "JPEG", quality=87, optimize=True)
    except (OSError, UnidentifiedImageError, Image.DecompressionBombError) as exc:
        raise HandbagReferenceError("Approved handbag photograph is unavailable") from exc
    data = out.getvalue()
    if len(data) > 1_500_000:
        raise HandbagReferenceError("Handbag photograph exceeds reference size limit")
    name, colour, material, dimensions = details
    return ({
        "sku": sku, "name": name, "colour": colour, "brand": "Stefania P. Creations",
        "material": material, "dimensions": dimensions,
        "photo_sha256": hashlib.sha256(raw).hexdigest(),
    }, data)
