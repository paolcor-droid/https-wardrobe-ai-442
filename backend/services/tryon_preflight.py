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
    pose = detect_pose(preview)
    warnings.extend(pose["warnings"])
    return {
        "pose_detection": pose["status"],
        "ready": True,
        "warnings": warnings,
        "guidance": "For tops, show your upper body; for trousers or dresses, show your full body. Use good lighting, a simple background, normal fully covering clothing, and unobstructed arms and legs.",
        "limitations": "Pose estimation is optional and can miss limbs or people; it cannot determine garment fit or guarantee Gemini approval.",
        "requires_confirmation": bool(warnings),
    }


def detect_pose(image):
    """Real landmark-based pose check when an installed local model is available.

    No network requests, no paid Gemini usage and no saved landmarks. A missing
    inference engine produces 'unavailable', never a fabricated clearance.
    """
    try:
        import mediapipe as mp
        import numpy as np
        pose_module = mp.solutions.pose
    except (ImportError, AttributeError):
        return {"status": "unavailable", "warnings": []}
    try:
        with pose_module.Pose(static_image_mode=True, model_complexity=0,
                              min_detection_confidence=0.5) as detector:
            result = detector.process(np.asarray(image.convert("RGB")))
        if not result.pose_landmarks:
            return {"status": "no_person_detected", "warnings": [
                "A full person could not be detected. Use a clearly visible standing photograph."
            ]}
        points = result.pose_landmarks.landmark
        indices = pose_module.PoseLandmark
        def visible(name):
            point = points[getattr(indices, name).value]
            return point.visibility >= 0.55 and 0.03 <= point.x <= 0.97 and 0.03 <= point.y <= 0.97
        upper = all(visible(name) for name in ("LEFT_SHOULDER", "RIGHT_SHOULDER", "LEFT_HIP", "RIGHT_HIP"))
        lower = all(visible(name) for name in ("LEFT_KNEE", "RIGHT_KNEE", "LEFT_ANKLE", "RIGHT_ANKLE"))
        warnings = []
        if not upper:
            warnings.append("Your shoulders or hips are unclear or cropped; try a front-facing photograph.")
        if upper and not lower:
            warnings.append("Your full legs are not visible; full-length garments may not render well.")
        return {"status": "detected", "warnings": warnings}
    except (RuntimeError, ValueError, OSError):
        return {"status": "unavailable", "warnings": []}
