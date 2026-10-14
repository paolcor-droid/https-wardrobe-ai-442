"""Deterministic image-quality screening. Never sends customer images to an AI provider."""
import io
from PIL import Image, ImageStat, ImageFilter, UnidentifiedImageError


def assess_photo(data: bytes, garment_prompt: str = "") -> dict:
    if not isinstance(data, bytes) or len(data) > 8 * 1024 * 1024:
        raise ValueError("Invalid image")
    try:
        with Image.open(io.BytesIO(data)) as source:
            source.verify()
        with Image.open(io.BytesIO(data)) as source:
            image = source.convert("RGB")
            width, height = image.size
            preview = image.copy()
            preview.thumbnail((160, 160))
            gray = preview.convert("L")
            luminance = ImageStat.Stat(gray).mean[0]
            contrast = ImageStat.Stat(gray).stddev[0]
            edges = gray.filter(ImageFilter.FIND_EDGES)
            edge_strength = ImageStat.Stat(edges).stddev[0]
    except (OSError, ValueError, UnidentifiedImageError, Image.DecompressionBombError) as exc:
        raise ValueError("Invalid image") from exc
    warnings = []
    if min(width, height) < 512:
        warnings.append("Your photograph is low resolution; a sharper photo may improve the preview.")
    if luminance < 45:
        warnings.append("Your photograph looks dark; try brighter, even lighting.")
    if luminance > 235:
        warnings.append("Your photograph looks overexposed; avoid strong glare.")
    if contrast < 9:
        warnings.append("Your photo has very little contrast; a clearer background and even lighting may help.")
    if edge_strength < 8:
        warnings.append("Your photo may lack visible detail; check that the person is in focus.")
    if width > height * 1.5:
        warnings.append("Your photo is very wide; a portrait photo showing your outfit may work better.")
    name = garment_prompt.lower()
    if any(word in name for word in ("trouser", "jean", "pants", "skirt", "dress")):
        warnings.append("For trousers, skirts or dresses, use a standing photo showing your legs.")
    return {
        "ready": True,
        "warnings": warnings,
        "guidance": "For tops, show your upper body; for trousers or dresses, show your full body. Use good lighting, a simple background, normal fully covering clothing, and unobstructed arms and legs.",
        "limitations": "Automatic checks assess image dimensions, brightness and basic detail only; they cannot verify pose, body visibility, garment fit or Gemini approval.",
        "requires_confirmation": bool(warnings),
    }
