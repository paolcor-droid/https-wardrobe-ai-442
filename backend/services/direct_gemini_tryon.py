"""Direct Gemini image editing. No customer images, keys, or provider bodies are logged."""
import base64
import io
from PIL import Image, UnidentifiedImageError
import requests

URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
ALLOWED_MODELS = {"gemini-3.1-flash-image", "gemini-2.5-flash-image"}
MAX_INPUT = 8 * 1024 * 1024
MAX_OUTPUT = 12 * 1024 * 1024


class GeminiTryOnError(RuntimeError):
    def __init__(self, category, status=None):
        self.category = category
        self.status_code = status
        super().__init__("Gemini Try-On failed")  # Never forward provider response text.


def _inline_image(data):
    if not isinstance(data, bytes) or len(data) > MAX_INPUT:
        raise GeminiTryOnError("invalid_input")
    try:
        with Image.open(io.BytesIO(data)) as img:
            img.verify()
        with Image.open(io.BytesIO(data)) as img:
            fmt = img.format
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise GeminiTryOnError("invalid_input") from exc
    mime = {"PNG": "image/png", "JPEG": "image/jpeg", "WEBP": "image/webp"}.get(fmt)
    if not mime:
        raise GeminiTryOnError("invalid_input")
    return {"inline_data": {"mime_type": mime, "data": base64.b64encode(data).decode("ascii")}}


def generate_direct_gemini(person, garment, second, instruction, *, api_key, model="gemini-3.1-flash-image", post=None):
    if not api_key:
        raise GeminiTryOnError("configuration")
    if model not in ALLOWED_MODELS:
        raise GeminiTryOnError("invalid_model")
    parts = [{"text": instruction}, _inline_image(person)]
    if garment is not None:
        parts.append(_inline_image(garment))
    if second is not None:
        parts.append(_inline_image(second))
    client = post or requests.post
    try:
        response = client(
            URL.format(model=model),
            headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
            json={"contents": [{"role": "user", "parts": parts}],
                  "generationConfig": {"responseModalities": ["TEXT", "IMAGE"]}},
            timeout=150,
        )
    except requests.RequestException as exc:
        raise GeminiTryOnError("network") from exc
    if response.status_code != 200:
        raise GeminiTryOnError("upstream", response.status_code)
    try:
        payload = response.json()
        for candidate in payload.get("candidates", []):
            for part in (candidate.get("content") or {}).get("parts", []):
                inline = part.get("inlineData") or part.get("inline_data")
                if isinstance(inline, dict) and inline.get("data"):
                    raw = base64.b64decode(inline["data"], validate=True)
                    if not raw or len(raw) > MAX_OUTPUT:
                        raise GeminiTryOnError("invalid_output")
                    _inline_image(raw) if len(raw) <= MAX_INPUT else _verify_large_image(raw)
                    return raw, inline.get("mimeType") or inline.get("mime_type") or "image/png"
    except (KeyError, TypeError, ValueError) as exc:
        raise GeminiTryOnError("invalid_output") from exc
    raise GeminiTryOnError("no_image")


def _verify_large_image(data):
    try:
        with Image.open(io.BytesIO(data)) as img:
            img.verify()
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise GeminiTryOnError("invalid_output") from exc
