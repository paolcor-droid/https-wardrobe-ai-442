from services.demo_outfit_variants import select_outfit_colours


def _product(*colours):
    return {"name": "Demo shirt", "colour_names": list(colours)}


def test_preserves_original_when_eligible():
    profile = {"preferences": {"preferred_colours": ["Navy"], "avoided_colours": ["Black"]}}
    result = select_outfit_colours([_product("Navy", "Black")], ["Navy"], profile)
    assert result == {"colours": ["Navy"], "substituted": 0}


def test_falls_back_to_stocked_eligible_variant():
    profile = {"preferences": {"preferred_colours": ["Navy"], "avoided_colours": ["Black"]}}
    result = select_outfit_colours([_product("Black", "Navy"), _product("Navy")],
                                   ["Black", "Navy"], profile)
    assert result == {"colours": ["Navy", "Navy"], "substituted": 1}


def test_never_uses_avoided_colour_even_when_original():
    profile = {"preferences": {"preferred_colours": ["Navy"], "avoided_colours": ["Black"]}}
    assert select_outfit_colours([_product("Black")], ["Black"], profile) is None


def test_all_pieces_required_and_no_unknown_unstocked_colours():
    profile = {"preferences": {"preferred_colours": ["Navy"]}}
    assert select_outfit_colours([_product("Navy"), _product("Red")], ["Navy", "Red"], profile) is None
    assert select_outfit_colours([_product("Navy")], ["Navy", "Navy"], profile) is None
    assert select_outfit_colours([_product("Red")], ["Navy"], profile) is None


def test_joint_selection_prefers_contrast_over_all_navy():
    from services.demo_outfit_variants import select_harmonised_outfit_colours
    products = [_product("Navy"), _product("Navy", "Beige"), _product("Navy", "Camel")]
    profile = {"preferences": {"preferred_colours": ["Navy", "Beige", "Camel"], "avoided_colours": ["Black"]}}
    result = select_harmonised_outfit_colours(products, ["", "", ""], profile)
    assert result is not None
    assert len(set(result["colours"])) > 1
    assert all(c in p["colour_names"] for c, p in zip(result["colours"], products))


def test_joint_selection_never_invents_nonstocked_or_avoided_colour():
    from services.demo_outfit_variants import select_harmonised_outfit_colours
    products = [_product("Navy", "Black"), _product("Navy"), _product("Navy")]
    profile = {"preferences": {"preferred_colours": ["Navy"], "avoided_colours": ["Black"]}}
    result = select_harmonised_outfit_colours(products, ["", "", ""], profile)
    assert result["colours"] == ["Navy", "Navy", "Navy"]


def test_demo_exploration_expands_neutrals_but_respects_avoided_colours():
    from services.demo_outfit_variants import select_harmonised_outfit_colours
    profile = {"skin":{"best_neutrals":[{"name":"Navy"}]},
               "preferences":{"avoided_colours":["Black", "Beige"]}}
    parts = [_product("Navy"), _product("Beige", "Cream"), _product("Black", "Brown")]
    strict = select_harmonised_outfit_colours(parts, ["", "", ""], profile)
    exploratory = select_harmonised_outfit_colours(parts, ["", "", ""], profile, demo_exploratory_colours=True)
    assert strict is None
    assert exploratory is not None
    assert exploratory["colours"] == ["Navy", "Cream", "Brown"]


def test_demo_exploration_does_not_allow_unverified_bright_colours():
    from services.recommendation_engine import is_demo_colour_eligible, is_colour_eligible
    profile = {"best_neutrals":[{"name":"Navy"}]}
    p = {"colour_names":["Coral"]}
    assert not is_demo_colour_eligible(p, profile)
    assert not is_colour_eligible({"colour_names":["Cream"]}, profile)
    assert is_demo_colour_eligible({"colour_names":["Cream"]}, profile)
