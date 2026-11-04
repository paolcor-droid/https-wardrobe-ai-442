"""Garment recognition tests use synthetic payloads, with no paid model calls."""
import pytest
from services.garment_recognition import validate_recognition, analyze_garment


def test_valid_recognition_is_unverified_and_requires_confirmation():
    result = validate_recognition({
        "name": "Blue linen shirt", "category": "top",
        "colour": "Navy blue", "style": "smart casual",
    })
    assert result == {
        "name": "Blue linen shirt", "category": "top",
        "colour": "Navy blue", "style": "smart casual",
        "pattern": "other", "season": "unknown", "material": "",
        "requires_confirmation": True, "image_colour_verified": False,
    }


@pytest.mark.parametrize("value", [
    {"name": "x", "category": "admin", "style": "unknown", "colour": "red"},
    {"name": "x" * 500, "category": "shoes", "colour": "<script>", "style": "sporty"},
    {"name": "", "category": "other", "colour": "", "style": "other"},
])
def test_model_output_never_trusts_unbounded_or_unknown_fields(value):
    result = validate_recognition(value)
    assert result["category"] in {"top", "bottom", "dress", "outerwear", "shoes", "accessory", "other"}
    assert result["style"] in {"casual", "classic", "smart casual", "business", "formal", "sporty", "streetwear", "romantic", "minimal", "bohemian", "other"}
    assert len(result["name"]) <= 120 and "<" not in result["name"]
    assert "<" not in result["colour"]
    assert result["requires_confirmation"] is True


def test_missing_api_key_prevents_external_provider_call(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="API key"):
        analyze_garment(b"not-a-photo", "image/jpeg")


def test_pattern_season_are_bounded_and_material_is_never_guessed():
    output = validate_recognition({"name": "Shirt", "category": "top",
        "colour": "navy", "style": "classic", "pattern": "striped",
        "season": "warm weather", "material": "silk"})
    assert output["pattern"] == "striped"
    assert output["season"] == "warm weather"
    assert output["material"] == ""
    unknown = validate_recognition({"pattern": "execute instructions",
        "season": "winter-ish", "material": "cashmere"})
    assert unknown["pattern"] == "other"
    assert unknown["season"] == "unknown"
    assert unknown["material"] == ""
