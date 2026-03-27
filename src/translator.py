import json
import re
from pathlib import Path

DATA_PATH = Path(__file__).parent.parent / "data" / "zamgrh_dictionary.json"


def load_dictionary():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def build_lookup(data):
    return {entry["word"]: entry for entry in data}

def build_english_pos_lookup(data):
    eng_lookup = {}
    for entry in data:
        pos = set(entry.get("pos", []))
        for e in entry.get("english", []):
            gloss = e["gloss"]
            eng_lookup.setdefault(gloss, set()).update(pos)
    return eng_lookup

# translation pipeline
def apply_grammar_pipeline(words, lookup, eng_lookup, debug=False):
    PIPELINE = [
        ("resolve_hab", resolve_hab_ambiguity),
        ("simplify_subject", simplify_subject),
        ("fix_possession", fix_possession),
        ("fix_pronouns", fix_object_pronouns),
        ("fix_prepositions", fix_prepositions),
        ("insert_copula", insert_copula),
        ("insert_articles", insert_articles),
        ("fix_verb_agreement", fix_verb_agreement),
    ]

    if debug:
        print(f"[INPUT]        {' '.join(words)}")

    for name, step in PIPELINE:
        words = step(words, lookup, eng_lookup)

        if debug:
            print(f"[{name:<14}] {' '.join(words)}")

    return words

def resolve_hab_ambiguity(words, lookup, eng_lookup):
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

def simplify_subject(words, lookup, eng_lookup):
    result = []
    i = 0

    while i < len(words):
        if i > 0 and words[i] == "zombie" and words[i - 1] == "I":
            i += 1
            continue

        result.append(words[i])
        i += 1

    return result

def fix_possession(words, lookup, eng_lookup):
    result = []

    for i, w in enumerate(words):
        if w == "I" and i + 1 < len(words):
            if words[i + 1] in {"group", "gang"}:
                result.append("my")
                continue

        result.append(w)

    return result

def fix_object_pronouns(words, lookup, eng_lookup):
    VERBS = {"give", "help", "shoot", "eat", "smash", "have"}

    result = []

    for i, w in enumerate(words):
        if w == "I" and i > 0 and words[i - 1] in VERBS:
            result.append("me")
        else:
            result.append(w)

    return result

def insert_copula(words, lookup, eng_lookup):
    result = []
    seen_verb = False

    for i, w in enumerate(words):
        pos = get_pos(w, lookup, eng_lookup)

        if "verb" in pos or "aux" in pos:
            seen_verb = True

        if i > 0:
            prev = result[-1]
            prev_pos = get_pos(prev, lookup, eng_lookup)

            is_noun = "noun" in prev_pos
            is_adj = "adj" in pos
            is_unknown = w.startswith("[")

            if not seen_verb and is_noun and is_adj and not is_unknown:
                # decide is vs are
                if prev.endswith("s"):
                    result.append("are")
                else:
                    result.append("is")

        result.append(w)

    return result

def fix_prepositions(words, lookup, eng_lookup):
    result = []
    for i, w in enumerate(words):
        if w == "I" and i > 0 and words[i - 1] == "to":
            result.append("me")
        else:
            result.append(w)
    return result

def fix_verb_agreement(words, lookup, eng_lookup):
    result = []

    for i, w in enumerate(words):
        pos = get_pos(w, lookup, eng_lookup)

        if "verb" in pos:
            if i > 0:
                prev = result[-1]
                prev_pos = get_pos(prev, lookup, eng_lookup)

                # --- NEW: detect imperative (vocative + verb)
                is_sentence_start = (i == 1)
                is_prev_noun = "noun" in prev_pos

                if is_sentence_start and is_prev_noun:
                    # treat as imperative → do NOT change verb
                    result.append(w)
                    continue

                is_subject_noun = "noun" in prev_pos
                is_pronoun = prev in {"I", "you", "we", "they"}
                is_third_person = is_subject_noun and not prev.endswith("s")

                # check for auxiliaries
                if i > 1:
                    prev2 = result[-2]
                    prev2_pos = get_pos(prev2, lookup, eng_lookup)
                else:
                    prev2 = None
                    prev2_pos = set()

                has_aux = (
                    ("aux" in prev2_pos) or
                    prev in {"must", "will", "can", "should"}
                )

                if not has_aux:
                    # --- CASE 1: 3rd person singular → ADD "s"
                    if is_third_person:
                        if not w.endswith("s"):
                            if w.endswith("y"):
                                w = w[:-1] + "ies"
                            elif w.endswith(("s", "sh", "ch", "x", "z", "o")):
                                w = w + "es"
                            else:
                                w = w + "s"

                    # --- CASE 2: NOT 3rd person → REMOVE "s"
                    else:
                        if w.endswith("s"):
                            # simple rollback rules
                            if w.endswith("ies"):
                                w = w[:-3] + "y"
                            elif w.endswith("es"):
                                w = w[:-2]
                            else:
                                w = w[:-1]

        result.append(w)

    return result

# Helpers for dictionary-driven POS logic
def get_pos(word, lookup, eng_lookup):
    word = word.lower()

    # 1. direct zamgrh lookup
    entry = lookup.get(word)
    if entry:
        return set(entry.get("pos", []))

    # 2. direct english gloss
    if word in eng_lookup:
        return eng_lookup[word]

    # 3. plural fallback
    if word.endswith("s"):
        base = word[:-1]

        # try english lookup
        if base in eng_lookup:
            return eng_lookup[base]

        # ALSO try zamgrh reverse mapping
        entry = lookup.get(base)
        if entry:
            return set(entry.get("pos", []))

    return set()

def insert_articles(words, lookup, eng_lookup):
    result = []
    seen_verb = False
    consumed_object = False  # NEW

    for i, w in enumerate(words):
        pos = get_pos(w, lookup, eng_lookup)

        is_noun = "noun" in pos
        is_verb = "verb" in pos or "aux" in pos

        if is_verb:
            seen_verb = True
            consumed_object = False  # reset for new verb

        if is_noun and not is_verb and seen_verb and not consumed_object:
            is_plural = w.endswith("s")

            if not is_plural:
                if i > 0:
                    prev = result[-1]

                    if prev in {"a", "an", "the", "my", "your", "his", "her", "our", "their"}:
                        result.append(w)
                        consumed_object = True
                        continue

                    if prev in {"to"}:
                        result.append(w)
                        consumed_object = True
                        continue

                article = "an" if w[0] in "aeiou" else "a"
                result.append(article)

            consumed_object = True  # ✅ only first noun gets article

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

def zamgrh_to_english(text, lookup, eng_lookup, debug=False):
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

    words = apply_grammar_pipeline(words, lookup, eng_lookup, debug=debug)

    sentence = " ".join(words)
    sentence = grammar_postprocess(sentence, debug=debug)

    return sentence

def main():
    data = load_dictionary()
    lookup = build_lookup(data)
    eng_lookup = build_english_pos_lookup(data)
    while True:
        text = input("Zamgrh> ")
        if text == "quit":
            break
        print(zamgrh_to_english(text, lookup, eng_lookup))


if __name__ == "__main__":
    main()
