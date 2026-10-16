"""Safe ranking improvements for complete synthetic coordinated outfits."""
from services.demo_outfit_quality import outfit_quality


def test_matching_occasion_and_style_receive_grounded_bonus():
    outfit = {"occasion": "Work", "style": "Classic"}
    matched = outfit_quality(outfit, [{"name": "Shirt", "materials": ["Cotton 100%"]}],
                             {"occasion": "work", "style": "classic"})
    unmatched = outfit_quality(outfit, [{"name": "Shirt", "materials": ["Cotton 100%"]}],
                               {"occasion": "party", "style": "relaxed"})
    assert matched["bonus"] == 20
    assert unmatched["bonus"] == 0
    assert "Work" in matched["reason"]
    assert "Classic" in matched["reason"]
    assert "Work" not in unmatched["reason"]


def test_hot_climate_bonus_is_small_and_uses_actual_garment_metadata():
    quality = outfit_quality({"occasion": "", "style": ""},
                             [{"name": "Linen shirt", "materials": ["Linen 100%"]},
                              {"name": "Shorts", "materials": ["Cotton 100%"]},
                              {"name": "Loafers", "materials": ["Leather 100%"]}],
                             {"climate": "hot"})
    assert quality["bonus"] == 4
    assert "2 piece(s)" in quality["reason"]


def test_unknown_outfit_metadata_does_not_claim_preference_match():
    quality = outfit_quality({}, [{"name": "Jacket"}],
                             {"occasion": "wedding", "style": "classic", "climate": "cold"})
    assert quality["bonus"] == 0
    assert "wedding" not in quality["reason"]
    assert "classic" not in quality["reason"]
