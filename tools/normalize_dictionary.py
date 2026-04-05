import json
from pathlib import Path

DATA_PATH = Path(__file__).parent.parent / "data" / "zamgrh_dictionary.json"


def load_dictionary(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_dictionary(path: Path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")  # newline at EOF


def normalize_word(entry):
    word = entry.get("word")
    if isinstance(word, str):
        entry["word"] = word.strip()


def normalize_pos(entry):
    pos = entry.get("pos")
    if isinstance(pos, list):
        entry["pos"] = [p.strip() for p in pos if isinstance(p, str)]


def normalize_english(entry):
    english = entry.get("english")
    if not isinstance(english, list):
        return

    new_english = []
    for gloss_entry in english:
        if not isinstance(gloss_entry, dict):
            continue

        gloss = gloss_entry.get("gloss")
        if isinstance(gloss, str):
            gloss = gloss.strip()

        new_entry = {"gloss": gloss}

        weight = gloss_entry.get("weight")
        if isinstance(weight, (int, float)):
            new_entry["weight"] = weight

        new_english.append(new_entry)

    # If multiple glosses and none have weights → assign equal weights
    if len(new_english) > 1:
        has_weight = any("weight" in g for g in new_english)
        if not has_weight:
            equal_weight = round(1.0 / len(new_english), 3)
            for g in new_english:
                g["weight"] = equal_weight

    entry["english"] = new_english


def normalize_entry(entry):
    if not isinstance(entry, dict):
        return entry

    normalize_word(entry)
    normalize_pos(entry)
    normalize_english(entry)

    return entry


def sort_dictionary(data):
    return sorted(data, key=lambda e: e.get("word", "").lower())


def main():
    data = load_dictionary(DATA_PATH)

    # Normalize entries
    normalized = [normalize_entry(entry) for entry in data]

    # Sort alphabetically by word
    normalized = sort_dictionary(normalized)

    save_dictionary(DATA_PATH, normalized)

    print("Normalization complete.")
    print(f"Entries processed: {len(normalized)}")


if __name__ == "__main__":
    main()
