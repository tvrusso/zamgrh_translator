import subprocess
import sys

CHECKS = [
    ("Translator tests", ["python", "tests/test_translator.py"]),
    ("Dictionary validation", ["python", "src/validate_dictionary.py"]),
    ("Dictionary audit", ["python", "tests/audit_dictionary_vs_tests.py"]),
]

def run_check(name, cmd):
    print(f"\n=== Running: {name} ===")
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print(f"❌ FAILED: {name}")
        return False
    print(f"✅ PASSED: {name}")
    return True

def main():
    all_passed = True
    for name, cmd in CHECKS:
        if not run_check(name, cmd):
            all_passed = False

    if not all_passed:
        print("\n🚫 Merge blocked: One or more checks failed.")
        sys.exit(1)

    print("\n🎉 All checks passed. Safe to merge.")

if __name__ == "__main__":
    main()
