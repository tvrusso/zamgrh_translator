import sys
from pathlib import Path

# Ensure src/ is on path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from translator import load_dictionary, build_lookup, zamgrh_to_english


TEST_CASES = [
    ("zambahz maz barg bra!nz", "Zombies must eat brains"),
    ("mah zambah bargz bra!nz", "I zombie eats brains"),
    ("harmanz bah! nah ma!g barragahz", "Humans are bad do not make barricades"),
    ("bah harman, nah bang bang mah zambah", "Bad human do not shoot shoot I zombie"),
    ("g!b bra!nz, harman", "Give brains human"),
    ("mah gang habbah zambahz", "I group happy zombies"),
    ("bangbangman nah bang bang mah zambah", "Headhunter do not shoot shoot I zombie"),
    ("zambahz zmazh barragahz", "Zombies smash barricades"),
    ("narz! mah zambah maz hab bra!n zarram!", "Nurse I zombie must have brain serum"),
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
            failed += 1

    print("\n---")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")

    return failed == 0


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
