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
SUBJECT_PRONOUNS = {"I", "you", "he", "she", "it", "we", "they"}
VERB_LIKE_WORDS = {"eat", "give", "go", "smash", "speak", "come", "run", "have", "is", "are", "am"}
DETERMINERS = {"a", "an", "the", "my", "your", "his", "her", "our", "their"}

SKIP_POS = {"adj", "adv", "det","prep",}
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
        context = build_context(w,result,lookup,eng_lookup)

        w, changed_word = handle_copula(context)
        if changed_word:
            result.append(w)
            continue

        w, changed_word = handle_auxiliary(context)
        if changed_word:
            result.append(w)
            continue

        w,changed_word = handle_main_verb(context)

        result.append(w)

    return result

# Utility functions for pipeline
def build_context(current_word, result, lookup, eng_lookup):
    pos = get_pos(current_word, lookup, eng_lookup)

    prev = result[-1] if result else None
    prev_pos = get_pos(prev, lookup, eng_lookup) if prev else set()

    prev2 = result[-2] if len(result) > 1 else None
    prev2_pos = get_pos(prev2, lookup, eng_lookup) if prev2 else set()

    return {
        "word": current_word,
        "pos": pos,
        "prev": prev,
        "prev_pos": prev_pos,
        "prev2": prev2,
        "prev2_pos": prev2_pos,
        "result_so_far": result,
        "lookup": lookup,
        "eng_lookup": eng_lookup,
    }

def find_subject_head(context):
    tokens = context["result_so_far"]
    lookup = context["lookup"]
    eng_lookup = context["eng_lookup"]

    idx = len(tokens) - 1
    candidate = None

    while idx >= 0:
        word = tokens[idx]
        pos = get_pos(word, lookup, eng_lookup)

        # --- normalize gerunds locally ---
        if len(pos) == 0 and word.endswith("ing"):
            pos = {"verb"}

        # --- STOP: auxiliary ---
        if "aux" in pos:
            return None

        # --- VERB boundary ---
        if "verb" in pos:
            if word.endswith("ing"):
                idx -= 1
                continue
            break  # stop scanning further left

        # --- skip irrelevant ---
        if pos & SKIP_POS:
            idx -= 1
            continue

        # --- record candidate (don't return yet!) ---
        if "noun" in pos or word in SUBJECT_PRONOUNS:
            candidate = word

        idx -= 1

    return candidate

# fix_verb_agreement helper functions
def handle_copula(context):
    current_word = context["word"]
    previous_word= context["prev"]

    if current_word in {"is", "are", "am"}:
        if previous_word == "I":
            return "am", True
        elif previous_word and (previous_word.endswith("s") or
                                previous_word in {"you", "we", "they"}):
            return "are", True
        else:
            return "is", True
    return current_word, False

#"Handling" an auxiliary in this case means returning it unmodified
def handle_auxiliary(context):
    w = context["word"]
    pos=context["pos"]
    if w in AUX_WORDS or "aux" in pos:
        return w,True
    return w,False

def handle_main_verb(context):
    w = context["word"]
    pos = context["pos"]
    prev = context["prev"]
    prev_pos = context["prev_pos"]
    prev2_pos = context["prev2_pos"]
    changed_word=False

    # You're not a verb.  We don't want your kind here
    if "verb" not in context["pos"]:
        return context["word"],False

    context["has_subject"], context["is_third_person"] = detect_subject(context)

    context["has_aux"] = detect_auxiliary(context)

    if context["has_aux"]:
        # force base form (non-third-person)
        context["is_third_person"] = False
        w, changed_word = inflect_verb(context)
    elif context["has_subject"]:
        w, changed_word = inflect_verb(context)

    return w,changed_word

def detect_subject(context):
    subject = find_subject_head(context)

    if not subject:
        return False, False

    is_third_person = classify_subject(subject)
    return True, is_third_person

def classify_subject(word):
    if word in {"he", "she", "it"}:
        return True  # 3rd person singular
    if word in {"I", "you", "we", "they"}:
        return False  # not 3rd person singular

    # noun heuristic
    if word.endswith("s"):
        return False  # plural noun

    return True  # singular noun

def detect_auxiliary(context):
    return  (
        ("aux" in context["prev2_pos"]) or
        (context["prev"] in AUX_WORDS if context["prev"] else False)
    )

def inflect_verb(context):
    word = context["word"]
    is_third_person = context.get("is_third_person")

    if is_third_person:
        if not word.endswith("s"):
            if word.endswith("y"):
                word = word[:-1] + "ies"
            elif word.endswith(("s", "sh", "ch", "x", "z", "o")):
                word = word + "es"
            else:
                word = word + "s"
    else:
        if word.endswith("ies"):
            word = word[:-3] + "y"
        elif word.endswith("es") and word[:-2].endswith(("s", "sh", "ch", "x", "z", "o")):
            word = word[:-2]
        elif word.endswith("s"):
            word = word[:-1]
    return word,(word != context["word"])

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
    main()

