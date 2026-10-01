from services.palette_engine import build_palette
from services.recommendation_engine import is_hot_weather_suitable, recommendation_score, recommendation_reasons


def test_palette_is_multidimensional_and_named():
    warm = build_palette("warm", "deep", "muted", "high")
    cool = build_palette("cool", "light", "clear", "low")
    for palette in (warm, cool):
        assert palette["best_neutrals"]
        assert palette["best_accents"]
        assert palette["statement_colours"]
        assert palette["caution_colours"]
        assert all("name" in c and "hex" in c for group in palette.values() for c in group)
    assert warm != cool


def test_hot_weather_excludes_heavy_layers():
    assert not is_hot_weather_suitable({"name": "Wool blazer", "description": "heavy wool blazer"})
    assert is_hot_weather_suitable({"name": "Linen shirt", "description": "light linen shirt"})


def test_recommendation_rejects_over_budget():
    product = {
        "name": "Linen shirt", "description": "light linen shirt", "price": 250,
        "palette_tags": ["warm"], "occasions": ["casual"]
    }
    score = recommendation_score(
        product, {"undertone": "warm"}, "casual", 100, "hot", "relaxed", [], []
    )
    assert score < 0


def test_reasons_explain_active_context():
    product = {
        "name": "Linen shirt", "description": "light linen relaxed shirt", "price": 80,
        "palette_tags": ["warm"], "occasions": ["casual"]
    }
    reasons = recommendation_reasons(
        product, {"undertone": "warm"}, "casual", "hot", "relaxed"
    )
    assert reasons


def test_personal_colour_preferences_change_score():
    product = {
        "name": "Navy cotton shirt", "description": "light cotton shirt", "price": 80,
        "colour_names": ["navy"], "palette_tags": ["neutral"], "occasions": ["casual"]
    }
    liked = recommendation_score(product, {"undertone": "neutral"}, "casual", 150, "hot", "classic", ["navy"], [])
    avoided = recommendation_score(product, {"undertone": "neutral"}, "casual", 150, "hot", "classic", [], ["navy"])
    assert liked > avoided


def test_colour_preference_reason_is_visible():
    product = {
        "name": "Navy cotton shirt", "description": "light cotton shirt", "price": 80,
        "colour_names": ["navy"], "palette_tags": ["neutral"], "occasions": ["casual"]
    }
    reasons = recommendation_reasons(product, {"undertone": "neutral"}, "casual", "hot", "classic", ["navy"], [])
    assert any("preferred clothing colours" in reason for reason in reasons)
