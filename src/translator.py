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


AUX_WORDS = {"must", "will", "can", "should", "have", "has", "had", "am", "is", "are", "do", "does"}
SUBJECT_PRONOUNS = {"he", "she", "it"}
NON_THIRD_PERSON_PRONOUNS = {"I", "you", "we", "they"}
VERB_LIKE_WORDS = {"eat", "give", "go", "smash", "speak", "come", "run", "have", "is", "are", "am"}
DETERMINERS = {"a", "an", "the", "my", "your", "his", "her", "our", "their"}

COLLAPSIBLE_WORDS = {
    "must", "will", "can", "should", "have",
    "is", "are", "am",
    "the", "a", "an",
}


# translation pipeline
def apply_grammar_pipeline(words, lookup, eng_lookup, debug=False):
    PIPELINE = [
        ("resolve_hab", resolve_hab_ambiguity),
        ("simplify_subject", simplify_subject),
        ("fix_possession", fix_possession),
        ("fix_pronouns", fix_object_pronouns),
        ("collapse_repeated_pronouns", collapse_repeated_pronouns),
        ("fix_determiners", fix_determiners),
        ("fix_prepositions", fix_prepositions),
        ("insert_copula", insert_copula),
        ("insert_articles", insert_articles),
        ("dedupe_function_words", dedupe_function_words),
        ("fix_am_progressive", fix_am_progressive),
        ("fix_verb_agreement", fix_verb_agreement),
    ]

    if debug:
        print(f"[INPUT]        {' '.join(words)}")

    for name, step in PIPELINE:
        words = step(words, lookup, eng_lookup)
        if debug:
            print(f"[{name:<24}] {' '.join(words)}")

    return words


def question_postprocess(text, structure, original_text):
    stripped = original_text.strip()
    if not stripped.endswith("?"):
        return text

    words = text.split()
    if not words:
        return text

    if len(words) >= 3 and words[0].lower() == "is" and "there" in words:
        return " ".join(words[:-1]) + ("?" if not text.endswith("?") else "")

    subject = structure.get("subject")
    verb = structure.get("verb")
    obj = structure.get("object")

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

        if w == "help":
            if i > 0 and words[i - 1] in {"I", "zombie"}:
                result.append("have")
                i += 1
                continue
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
    verbs = {"give", "help", "shoot", "eat", "smash", "have"}
    result = []
    for i, w in enumerate(words):
        if w == "I" and i > 0 and words[i - 1] in verbs:
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
        prev = result[-1] if result else None
        prev_pos = get_pos(prev, lookup, eng_lookup) if prev else set()

        # handle copula first
        if w in {"is", "are", "am"}:
            if prev == "I":
                w = "am"
            elif prev and (prev.endswith("s") or prev in {"you", "we", "they"}):
                w = "are"
            else:
                w = "is"
            result.append(w)
            continue

        # auxiliaries never inflect
        if w in AUX_WORDS or "aux" in pos:
            result.append(w)
            continue

        if "verb" in pos:
            has_subject = False
            is_third_person = False

            if prev:
                prev_is_verb_like = (
                    ("verb" in prev_pos) or
                    ("aux" in prev_pos) or
                    (prev in AUX_WORDS)
                )

                # only allow subject detection if previous word is not verb-like
                if not prev_is_verb_like:
                    if "noun" in prev_pos:
                        has_subject = True
                        is_third_person = not prev.endswith("s")
                    elif prev in {"he", "she", "it"}:
                        has_subject = True
                        is_third_person = True
                    elif prev in {"I", "you", "we", "they"}:
                        has_subject = True
                        is_third_person = False

            if i > 1:
                prev2 = result[-2]
                prev2_pos = get_pos(prev2, lookup, eng_lookup)
            else:
                prev2 = None
                prev2_pos = set()

            has_aux = (
                ("aux" in prev2_pos) or
                (prev in AUX_WORDS if prev else False)
            )

            if has_subject and not has_aux:
                if is_third_person:
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
                    elif w.endswith("es") and w[:-2].endswith(("s", "sh", "ch", "x", "z", "o")):
                        w = w[:-2]
                    elif w.endswith("s"):
                        w = w[:-1]

        result.append(w)

    return result


