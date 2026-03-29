import json
import re
from pathlib import Path

DATA_PATH = Path(__file__).parent.parent / "data" / "zamgrh_dictionary.json"

def load_dictionary():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def build_lookup(data):
    lookup = {}
    for entry in data:
        key = normalize_token(clean(entry["word"]))
        lookup[key] = entry
    return lookup

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
        ("fix_am_progressive", fix_am_progressive),
        ("fix_verb_agreement", fix_verb_agreement),
    ]

    if debug:
        print(f"[INPUT]        {' '.join(words)}")

    for name, step in PIPELINE:
        words = step(words, lookup, eng_lookup)
        if debug:
            print(f"[{name:<16}] {' '.join(words)}")

    return words

def question_postprocess(text, structure, original_text):
    stripped = original_text.strip()

    if not stripped.endswith("?"):
        return text

    words = text.split()
    if not words:
        return text

    # existential question: "is there ..."
    if len(words) >= 3 and words[0].lower() == "is" and "there" in words:
        return " ".join(words[:-1]) + ("?" if not text.endswith("?") else "")

    subject = structure.get("subject")
    verb = structure.get("verb")
    obj = structure.get("object")

    # simple yes/no question: "Zombie eats brains" -> "Does the zombie eat brains?"
    if subject and verb:
        subject_text = f"the {subject}" if not subject.endswith("s") else f"the {subject}"
        if subject.endswith("s"):
            return f"Do {subject_text} {verb} {obj}?".replace(" None", "")
        return f"Does {subject_text} {verb} {obj}?".replace(" None", "")

    return text if text.endswith("?") else text + "?"

def fix_am_progressive(words, lookup, eng_lookup):
    result = []
    i = 0

    while i < len(words):
        w = words[i]

        if w == "I" and i + 2 < len(words):
            if words[i + 1] == "going" and words[i + 2] == "to":
                result.append("I")
                result.append("am")
                i += 1
                continue

        result.append(w)
        i += 1

    return result

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

        if "verb" in pos or "aux" in pos:
            if i > 0:
                prev = result[-1]
                prev_pos = get_pos(prev, lookup, eng_lookup)

                is_sentence_start = (i == 1)
                is_prev_noun = "noun" in prev_pos

                # repeated bare verbs: "eat eat eat"
                if "verb" in prev_pos or "aux" in prev_pos:
                    result.append(w)
                    continue

                # vocative + imperative, e.g. "Nurse give serum"
                if is_sentence_start and is_prev_noun and w not in {"is", "are", "am"}:
                    result.append(w)
                    continue

                is_subject_noun = "noun" in prev_pos
                is_plural_subject = prev.endswith("s") or prev in {"you", "we", "they"}
                is_singular_subject = is_subject_noun and not prev.endswith("s")

                if i > 1:
                    prev2 = result[-2]
                    prev2_pos = get_pos(prev2, lookup, eng_lookup)
                else:
                    prev2_pos = set()

                has_aux = ("aux" in prev2_pos) or prev in {"must", "will", "can", "should"}

                # special-case copula
                if w in {"is", "are", "am"}:
                    if prev == "I":
                        w = "am"
                    elif is_plural_subject:
                        w = "are"
                    else:
                        w = "is"

                    result.append(w)
                    continue

                if not has_aux:
                    if is_singular_subject:
                        if not w.endswith("s"):
                            if w.endswith("y"):
                                w = w[:-1] + "ies"
                            elif w.endswith(("s", "sh", "ch", "x", "z", "o")):
                                w = w + "es"
                            else:
                                w = w + "s"
                    else:
                        if w.endswith("ies"):
                            w = w[:-3] + "y"
                        elif (
                            w.endswith("es")
                            and len(w) > 2
                            and w[:-2].endswith(("s", "sh", "ch", "x", "z", "o"))
                        ):
                            w = w[:-2]
                        elif w.endswith("s") and w not in {"is"}:
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
    consumed_object = False

    for i, w in enumerate(words):
        pos = get_pos(w, lookup, eng_lookup)

        is_noun = "noun" in pos
        is_verb = "verb" in pos or "aux" in pos

        if is_verb:
            seen_verb = True
            consumed_object = False

        should_article_after_to = (
            is_noun
            and i > 0
            and result[-1] == "to"
            and not is_verb            
            and not w.endswith("s")
        )

        if (is_noun and not is_verb and seen_verb and not consumed_object) or should_article_after_to:
            is_plural = w.endswith("s")

            if not is_plural:
                if i > 0:
                    prev = result[-1]

                    if prev in {"a", "an", "the", "my", "your", "his", "her", "our", "their"}:
                        result.append(w)
                        consumed_object = True
                        continue

                    # don't insert article before verbs after "to"
                    if prev == "to" and not is_noun:
                        result.append(w)
                        consumed_object = True
                        continue

                article = "an" if w[0].lower() in "aeiou" else "a"
                result.append(article)

            consumed_object = True

        result.append(w)

    return result

