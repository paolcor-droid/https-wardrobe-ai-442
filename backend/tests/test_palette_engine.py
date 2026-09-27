from services.palette_engine import build_palette
from services.recommendation_engine import recommendation_score, is_hot_weather_suitable

def test_warm_light_clear_differs_from_warm_deep_muted():
    a = build_palette("warm", "light", "clear", "medium")
    b = build_palette("warm", "deep", "muted", "medium")
    assert a["best_neutrals"] != b["best_neutrals"]
    assert a["best_accents"] != b["best_accents"]

def test_neutral_warm_and_neutral_cool_differ():
    a = build_palette("neutral_warm", "medium", "balanced", "medium")
    b = build_palette("neutral_cool", "medium", "balanced", "medium")
    assert a["best_accents"] != b["best_accents"]

def test_hot_weather_excludes_heavy_outerwear():
    coat = {"name": "Wool Overcoat", "description": "Long wool coat", "category": "outerwear"}
    linen = {"name": "Linen Shirt", "description": "Light linen", "category": "tops"}
    assert not is_hot_weather_suitable(coat)
    assert is_hot_weather_suitable(linen)

def test_budget_and_occasion_are_hard_constraints():
    p = {"name":"Linen Shirt","description":"Light linen","category":"tops","price":200,"occasions":["casual"],"palette_tags":["warm"]}
    cp = {"undertone":"warm"}
    assert recommendation_score(p, cp, "casual", 150, "hot") == -1
    assert recommendation_score(p, cp, "formal", 300, "hot") == -1