def dedupe_function_words(words, lookup, eng_lookup):
    result = []
    prev = None
    for w in words:
        if w == prev and w in COLLAPSIBLE_WORDS:
            continue
        result.append(w)
        prev = w
    return result


def normalize_morphology(word, lookup):
    if word in lookup:
        return word, {}

    if word.endswith("z") and len(word) > 1:
        base = word[:-1]
        entry = lookup.get(base)

        if entry:
            pos = set(entry.get("pos", []))

            if "noun" in pos:
                return base, {"number": "plural", "pos_family": "noun"}

            if "pron" in pos:
                return base, {"number": "plural", "pos_family": "pron"}

            return base, {}

    return word, {}

# Helpers for dictionary-driven POS logic
def get_pos(word, lookup, eng_lookup):
    if not word:
        return set()

    word = word.lower()

    # 1. direct zamgrh lookup
    entry = lookup.get(word)
    if entry:
        return set(entry.get("pos", []))

    # 2. direct english gloss
    if word in eng_lookup:
        return eng_lookup[word]

    # 3. english plural fallback
    if word.endswith("s"):
        base = word[:-1]
        if base in eng_lookup:
            return eng_lookup[base]

    # 4. morphology fallback for zamgrh
    base, _features = normalize_morphology(word, lookup)
    if base != word:
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
        is_pure_noun = is_noun and not is_verb and w not in AUX_WORDS and w not in VERB_LIKE_WORDS

        nxt = words[i + 1] if i + 1 < len(words) else None
        nxt_pos = get_pos(nxt, lookup, eng_lookup) if nxt else set()
        next_is_noun = nxt is not None and "noun" in nxt_pos and "verb" not in nxt_pos and "aux" not in nxt_pos

        if is_verb or w in AUX_WORDS or w in VERB_LIKE_WORDS:
            seen_verb = True
            consumed_object = False
            result.append(w)
            continue

        should_article_after_to = (
            is_pure_noun
            and i > 0
            and result[-1] == "to"
            and not w.endswith("s")
            and not next_is_noun
        )

        should_article_as_object = (
            is_pure_noun
            and seen_verb
            and not consumed_object
            and not next_is_noun
        )

        if should_article_as_object or should_article_after_to:
            is_plural = w.endswith("s")
            prev = result[-1] if result else None

            if not is_plural and prev not in DETERMINERS:
                article = "an" if w[0].lower() in "aeiou" else "a"
                result.append(article)

            consumed_object = True

        result.append(w)

    return result


def fix_determiners(words, lookup, eng_lookup):
    result = []

    for i, w in enumerate(words):
        if w == "I":
            nxt = words[i + 1] if i + 1 < len(words) else None
            nxt2 = words[i + 2] if i + 2 < len(words) else None

            nxt_pos = get_pos(nxt, lookup, eng_lookup) if nxt else set()
            nxt2_pos = get_pos(nxt2, lookup, eng_lookup) if nxt2 else set()

            # Keep "I" when it is acting like a subject:
            #   I eat brains
            #   not I eat brains
            if nxt and (
                "verb" in nxt_pos
                or "aux" in nxt_pos
                or nxt in AUX_WORDS
                or nxt in VERB_LIKE_WORDS
            ):
                result.append(w)
                continue

            # Convert to "my" only in clearly possessive environments:
            #   I brains -> my brains
            # but not when that noun is really part of a subject phrase
            if nxt and "noun" in nxt_pos:
                if nxt2 and (
                    "verb" in nxt2_pos
                    or "aux" in nxt2_pos
                    or nxt2 in AUX_WORDS
                    or nxt2 in VERB_LIKE_WORDS
                ):
                    result.append(w)
                    continue

                result.append("my")
                continue

        result.append(w)

    return result


def collapse_repeated_pronouns(words, lookup, eng_lookup):
    result = []
    prev = None
    for w in words:
        if w == prev and w in {"I", "me"}:
            continue
        result.append(w)
        prev = w
    return result


