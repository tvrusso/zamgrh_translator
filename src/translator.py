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
    word = word.lower()

    # remove leading punctuation (keep ! if internal)
    word = re.sub(r'^[^\w!]+', '', word)

    # remove trailing punctuation INCLUDING !
    word = re.sub(r'[^\w]+$', '', word)

    return word

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

def grammar_postprocess(text):
    COMMON_VERBS = {"eat", "eats", "make", "shoot", "have", "give", "smash", "must"}
    COMMON_NOUNS = {
        "human", "brains", "brain", "zombie", "group",
        "barricades", "headhunter"
    }

    words = text.split()

    result = []
    i = 0

    while i < len(words):
        w = words[i]

        # Rule 1: noun + adjective → insert "are"
        if i > 0:
            prev = result[-1] if result else ""

            if prev.endswith("s"):  # likely plural noun
                if w not in COMMON_VERBS and w not in COMMON_NOUNS and w != "not":
                    if not w.endswith("s"):
                        result.append("are")

        # Rule 2: "not <verb>" → "do not <verb>"
        if w == "not" and i + 1 < len(words):
            result.append("do")
            result.append("not")
            i += 1
            result.append(words[i])
            i += 1
            continue

        result.append(w)
        i += 1

    # Capitalize first word
    if result:
        result[0] = result[0].capitalize()

    return " ".join(result)

# --- updated translator ---
# NOTE: POS (including "conj") is currently not used in translation logic,
# but is preserved for future grammar-layer improvements.

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

    sentence = " ".join(out)
    sentence = grammar_postprocess(sentence)
    return sentence


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
