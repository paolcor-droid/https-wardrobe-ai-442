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
