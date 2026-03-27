import sys
from pathlib import Path

# Ensure src/ is on path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from translator import load_dictionary, build_lookup, build_english_pos_lookup, zamgrh_to_english


TEST_CASES = [
    ("zambahz maz barg bra!nz", "Zombies must eat brains"),
    ("mah zambah bargz bra!nz", "I eats brains"),
    ("harmanz bah! nah ma!g barragahz", "Humans are bad do not make barricades"),
    ("bah harman, nah bang bang mah zambah", "Bad human do not shoot shoot me"),
    ("g!b bra!nz, harman", "Give brains human"),
    ("mah gang habbah zambahz", "My group are happy zombies"),
    ("bangbangman nah bang bang mah zambah", "Headhunter do not shoot shoot me"),
    ("zambahz zmazh barragahz", "Zombies smash barricades"),
    ("narz! mah zambah maz haz bra!n zarram!", "Nurse I must have brain serum"),
    ("g!b bra!nz", "Give brains"),
    ("g!b mah bra!nz", "Give me brains"),
    ("barg bra!nz", "Eat brains"),
    ("grahm haarh", "Come here"),
    ("ran nahaarh", "Go away"),
    ("hab mah","Help me"),
    ("hab mah zambah","Help me"),
    ("nah ran nahaarh","Do not go away"),
    ("nah hab harman","Do not help human"),
    ("mah zambah zmazh harman", "I smash human"),
    ("zambahz zmazh gaa", "Zombies smash you"),
    ("g!b bra!nz arh zambahz zmazh gaa", "Give brains or zombies smash you"),
    ("nah g!b bra!nz an zambahz zmazh gaa", "Do not give brains and zombies smash you"),
    ("mah gang zmazh barragahz", "My group smash barricades"),
    ("mah gang nah ran nahaarh", "My group do not go away"),
    ("narz g!b zarram", "Nurse give serum"),
    ("mah zambah maz haz zarram", "I must have serum"),
    ("bra!nz bra!nz bra!nz", "Brains brains brains"),
    ("nah nah g!b bra!nz", "Do not do not give brains"),

    # 🔀 Ambiguity (hab: have vs help)
    ("hab mah bra!nz", "Help me brains"),
    ("mah zambah hab bra!nz", "I have brains"),
    ("mah zambah haz bra!nz", "I have brains"),
    ("nah hab mah zambah", "Do not help me"),

    # 👥 Pronouns
    ("g!b gaa bra!nz", "Give you brains"),
    ("gaa g!b mah bra!nz", "You give me brains"),
    ("zambahz zmazh gaa", "Zombies smash you"),

    # 🔁 Word order variants
    ("g!b bra!nz zaa mah zambah", "Give brains to me"),
    ("mah zambah g!b bra!nz", "I give brains"),

    # 🔗 Conjunction chains
    ("g!b bra!nz an g!b zarram", "Give brains and give serum"),
    ("g!b bra!nz arh g!b zarram", "Give brains or give serum"),
    ("nah g!b bra!nz an nah g!b zarram", "Do not give brains and do not give serum"),

    # ❗ Repetition / emphasis
    ("g!b g!b bra!nz", "Give give brains"),
    ("nah nah nah g!b bra!nz", "Do not do not do not give brains"),

    # 🧩 Unknown words (fallback behavior)
    ("zambahz flargh bra!nz", "Zombies [flargh] brains"),

    # 🔤 Morphology / plural interaction
    ("zambah zmazh harmanz", "Zombie smash humans"),
    ("harmanz zmazh zambahz", "Humans smash zombies"),

    # 🧠 Longer sentences
    ("mah zambah maz barg bra!nz an zmazh harman",
     "I must eat brains and smash human"),

    ("nah g!b bra!nz arh zambahz zmazh gaa an harman ran nahaarh",
     "Do not give brains or zombies smash you and human go away"),

    # ⚠️ Grammar collision tests (are-insertion edge cases)
    ("bra!nz an zarram", "Brains and serum"),
    ("zambahz arh harmanz", "Zombies or humans"),

    # 🧪 Minimal inputs
    ("", ""),
    ("nah", "Do not"),
    ("bra!nz", "Brains"),
]


def run_tests():
    data = load_dictionary()
    lookup = build_lookup(data)
    eng_lookup = build_english_pos_lookup(data)

    passed = 0
    failed = 0

    for zamgrh, expected in TEST_CASES:
        result = zamgrh_to_english(zamgrh, lookup, eng_lookup)

        if result == expected:
            print(f"PASS: {zamgrh}")
            passed += 1
        else:
            print(f"FAIL: {zamgrh}")
            print(f"  expected: {expected}")
            print(f"  got:      {result}")
            print(f"\nDEBUG for {zamgrh}:")
            zamgrh_to_english(zamgrh, lookup, eng_lookup, debug=True)
            failed += 1

    print("\n---")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")

    return failed == 0


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