# --- normalization helpers ---

def clean(word):
    word = word.lower()

    # strip leading non-word chars, but keep internal !
    word = re.sub(r'^[^\w!]+', '', word)

    # strip trailing punctuation, including ? . , ; : !
    while word and not (word[-1].isalnum() or word[-1] == "!"):
        word = word[:-1]

    # if the word ends with ! as punctuation rather than internal spelling, drop it
    if word.endswith("!") and not re.search(r'![a-z0-9]', word):
        word = word[:-1]

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

TRAILING_PUNCT = ".,?!:;"

def normalize_token(token: str) -> str:
    token = token.lower().strip()
    token = token.strip(TRAILING_PUNCT)
    return token

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

def pick_gloss(entry, desired_pos=None):
    english = entry.get("english", [])
    if not english:
        return None

    if desired_pos is None:
        return english[0]["gloss"]

    entry_pos = set(entry.get("pos", []))

    if desired_pos in entry_pos:
        for sense in english:
            gloss = sense.get("gloss")
            if gloss:
                return gloss

    return english[0]["gloss"]

def infer_desired_pos(words, i, translated_out):
    if i == 0:
        return None

    prev = translated_out[-1].lower() if translated_out else ""

    if prev in {"i", "you", "we", "they", "he", "she"}:
        return "verb"

    if prev in {"the", "a", "an", "my", "your", "our", "their", "this", "that"}:
        return "noun"

    if prev in {"must", "will", "can", "should"}:
        return "verb"

    if len(translated_out) >= 2 and translated_out[-2:].copy() == ["going", "to"]:
        return "verb"

    return None

def zamgrh_to_english(text, lookup, eng_lookup, debug=False):
    is_question = text.strip().endswith("?")

    words = text.split()
    out = []

    for raw in words:
        w = normalize_token(clean(raw))

        entry = lookup.get(w)
        if entry:
            base = w
            modifier = None
        else:
            base, modifier = normalize(w, lookup)
            entry = lookup.get(base)

        if entry:
            gloss = entry["english"][0]["gloss"]
            if modifier == "plural":
                gloss = gloss + "s"
            out.append(gloss)
        else:
            out.append(f"[{w}]")

    sentence = " ".join(out)
    words = sentence.split()
    words = apply_grammar_pipeline(words, lookup, eng_lookup, debug=debug)
    sentence = " ".join(words)
    sentence = grammar_postprocess(sentence, debug=debug)

    if is_question and sentence and not sentence.endswith("?"):
        sentence += "?"

    return sentence

# Early attempt to parse out Zamgrh sentences into a structure
# does nothing with the structure yet
def zamgrh_to_structure(text, lookup):
    words = text.split()

    structure = {
        "subject": None,
        "verb": None,
        "object": None,
        "plural": False,
        "negated": False,
        "imperative": False,
    }

    tokens = []

    # --- normalize + map to base + POS ---
    for raw in words:
        w = clean(raw)

        entry = lookup.get(w)
        if entry:
            base = w
            modifier = None
        else:
            base, modifier = normalize(w, lookup)
            entry = lookup.get(base)

        if entry:
            gloss = entry["english"][0]["gloss"]
            pos = set(entry.get("pos", []))
        else:
            gloss = w
            pos = set()

        tokens.append({
            "raw": raw,
            "word": gloss,
            "base": base,
            "pos": pos,
            "modifier": modifier
        })

    # --- detect negation ---
    for t in tokens:
        if t["base"] == "nah":
            structure["negated"] = True

    # --- find verb (first verb) ---
    for t in tokens:
        if "verb" in t["pos"]:
            structure["verb"] = t["word"]
            break

    # --- find subject (first noun before verb) ---
    for t in tokens:
        if t["word"] == structure["verb"]:
            break
        if "noun" in t["pos"]:
            structure["subject"] = t["word"]
            if t["modifier"] == "plural" or t["word"].endswith("s"):
                structure["plural"] = True
            break

    # --- detect imperative (no subject before verb) ---
    if structure["verb"] and not structure["subject"]:
        structure["imperative"] = True

    # --- find object (first noun after verb) ---
    seen_verb = False
    for t in tokens:
        if t["word"] == structure["verb"]:
            seen_verb = True
            continue
        if seen_verb and "noun" in t["pos"]:
            structure["object"] = t["word"]
            break

    return structure

def main():
    data = load_dictionary()
    lookup = build_lookup(data)
    eng_lookup = build_english_pos_lookup(data)

    while True:
        try:
            text = input("Zamgrh> ")
        except EOFError:
            print("\nExiting translator.")
            break
        except KeyboardInterrupt:
            print("\nExiting translator.")
            break

        if not text.strip():
            continue

        if text.strip().lower() == "quit":
            print("Exiting translator.")
            break

        print(zamgrh_to_english(text, lookup, eng_lookup))
        print(zamgrh_to_structure(text, lookup))

if __name__ == "__main__":
    main()
