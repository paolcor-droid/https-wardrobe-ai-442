"""Strip photograph metadata before persistence without changing the accepted format.

Caller must first validate dimensions, encoding and byte size. The sanitized
payload contains pixels only; orientation is applied before EXIF is discarded.
"""
from io import BytesIO
from PIL import Image, ImageOps


def sanitize_photo(data: bytes, extension: str) -> bytes:
    formats = {"jpg": "JPEG", "jpeg": "JPEG", "png": "PNG", "webp": "WEBP"}
    if extension not in formats:
        raise ValueError("Unsupported photograph format")
    with Image.open(BytesIO(data)) as source:
        upright = ImageOps.exif_transpose(source)
        # A new image ensures EXIF, XMP, GPS, comments, thumbnails and ICC
        # metadata from the source are not copied to persisted bytes.
        mode = "RGBA" if upright.mode in {"RGBA", "LA", "P"} and extension != "jpg" and extension != "jpeg" else "RGB"
        pixels = upright.convert(mode)
        clean = Image.new(mode, pixels.size)
        clean.paste(pixels)
        output = BytesIO()
        options = {"quality": 92} if formats[extension] == "JPEG" else {}
        clean.save(output, format=formats[extension], **options)
        payload = output.getvalue()
        if len(payload) > 8 * 1024 * 1024:
            raise ValueError("Sanitized photograph exceeds 8 MB storage limit")
        return payload
