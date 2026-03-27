import sys
from pathlib import Path

# Ensure src/ is on path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from translator import load_dictionary, build_lookup, zamgrh_to_english


TEST_CASES = [
    ("zambahz maz barg bra!nz", "Zombies must eat brains"),
    ("mah zambah bargz bra!nz", "I eats brains"),
    ("harmanz bah! nah ma!g barragahz", "Humans are bad do not make barricades"),
    ("bah harman, nah bang bang mah zambah", "Bad human do not shoot shoot me"),
    ("g!b bra!nz, harman", "Give brains human"),
    ("mah gang habbah zambahz", "My group happy zombies"),
    ("bangbangman nah bang bang mah zambah", "Headhunter do not shoot shoot me"),
    ("zambahz zmazh barragahz", "Zombies smash barricades"),
    ("narz! mah zambah maz hab bra!n zarram!", "Nurse I must have brain serum"),
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
    ("mah zambah maz hab zarram", "I must have serum"),
    ("bra!nz bra!nz bra!nz", "Brains brains brains"),
    ("nah nah g!b bra!nz", "Do not do not give brains"),
]


def run_tests():
    data = load_dictionary()
    lookup = build_lookup(data)

    passed = 0
    failed = 0

    for zamgrh, expected in TEST_CASES:
        result = zamgrh_to_english(zamgrh, lookup)

        if result == expected:
            print(f"PASS: {zamgrh}")
            passed += 1
        else:
            print(f"FAIL: {zamgrh}")
            print(f"  expected: {expected}")
            print(f"  got:      {result}")
            print(f"\nDEBUG for {zamgrh}:")
            zamgrh_to_english(zamgrh, lookup, debug=True)
            failed += 1

    print("\n---")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")

    return failed == 0


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
