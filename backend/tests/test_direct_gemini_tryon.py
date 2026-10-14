import base64
import io
import pytest
from PIL import Image
from services.direct_gemini_tryon import generate_direct_gemini, GeminiTryOnError


def image_bytes():
    output = io.BytesIO()
    Image.new("RGB", (24, 24), "blue").save(output, "PNG")
    return output.getvalue()


class Response:
    def __init__(self, status, data=None):
        self.status_code = status
        self.data = data or {}

    def json(self):
        return self.data


def test_direct_gemini_receives_two_images_and_returns_image():
    source = image_bytes()
    captured = {}
    def post(url, **kwargs):
        captured.update(url=url, **kwargs)
        return Response(200, {"candidates": [{"content": {"parts": [
            {"text": "complete"},
            {"inlineData": {"mimeType": "image/png", "data": base64.b64encode(source).decode()}}
        ]}}]})
    output, mime = generate_direct_gemini(source, source, None, "Change clothing", api_key="fake-test-key", post=post)
    assert output == source and mime == "image/png"
    assert captured["url"].endswith("/gemini-3.1-flash-image:generateContent")
    assert len(captured["json"]["contents"][0]["parts"]) == 3
    assert captured["json"]["generationConfig"]["responseModalities"] == ["IMAGE"]
    assert "/v1/models/" in captured["url"]


def test_provider_error_never_contains_response_body_or_key():
    with pytest.raises(GeminiTryOnError) as info:
        generate_direct_gemini(image_bytes(), None, None, "test", api_key="secret",
                               post=lambda *a, **kw: Response(503, {"detail": "secret response"}))
    assert info.value.status_code == 503
    assert "secret" not in str(info.value)


def test_invalid_image_is_rejected_before_network():
    with pytest.raises(GeminiTryOnError):
        generate_direct_gemini(b"not an image", None, None, "test", api_key="test",
                               post=lambda *a, **kw: pytest.fail("must not call provider"))


def test_key_required_and_model_allowlisted():
    with pytest.raises(GeminiTryOnError):
        generate_direct_gemini(image_bytes(), None, None, "test", api_key="")
    with pytest.raises(GeminiTryOnError):
        generate_direct_gemini(image_bytes(), None, None, "test", api_key="test", model="unknown")


@pytest.mark.parametrize("payload,expected", [
    ({"promptFeedback": {"blockReason": "SAFETY"}}, "prompt_blocked"),
    ({"candidates": [{"finishReason": "IMAGE_SAFETY", "content": {"parts": []}}]}, "generation_filtered"),
    ({"candidates": [{"finishReason": "STOP", "content": {"parts": [{"text": "explanation"}]}}]}, "text_only"),
    ({}, "empty_response"),
])
def test_success_response_without_image_has_safe_reason(payload, expected):
    with pytest.raises(GeminiTryOnError) as error:
        generate_direct_gemini(
            image_bytes(), image_bytes(), None, "test", api_key="fake",
            post=lambda *a, **kw: Response(200, payload),
        )
    assert error.value.category == expected
    assert "explanation" not in str(error.value)


@pytest.mark.parametrize("status,category", [(429, "temporarily_unavailable"), (503, "temporarily_unavailable"), (403, "provider_access"), (500, "upstream")])
def test_gemini_provider_status_is_safely_classified(status, category):
    with pytest.raises(GeminiTryOnError) as error:
        generate_direct_gemini(image_bytes(), image_bytes(), None, "test", api_key="fake",
                               post=lambda *a, **kw: Response(status, {"private": "do not log"}))
    assert error.value.category == category
    assert error.value.status_code == status
    assert "private" not in str(error.value)


def test_timeout_does_not_retry_personal_images():
    import requests
    calls = []
    def timeout(*args, **kwargs):
        calls.append(1)
        raise requests.Timeout("provider timed out")
    with pytest.raises(GeminiTryOnError) as error:
        generate_direct_gemini(image_bytes(), image_bytes(), None, "test", api_key="fake", post=timeout)
    assert error.value.category == "timeout"
    assert len(calls) == 1
