"""Synthetic, non-personal regression cases for the free Try-On preflight."""
import io
import pytest
from PIL import Image
from services.tryon_preflight import assess_photo


@pytest.fixture(autouse=True)
def keep_image_quality_tests_independent_of_optional_pose_model(monkeypatch):
    # The real MediaPipe inference path is tested separately by smoke_pose_detection.py.
    # Image-quality tests must give the same results with or without a cached model.
    monkeypatch.setattr(
        "services.tryon_preflight.detect_pose",
        lambda image: {"status": "unavailable", "warnings": []},
    )


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


def test_pose_unavailable_when_local_model_absent(monkeypatch, tmp_path):
    from services.tryon_preflight import detect_pose
    monkeypatch.setenv("LUMIERE_POSE_MODEL_PATH", str(tmp_path / "not-installed.task"))
    assert detect_pose(Image.new("RGB", (640, 960))) == {
        "status": "unavailable", "warnings": []
    }
