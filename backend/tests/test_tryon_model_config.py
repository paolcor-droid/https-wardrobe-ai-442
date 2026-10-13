"""Regression guard: do not accidentally restore a retired Gemini preview ID."""
from pathlib import Path

def test_private_tryon_uses_supported_stable_image_model():
    source = (Path(__file__).resolve().parents[1] / "server.py").read_text()
    assert 'IMAGE_MODEL = ("gemini", "gemini-3.1-flash-image")' in source
    assert 'IMAGE_MODEL = ("gemini", "gemini-3.1-flash-image-preview")' not in source
