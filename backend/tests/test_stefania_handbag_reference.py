"""Trust boundary for authorised handbag image references.

Never accept a client URL or path. This suite uses local synthetic photos
and does not transmit any supplier photographs or customer records.
"""
from io import BytesIO
import pytest
from PIL import Image
from services import stefania_handbag_reference as refs


def test_known_sku_loads_only_matching_approved_product_photo(tmp_path, monkeypatch):
    monkeypatch.setattr(refs, "HERO_DIR", tmp_path)
    photo = tmp_path / "SPC-FW2627-15_hero.jpg"
    Image.new("RGB", (1200, 800), (230, 224, 215)).save(photo, "JPEG")
    bag, jpeg = refs.handbag_reference("SPC-FW2627-15")
    assert bag["sku"] == "SPC-FW2627-15"
    assert bag["name"] == "Aura Sposa"
    assert bag["colour"] == "Silk White"
    assert len(bag["photo_sha256"]) == 64
    with Image.open(BytesIO(jpeg)) as img:
        assert img.format == "JPEG"
        assert img.width <= 1024 and img.height <= 1024
    assert photo.read_bytes()[:2] == bytes([255, 216])
    other = tmp_path / "SPC-FW2627-01_hero.jpg"
    Image.new("RGB", (80, 80), (20, 20, 20)).save(other, "JPEG")
    black, black_jpeg = refs.handbag_reference("SPC-FW2627-01")
    assert black["name"] == "Velvet Black & Grey"
    assert black["colour"] == "Black / Medium Grey"
    assert jpeg != black_jpeg


@pytest.mark.parametrize("sku", [
    "", "SPC-FW2627-00", "SPC-FW2627-19",
    "../SPC-FW2627-15", "SPC-FW2627-15/../../passwords",
    "https://example.org/image.jpg", "SPC-FW2627-15.jpg",
])
def test_unknown_or_path_like_sku_is_rejected(sku):
    with pytest.raises(refs.HandbagReferenceError):
        refs.handbag_reference(sku)


def test_missing_or_corrupt_photo_cannot_fall_back_to_a_generic_bag(tmp_path, monkeypatch):
    monkeypatch.setattr(refs, "HERO_DIR", tmp_path)
    with pytest.raises(refs.HandbagReferenceError):
        refs.handbag_reference("SPC-FW2627-15")
    (tmp_path / "SPC-FW2627-15_hero.jpg").write_bytes(b"not an image")
    with pytest.raises(refs.HandbagReferenceError):
        refs.handbag_reference("SPC-FW2627-15")