# --- normalization helpers ---
def clean(word):
    word = word.lower()
    # remove leading punctuation (keep ! if internal)
    word = re.sub(r"^[^\w!]+", "", word)
    # remove trailing punctuation INCLUDING !
    word = re.sub(r"[^\w]+$", "", word)
    return word


def grammar_postprocess(text, debug=False):
    words = text.split()
    result = []
    i = 0

    while i < len(words):
        w = words[i]

        # Rule: "not" -> "do not"
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


def run_structure_tests():
    data = load_dictionary()
    lookup = build_lookup(data)

    passed = 0
    failed = 0

    for group, cases in STRUCTURE_TESTS.items():
        print(f"\n=== STRUCTURE: {group.upper()} ===")
        for zamgrh, expected in cases:
            result = zamgrh_to_structure(zamgrh, lookup)

            if result == expected:
                print(f"PASS: {zamgrh}")
                passed += 1
            else:
                print(f"FAIL: {zamgrh}")
                print(f"  expected: {expected}")
                print(f"  got:      {result}")
                failed += 1

    print("\n---")
    print(f"Structure Passed: {passed}")
    print(f"Structure Failed: {failed}")
    return failed == 0

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

def render_gloss_with_features(gloss, features, pos):
    if features.get("number") == "plural":
        if gloss == "you" and "pron" in pos:
            return "yous"
        return gloss + "s"
    return gloss

def zamgrh_to_english(text, lookup, eng_lookup, debug=False):
    is_question = text.strip().endswith("?")
    words = text.split()
    out = []

    for raw in words:
        w = clean(raw)
        base, features = normalize_morphology(w, lookup)
        entry = lookup.get(base)

        if entry:
            gloss = entry["english"][0]["gloss"]
            pos = set(entry.get("pos", []))
            gloss = render_gloss_with_features(gloss, features, pos)
            out.append(gloss)
        else:
            out.append(f"[{raw}]")

    sentence = " ".join(out)
    words = sentence.split()
    words = apply_grammar_pipeline(words, lookup, eng_lookup, debug=debug)
    sentence = " ".join(words)
    sentence = grammar_postprocess(sentence, debug=debug)

    if is_question and sentence and not sentence.endswith("?"):
        sentence += "?"

    return sentence

def is_plural_subject_token(word, features):
    if features.get("number") == "plural":
        return True
    return word in {"we", "they"}

SUBJECT_PRONOUNS = {"I", "you", "he", "she", "it", "we", "they"}

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
    prev_gloss = None

    for raw in words:
        w = clean(raw)
        base, features = normalize_morphology(w, lookup)
        entry = lookup.get(base)

        if entry:
            gloss = entry["english"][0]["gloss"]
            pos = set(entry.get("pos", []))
        else:
            gloss = w
            pos = set()

        # mirror simplify_subject behavior:
        # "I zombie" -> treat as just "I"
        if gloss == "zombie" and prev_gloss == "I":
            continue

        tokens.append({
            "raw": raw,
            "word": gloss,
            "base": base,
            "pos": pos,
            "features": features,
        })

        prev_gloss = gloss

    for t in tokens:
        if t["base"] == "nah":
            structure["negated"] = True

    for t in tokens:
        if "verb" in t["pos"]:
            structure["verb"] = t["word"]
            break

    has_explicit_subject = False
    
    for t in tokens:
        if t["word"] == structure["verb"]:
            break

        if t["word"] in SUBJECT_PRONOUNS:
            structure["subject"] = t["word"]
            has_explicit_subject = True

            if t["word"] in {"we", "they"}:
                structure["plural"] = True
            elif t["word"] == "you" and t["features"].get("number") == "plural":
                structure["plural"] = True

            break

        if "noun" in t["pos"]:
            structure["subject"] = t["word"]
            has_explicit_subject = True

            if t["features"].get("number") == "plural" or t["word"].endswith("s"):
                structure["plural"] = True

            break

    if structure["verb"] and not has_explicit_subject:
        structure["imperative"] = True

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
    success_translation = run_tests()
    success_structure = run_structure_tests()
    sys.exit(0 if (success_translation and success_structure) else 1)