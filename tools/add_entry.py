import json
import os

DICTIONARY_PATH = "zamgrh_dictionary.json"
VALIDATOR_PATH = "validate_dictionary.py"  # optional


def load_dictionary():
    if not os.path.exists(DICTIONARY_PATH):
        return []
    with open(DICTIONARY_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_dictionary(data, pretty=True):
    with open(DICTIONARY_PATH, "w", encoding="utf-8") as f:
        if pretty:
            json.dump(data, f, indent=2, ensure_ascii=False)
        else:
            json.dump(data, f)


def word_exists(data, word):
    return any(entry["word"] == word for entry in data)


def prompt_list(prompt):
    raw = input(prompt).strip()
    return [x.strip() for x in raw.split(",") if x.strip()]


def prompt_glosses():
    glosses = []
    while True:
        gloss = input("Gloss (leave empty to finish): ").strip()
        if not gloss:
            break
        weight_input = input("Weight (default 1.0): ").strip()
        weight = float(weight_input) if weight_input else 1.0
        glosses.append({"gloss": gloss, "weight": weight})
    return glosses


def run_validator():
    if not os.path.exists(VALIDATOR_PATH):
        print("⚠️ Validator not found, skipping...")
        return

    print("\nRunning validator...")
    exit_code = os.system(f"python {VALIDATOR_PATH}")
    if exit_code != 0:
        print("❌ Validator reported errors!")
    else:
        print("✅ Validator passed!")


def main():
    data = load_dictionary()

    print("=== Add Dictionary Entry ===")

    word = input("Word: ").strip()
    if not word:
        print("❌ Word cannot be empty.")
        return

    if word_exists(data, word):
        print(f"⚠️ Word '{word}' already exists. Aborting.")
        return

    pos = prompt_list("Parts of speech (comma separated): ")
    if not pos:
        print("❌ At least one part of speech required.")
        return

    print("\nEnter glosses:")
    english = prompt_glosses()
    if not english:
        print("❌ At least one gloss required.")
        return

    confidence_input = input("Confidence (default 1.0): ").strip()
    confidence = float(confidence_input) if confidence_input else 1.0

    new_entry = {
        "word": word,
        "pos": pos,
        "english": english,
        "confidence": confidence
    }

    print("\nPreview entry:")
    print(json.dumps(new_entry, indent=2, ensure_ascii=False))

    confirm = input("\nSave this entry? (y/n): ").lower()
    if confirm != "y":
        print("❌ Aborted.")
        return

    data.append(new_entry)

    pretty = input("Pretty-print JSON? (y/n, default y): ").lower() != "n"
    save_dictionary(data, pretty=pretty)

    print("✅ Entry added successfully!")

    run_val = input("Run validator now? (y/n): ").lower()
    if run_val == "y":
        run_validator()


if __name__ == "__main__":
    main()
