import json
import re
from pathlib import Path

DATA_PATH = Path(__file__).parent.parent / "data" / "zamgrh_dictionary.json"


def load_dictionary():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def build_lookup(data):
    return {entry["word"]: entry for entry in data}


# --- NEW: normalization helpers ---

def clean(word):
    """Remove punctuation except ! (used in Zamgrh words)."""
    return re.sub(r'[^\w!]', '', word.lower())


def normalize(word, lookup):
    """
    Normalize simple morphology:
    - Only strip plural 'z' if the base word exists in dictionary
    """
    if word.endswith("z") and len(word) > 1:
        base = word[:-1]
        if base in lookup:
            return base, "plural"

    return word, None

# --- updated translator ---

def zamgrh_to_english(text, lookup):
    words = text.split()
    out = []

    for raw in words:
        w = clean(raw)

        # FIRST: try exact match
        entry = lookup.get(w)

        if entry:
            base = w
            modifier = None
        else:
            # THEN try normalization
            base, modifier = normalize(w, lookup)
            entry = lookup.get(base)

        if entry:
            gloss = entry["english"][0]["gloss"]

            # optional: mark plural (simple version)
            if modifier == "plural":
                gloss = gloss + "s"

            out.append(gloss)
        else:
            out.append(f"[{raw}]")

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
