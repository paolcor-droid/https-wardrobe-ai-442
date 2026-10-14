"""Synthetic, non-personal regression cases for the free Try-On preflight."""
import io
import pytest
from PIL import Image
from services.tryon_preflight import assess_photo


def fixture_photo(width, height, brightness=128):
    output = io.BytesIO()
    Image.new("RGB", (width, height), (brightness,) * 3).save(output, format="PNG")
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
