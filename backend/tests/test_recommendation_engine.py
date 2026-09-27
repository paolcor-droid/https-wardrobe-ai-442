from services.recommendation_engine import recommendation_reasons, recommendation_score

CP_WARM = {"undertone": "neutral_warm", "depth": "medium", "chroma": "muted", "contrast": "medium"}

def product(**overrides):
    p = {"name":"Linen Shirt","description":"Light linen shirt","category":"tops","price":100,
         "occasions":["casual"],"palette_tags":["warm","neutral"],"colors":["#E4C9A7"]}
    p.update(overrides); return p

def test_hot_weather_rejects_wool():
    p=product(name="Wool Overcoat",description="Long wool coat",category="outerwear")
    assert recommendation_score(p, CP_WARM, "casual", 500, "hot", "classic") == -1

def test_hot_weather_rewards_linen():
    assert recommendation_score(product(), CP_WARM, "casual", 500, "hot", "relaxed") > 70

def test_budget_is_hard_constraint():
    assert recommendation_score(product(price=301), CP_WARM, "casual", 300, "mild", "classic") == -1

def test_occasion_is_hard_constraint():
    assert recommendation_score(product(), CP_WARM, "formal", 300, "mild", "classic") == -1

def test_reasons_are_human_readable():
    reasons=recommendation_reasons(product(), CP_WARM, "casual", "hot", "relaxed")
    assert 1 <= len(reasons) <= 3
    assert any("colour" in r.lower() for r in reasons)
    assert any("hot weather" in r.lower() for r in reasons)
