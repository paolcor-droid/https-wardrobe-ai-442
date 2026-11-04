"""Pre-Loved safety and stylist matching tests. Synthetic records only."""
import pytest

from services.preloved_marketplace import (
    validate_listing, public_listing, rank_pre_loved, match_listing,
)


def sample_listing(**updates):
    return {"size": "M", "condition": "good", "price": 55, "currency": "AUD",
            "description": "Worn occasionally", "delivery": "arrange later", **updates}


def public_record(**updates):
    return {"id": "listing-1", "user_id": "seller-secret",
            "wardrobe_item_id": "private-wardrobe-secret",
            **sample_listing(), "status": "published", **updates}


def garment(**updates):
    return {"name": "Navy shirt", "category": "top", "colour": "navy",
            "style": "classic", "image_path": "private:secret-photo", **updates}


def test_public_listings_do_not_disclose_private_account_or_photo():
    listing = public_listing(public_record(), garment())
    for field in ("user_id", "seller_id", "wardrobe_item_id", "image_path", "path",
                  "skin", "profile", "email", "created_at"):
        assert field not in listing
    assert listing["photo_available"] is False
    assert listing["checkout_enabled"] is False
    assert listing["messaging_enabled"] is False
    assert "secret-photo" not in repr(listing)


@pytest.mark.parametrize("details", [
    sample_listing(description="Find me at example@domain.test"),
    sample_listing(description="https://unsafe.example/link"),
    sample_listing(size="m@example.com"),
    sample_listing(price=float("inf")),
    sample_listing(price=True),
    sample_listing(swap_accepted="yes"),
    sample_listing(currency="USD"),
])
def test_private_listings_reject_bad_fields_or_publishing_rejects_public_pii(details):
    if details.get("size") == "m@example.com":
        validated = validate_listing(details)
        with pytest.raises(ValueError):
            public_listing(public_record(**validated), garment())
    else:
        with pytest.raises(ValueError):
            validate_listing(details)


def test_swap_preference_is_explicit_and_not_a_transaction():
    validated = validate_listing(sample_listing(swap_accepted=True))
    assert validated["swap_accepted"] is True
    shown = public_listing(public_record(**validated), garment())
    assert shown["swap_accepted"] is True
    assert shown["checkout_enabled"] is False


def test_colour_profile_and_size_limit_recommendations():
    listing = public_listing(public_record(), garment())
    profile = {"sizes": {"top": "M"},
               "preferences": {"style": "classic", "preferred_colours": ["navy"]},
               "skin": {"best_neutrals": [{"name": "Navy"}]}}
    owned = [{"id": "pants", "name": "Cream trousers", "category": "bottom",
              "colour": "cream", "style": "classic"}]
    matches = rank_pre_loved([listing], profile, owned)
    assert len(matches) == 1
    assert matches[0]["match_score"] >= 55
    assert "skin" not in matches[0] and "sizes" not in matches[0]
    assert match_listing(listing, profile={**profile, "sizes": {"top": "S"}},
                         wardrobe=owned)["eligible"] is False
    assert match_listing(listing, profile={
        **profile, "preferences": {"avoided_colours": ["navy"]}},
        wardrobe=owned)["eligible"] is False


def test_public_labels_with_contact_information_cannot_be_published():
    with pytest.raises(ValueError):
        public_listing(public_record(), garment(name="Email seller@private.test"))
