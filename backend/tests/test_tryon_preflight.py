"""Synthetic, non-personal regression cases for the free Try-On preflight."""
import io
import pytest
from PIL import Image
from services.tryon_preflight import assess_photo


def fixture_photo(width, height, brightness=128):
    output = io.BytesIO()
    image = Image.new("RGB", (width, height), (brightness,) * 3)
    if brightness == 128:
        from PIL import ImageDraw
        draw = ImageDraw.Draw(image)
        for x in range(0, width, 24):
            draw.rectangle((x, 0, min(width - 1, x + 11), height - 1), fill=(60, 60, 60))
    image.save(output, format="PNG")
    return output.getvalue()


def test_adequate_photo_passes_without_blocking_paid_generation():
    result = assess_photo(fixture_photo(720, 960))
    assert result["ready"] is True
    assert result["requires_confirmation"] is False
    assert result["warnings"] == []
    assert "cannot" in result["limitations"]


def test_dark_and_low_resolution_photo_requires_confirmation():
    result = assess_photo(fixture_photo(200, 300, 10))
    assert result["requires_confirmation"] is True
    assert any("dark" in warning for warning in result["warnings"])
    assert any("resolution" in warning for warning in result["warnings"])


def test_wide_photo_and_lower_body_prompt_get_guidance():
    result = assess_photo(fixture_photo(900, 512), "Blue trousers")
    assert result["requires_confirmation"] is True
    assert any("legs" in warning for warning in result["warnings"])
    assert any("wide" in warning for warning in result["warnings"])


def test_invalid_photo_rejected_without_provider_call():
    with pytest.raises(ValueError):
        assess_photo(b"not a photo")


def test_flat_photo_warns_about_detail_before_paid_generation():
    result = assess_photo(fixture_photo(720, 960, brightness=100))
    assert result["requires_confirmation"] is True
    assert any("detail" in warning or "contrast" in warning for warning in result["warnings"])


def test_pose_landmarks_are_assessed_when_local_model_is_available(monkeypatch):
    import sys
    import types
    from services.tryon_preflight import detect_pose
    class Point:
        x = 0.5
        y = 0.5
        visibility = 0.99
    class Detector:
        def __init__(self, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def process(self, image):
            return types.SimpleNamespace(pose_landmarks=types.SimpleNamespace(landmark=[Point() for _ in range(33)]))
    names = ("LEFT_SHOULDER", "RIGHT_SHOULDER", "LEFT_HIP", "RIGHT_HIP",
             "LEFT_KNEE", "RIGHT_KNEE", "LEFT_ANKLE", "RIGHT_ANKLE")
    indices = {name: types.SimpleNamespace(value=i) for i, name in enumerate(names)}
    fake_pose = types.SimpleNamespace(Pose=Detector, PoseLandmark=types.SimpleNamespace(**indices))
    fake_media = types.SimpleNamespace(solutions=types.SimpleNamespace(pose=fake_pose))
    monkeypatch.setitem(sys.modules, "mediapipe", fake_media)
    image = Image.new("RGB", (100, 150))
    result = detect_pose(image)
    assert result == {"status": "detected", "warnings": []}
