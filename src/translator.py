import json
import re
from pathlib import Path

DATA_PATH = Path(__file__).parent.parent / "data" / "zamgrh_dictionary.json"


def load_dictionary():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def build_lookup(data):
    return {entry["word"]: entry for entry in data}

# translation pipeline
def apply_grammar_pipeline(words, debug=False):
    PIPELINE = [
        ("resolve_hab", resolve_hab_ambiguity),
        ("simplify_subject", simplify_subject),
        ("fix_possession", fix_possession),
        ("fix_pronouns", fix_object_pronouns),
        ("fix_prepositions", fix_prepositions),
        ("insert_are", insert_are),
    ]

    if debug:
        print(f"[INPUT]        {' '.join(words)}")

    for name, step in PIPELINE:
        words = step(words)

        if debug:
            print(f"[{name:<14}] {' '.join(words)}")

    return words

def resolve_hab_ambiguity(words):
    result = []
    i = 0
    while i < len(words):
        w = words[i]

        # default = help → upgrade to "have" in possession contexts
        if w == "help":
            # patterns like: "I help brains" → "I have brains"
            if i > 0 and words[i - 1] in {"I", "zombie"}:
                result.append("have")
                i += 1
                continue

            # "must help" → "must have"
            if i > 0 and words[i - 1] == "must":
                result.append("have")
                i += 1
                continue

        result.append(w)
        i += 1

    return result

def simplify_subject(words):
    result = []
    i = 0

    while i < len(words):
        if i > 0 and words[i] == "zombie" and words[i - 1] == "I":
            i += 1
            continue

        result.append(words[i])
        i += 1

    return result

def fix_possession(words):
    result = []

    for i, w in enumerate(words):
        if w == "I" and i + 1 < len(words):
            if words[i + 1] in {"group", "gang"}:
                result.append("my")
                continue

        result.append(w)

    return result

def fix_object_pronouns(words):
    VERBS = {"give", "help", "shoot", "eat", "smash", "have"}

    result = []

    for i, w in enumerate(words):
        if w == "I" and i > 0 and words[i - 1] in VERBS:
            result.append("me")
        else:
            result.append(w)

    return result

def insert_are(words):
    COMMON_VERBS = {"eat", "eats", "make", "shoot", "have", "give", "smash", "must", "help"}
    COMMON_NOUNS = {
        "human", "brains", "brain", "zombie", "group",
        "barricades", "headhunter"
    }
    COMMON_CONJUNCTIONS = {"or", "and"}
    
    result = []
    seen_verb = False

    for i, w in enumerate(words):
        # track if we've seen a verb already
        if w in COMMON_VERBS:
            seen_verb = True

        if i > 0:
            prev = result[-1]

            should_insert_are = (
                not seen_verb and
                prev.endswith("s") and
                w not in COMMON_VERBS and
                w not in COMMON_NOUNS and
                w not in COMMON_CONJUNCTIONS and
                w != "not" and
                not w.endswith("s") and
                not w.startswith("[")
            )

            if should_insert_are:
                result.append("are")

        result.append(w)

    return result

def fix_prepositions(words):
    result = []
    for i, w in enumerate(words):
        if w == "I" and i > 0 and words[i - 1] == "to":
            result.append("me")
        else:
            result.append(w)
    return result

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

def grammar_postprocess(text, debug=False):
    COMMON_VERBS = {"eat", "eats", "make", "shoot", "have", "give", "smash", "must"}
    COMMON_NOUNS = {
        "human", "brains", "brain", "zombie", "group",
        "barricades", "headhunter"
    }
    COMMON_CONJUNCTIONS = {"or", "and"}

    words = text.split()

    result = []
    i = 0

    while i < len(words):
        w = words[i]

        # Rule: "not" → "do not"
        if w == "not":
            result.append("do")
            result.append("not")
            i += 1
            continue

        result.append(w)
        i += 1

    if result:
        result[0] = result[0].capitalize()

    output = " ".join(result)

    if debug:
        print(f"[grammar]      {output}")

    return output

# --- updated translator ---
# NOTE: POS (including "conj") is currently not used in translation logic,
# but is preserved for future grammar-layer improvements.

def zamgrh_to_english(text, lookup, debug=False):
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
    words = sentence.split()

    words = apply_grammar_pipeline(words, debug=debug)

    sentence = " ".join(words)
    sentence = grammar_postprocess(sentence, debug=debug)

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
