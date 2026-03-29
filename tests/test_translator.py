import sys
from pathlib import Path

# Ensure src/ is on path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from translator import (
    load_dictionary,
    build_lookup,
    build_english_pos_lookup,
    zamgrh_to_english,
    zamgrh_to_structure,
)


# ---------------------------
# Translator helper
# ---------------------------

def build_translator():
    data = load_dictionary()
    lookup = build_lookup(data)
    eng_lookup = build_english_pos_lookup(data)

    def run(text, debug=False):
        return zamgrh_to_english(text, lookup, eng_lookup, debug=debug)

    return run, lookup


# ---------------------------
# Grouped test cases
# ---------------------------

TEST_GROUPS = {

    "core": [
        ("zambahz maz barg bra!nz", "Zombies must eat brains"),
        ("mah zambah bargz bra!nz", "I eat brains"),
        ("zambahz zmazh barragahz", "Zombies smash barricades"),
    ],

    "pronouns": [
        ("g!b gaa bra!nz", "Give you brains"),
        ("gaa g!b mah bra!nz", "You give me brains"),
        ("gab m!z ahz", "Speak with us"),
    ],

    "gloss_picker": [
        ("mah zambah gan barg bra!nz", "I will eat brains"),
        ("nam nam nam", "Eat eat eat"),
        ("mah gang", "My group"),
        ("g!b mah bra!nz", "Give me brains"),
        ("mah zambah", "I"),
        ("za harman", "The human"),
    ],

     "negation": [
        ("nah g!b bra!nz", "Do not give brains"),
        ("nah ran nahaarh", "Do not go away"),
        ("nah nah g!b bra!nz", "Do not do not give brains"),
    ],

    "questions": [
        ("!z raam azza !nn?", "Is a room at the inn?"),
        ("zambah barg bra!nz?", "Zombie eat brains?"),
    ],

    "imperatives": [
        ("g!b bra!nz", "Give brains"),
        ("g!b mah bra!nz", "Give me brains"),
        ("barg bra!nz", "Eat brains"),
    ],

    "articles_and_plural": [
        ("zambah", "Zombie"),
        ("harman", "Human"),
        ("zambahz barg bra!nz", "Zombies eat brains"),
        ("zambah barg bra!n", "Zombie eat a brain"),
    ],

    "agreement": [
        ("zambah bargz bra!nz", "Zombie eats brains"),
        ("harmanz bah", "Humans are bad"),
        ("harman bah", "Human is bad"),
    ],

    "conjunctions": [
        ("g!b bra!nz an g!b zarram", "Give brains and give a serum"),
        ("g!b bra!nz arh g!b zarram", "Give brains or give a serum"),
    ],

    "unknown_words": [
        ("zambahz flargh bra!nz", "Zombies [flargh] brains"),
    ],

    "edge_cases": [
        ("", ""),
        ("nah", "Do not"),
        ("bra!nz", "Brains"),
    ],

    "duplicate_grammar_triggers": [
        ("zambah !z bah", "Zombie is bad"),          # no double copula
        ("zambahz !z bah", "Zombies are bad"),       # explicit copula + plural normalization
        ("mah zambah gonna barg bra!nz", "I am going to eat brains"),  # no missing "am"
    ],

    "preposition_and_article_collisions": [
        ("g!b bra!nz zaa harman", "Give brains to a human"),
        ("g!b bra!nz zaa zah harman", "Give brains to the human"),
        ("gaam zaa mah", "Come to me"),              # no "to I"
    ],

    "auxiliary_collisions": [
        ("mah zambah maz hab bra!nz", "I must have brains"),
        ("mah zambah gan barg bra!nz", "I will eat brains"),
        ("mah zambah haz barg bra!nz", "I have eat brains"),  # useful as a current-behavior lock if parser is imperfect
    ],

    "copula_vs_lexical_is": [
        ("zambah n!z", "Zombie is nice"),
        ("zambah !z n!z", "Zombie is nice"),
        ("zambah !z !z", "Zombie is is"),            # ugly, but good to expose weird dictionary interactions
    ],

    "unknown_word_mixed_with_known": [
        ("gab flargh ahz", "Speak [flargh] us"),
        ("flargh zambah", "[flargh] zombie"),
        ("zambah flargh harman", "Zombie [flargh] human"),
    ],

    "punctuation_and_case": [
        ("HARRAH!", "Hello"),
        ("G!B BRA!NZ!", "Give brains"),
        ("nah G!B BRA!NZ!", "Do not give brains"),
    ],

    "repeated_words": [
        ("nam nam nam", "Eat eat eat"),
        ("bra!nz bra!nz bra!nz", "Brains brains brains"),
        ("nah nah nah g!b bra!nz", "Do not do not do not give brains"),
    ],

    "plural_normalization_edges": [
        ("harmanz", "Humans"),
        ("zambahz", "Zombies"),
        ("gahz", "Yous"),   # useful if this breaks incorrectly; catches over-eager plural stripping
    ],

    "empty_and_whitespace": [
        ("", ""),
        ("   ", ""),
    ],

    "long_sentences": [
        (
            "mah zambah maz barg bra!nz an zmazh harman",
            "I must eat brains and smash a human"
        ),
        (
            "nah g!b bra!nz arh zambahz zmazh gaa an harman ran nahaarh",
            "Do not give brains or zombies smash you and a human goes away"
        ),
    ],
}


# ---------------------------
# Test runner
# ---------------------------

def run_tests():
    translator, lookup = build_translator()

    passed = 0
    failed = 0

    for group, cases in TEST_GROUPS.items():
        print(f"\n=== {group.upper()} ===")

        for zamgrh, expected in cases:
            result = translator(zamgrh)

            if result == expected:
                print(f"PASS: {zamgrh}")
                passed += 1
            else:
                print(f"FAIL: {zamgrh}")
                print(f"  expected: {expected}")
                print(f"  got:      {result}")

                # 🔍 Debug pipeline
                print(f"\nDEBUG for {zamgrh}:")
                translator(zamgrh, debug=True)

                # 🔍 Structure insight (NEW)
                structure = zamgrh_to_structure(zamgrh, lookup)
                print(f"[structure] {structure}")

                failed += 1

    print("\n---")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")

    return failed == 0


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
