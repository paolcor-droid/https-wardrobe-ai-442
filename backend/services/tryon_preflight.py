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
    """Run local MediaPipe Tasks inference when model asset is available.

    Returns unavailable rather than claiming successful screening when
    dependency/model cannot load. No user image leaves the backend.
    """
    import os
    from pathlib import Path
    model_path = Path(os.environ.get(
        "LUMIERE_POSE_MODEL_PATH",
        str(Path(__file__).resolve().parents[1] / ".lumiere-models" / "pose_landmarker_lite.task"),
    ))
    if not model_path.is_file():
        return {"status": "unavailable", "warnings": []}
    try:
        import mediapipe as mp
        import numpy as np
        from mediapipe.tasks import python
        from mediapipe.tasks.python import vision
        options = vision.PoseLandmarkerOptions(
            base_options=python.BaseOptions(model_asset_path=str(model_path)),
            running_mode=vision.RunningMode.IMAGE,
            num_poses=1,
            min_pose_detection_confidence=0.5,
        )
        frame = mp.Image(image_format=mp.ImageFormat.SRGB,
                         data=np.asarray(image.convert("RGB")))
        with vision.PoseLandmarker.create_from_options(options) as detector:
            result = detector.detect(frame)
    except (ImportError, AttributeError, RuntimeError, ValueError, OSError):
        return {"status": "unavailable", "warnings": []}
    if not result.pose_landmarks:
        return {"status": "no_person_detected", "warnings": [
            "A person could not be detected clearly. Try a well-lit, unobstructed photo."
        ]}
    points = result.pose_landmarks[0]
    # Standard MediaPipe 33-landmark topology, no landmarks are persisted.
    landmark_indices = {
        "LEFT_SHOULDER": 11, "RIGHT_SHOULDER": 12,
        "LEFT_HIP": 23, "RIGHT_HIP": 24,
        "LEFT_KNEE": 25, "RIGHT_KNEE": 26,
        "LEFT_ANKLE": 27, "RIGHT_ANKLE": 28,
    }
    def visible(name):
        point = points[landmark_indices[name]]
        return point.visibility >= 0.55 and 0.02 <= point.x <= 0.98 and 0.02 <= point.y <= 0.98
    upper = all(visible(name) for name in ("LEFT_SHOULDER", "RIGHT_SHOULDER", "LEFT_HIP", "RIGHT_HIP"))
    lower = all(visible(name) for name in ("LEFT_KNEE", "RIGHT_KNEE", "LEFT_ANKLE", "RIGHT_ANKLE"))
    warnings = []
    if not upper:
        warnings.append("Your shoulders or hips are unclear or cropped; try a front-facing photograph.")
    if upper and not lower:
        warnings.append("Your full legs are not visible; full-length garments may not render well.")
    return {"status": "detected", "warnings": warnings}
