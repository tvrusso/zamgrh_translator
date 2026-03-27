import json
from pathlib import Path

DATA_PATH = Path(__file__).parent.parent / "data" / "zamgrh_dictionary.json"


def load_dictionary():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def build_lookup(data):
    return {entry["word"]: entry for entry in data}


def zamgrh_to_english(text, lookup):
    words = text.lower().split()
    out = []

    for w in words:
        entry = lookup.get(w)
        if entry:
            out.append(entry["english"][0]["gloss"])
        else:
            out.append(f"[{w}]")

    return " ".join(out)


def main():
    data = load_dictionary()
    lookup = build_lookup(data)

    while True:
        text = input("Zamgrh> ")
        if text == "quit":
            break
        print(zamgrh_to_english(text, lookup))


if __name__ == "__main__":
    main()
