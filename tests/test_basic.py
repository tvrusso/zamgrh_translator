from src.translator import zamgrh_to_english, build_lookup, load_dictionary

def test_basic_translation():
    data = load_dictionary()
    lookup = build_lookup(data)

    result = zamgrh_to_english("mah ganna nam bra!n", lookup)
    assert "eat" in result
