import json
import sys
import re
from pathlib import Path

REQUIRED_FIELDS = {"word", "english"}


def normalize(word: str) -> str:
    word = word.lower().strip()
    word = re.sub(r'^[^\w!]+', '', word)
    while word and not (word[-1].isalnum() or word[-1] == "!"):
        word = word[:-1]
    if word.endswith("!") and not re.search(r'![a-z0-9]', word):
        word = word[:-1]
    return word


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def validate_entry(entry, index, source):
    if not isinstance(entry, dict):
        raise ValueError(f"{source}[{index}] is not an object")

    missing = REQUIRED_FIELDS - entry.keys()
    if missing:
        raise ValueError(f"{source}[{index}] missing fields: {missing}")

    if not isinstance(entry["word"], str):
        raise ValueError(f"{source}[{index}].word must be a string")

    if not isinstance(entry["english"], list):
        raise ValueError(f"{source}[{index}].english must be a list")

    for i, e in enumerate(entry["english"]):
        if "gloss" not in e:
            raise ValueError(f"{source}[{index}].english[{i}] missing 'gloss'")


def build_index(data, label):
    index = {}
    for i, entry in enumerate(data):
        validate_entry(entry, i, label)
        key = normalize(entry["word"])

        if key in index:
            print(f"⚠️ Duplicate in {label}: {key} (overwriting)")

        index[key] = entry
    return index


def merge(base_data, add_data):
    base_index = build_index(base_data, "base")
    add_index = build_index(add_data, "additions")

    for key, entry in add_index.items():
        if key in base_index:
            print(f"🔁 Overwriting existing entry: {key}")
        else:
            print(f"➕ Adding new entry: {key}")

        base_index[key] = entry

    return list(base_index.values())


def main():
    if len(sys.argv) != 4:
        print("Usage: python merge_json.py base.json additions.json output.json")
        sys.exit(1)

    base_path = Path(sys.argv[1])
    add_path = Path(sys.argv[2])
    out_path = Path(sys.argv[3])

    base_data = load_json(base_path)
    add_data = load_json(add_path)

    if not isinstance(base_data, list) or not isinstance(add_data, list):
        raise ValueError("Both files must contain a JSON list")

    merged = merge(base_data, add_data)

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Merge complete: {out_path}")


if __name__ == "__main__":
    main()
