from io import BytesIO

from PIL import Image

from services.photo_privacy import sanitize_photo


def test_photo_upload_removes_exif_and_gps_metadata():
    img = Image.new("RGB", (10, 10), (120, 70, 40))
    exif = Image.Exif()
    exif[270] = "Sensitive camera notes"
    exif[274] = 1
    exif[34853] = {1: "N", 2: (27, 1)}
    data = BytesIO()
    img.save(data, format="JPEG", exif=exif)
    safe = sanitize_photo(data.getvalue(), "jpg")
    with Image.open(BytesIO(safe)) as result:
        assert result.size == (10, 10)
        assert not result.getexif()
    assert b"Sensitive camera notes" not in safe


def test_transparent_png_preserves_alpha_without_metadata():
    img = Image.new("RGBA", (4, 4), (255, 10, 20, 30))
    data = BytesIO()
    img.save(data, format="PNG", pnginfo=None)
    safe = sanitize_photo(data.getvalue(), "png")
    with Image.open(BytesIO(safe)) as result:
        assert result.mode == "RGBA"
        assert result.getpixel((0, 0))[3] == 30


def test_rejects_unknown_format():
    import pytest
    with pytest.raises(ValueError):
        sanitize_photo(b"invalid", "svg")


def test_sanitized_photo_keeps_expected_pixel_dimensions():
    image = Image.new("RGB", (12, 9), (45, 78, 120))
    buf = BytesIO()
    image.save(buf, format="WEBP")
    cleaned = sanitize_photo(buf.getvalue(), "webp")
    with Image.open(BytesIO(cleaned)) as result:
        assert result.size == (12, 9)
        assert result.format == "WEBP"
        assert not result.info.get("exif")
