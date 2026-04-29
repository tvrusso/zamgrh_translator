"""
translator.py

Rule-based Zamgrh -> English translator.

SPRINT 3: PIPELINE CONTRACTS & INVARIANTS
-----------------------------------------
This file documents the responsibility of each pipeline step and adds light
assertions to make assumptions explicit.

GLOBAL PIPELINE INVARIANTS
--------------------------
- Pipeline input and output are always list[str].
- No pipeline step should introduce None or empty-string tokens.
- Unknown tokens should remain bracketed if bracketed form is introduced.
- Steps may modify / insert / remove tokens locally, but should not perform
  broad token reordering.
- fix_verb_agreement is the final authority on verb/copula agreement.
"""

import sys
import json
import re
from pathlib import Path

DATA_PATH = Path(__file__).parent.parent / "data" / "zamgrh_dictionary.json"

AUX_WORDS = {
    "must", "will", "can", "should", "have", "has", "had",
    "am", "is", "are", "do", "does"
}
SUBJECT_PRONOUNS = {"I", "you", "he", "she", "it", "we", "they"}
VERB_LIKE_WORDS = {"eat", "give", "go", "smash", "speak", "come", "run", "have", "is", "are", "am"}
DETERMINERS = {"a", "an", "the", "my", "your", "his", "her", "our", "their"}
SKIP_POS = {"adj", "adv", "det", "prep"}
COLLAPSIBLE_WORDS = {
    "must", "will", "can", "should", "have",
    "is", "are", "am",
    "the", "a", "an",
}


# ---------------------------
# Dictionary loading
# ---------------------------

def load_dictionary():
    """Load the Zamgrh dictionary JSON."""
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def build_lookup(data):
    """Build a Zamgrh word -> entry lookup table."""
    return {entry["word"]: entry for entry in data}


def build_english_pos_lookup(data):
    """Build an English gloss -> POS lookup table."""
    eng_lookup = {}
    for entry in data:
        pos = set(entry.get("pos", []))
        for e in entry.get("english", []):
            gloss = e["gloss"]
            eng_lookup.setdefault(gloss, set()).update(pos)
    return eng_lookup


# ---------------------------
# Translation pipeline
# ---------------------------

SKIP_POS = {"adj", "adv", "det","prep",}
COLLAPSIBLE_WORDS = {
    "must", "will", "can", "should", "have",
    "is", "are", "am",
    "the", "a", "an",
}

# ---------------------------
# Validation helpers
# ---------------------------

def assert_word_list(words, label="words"):
    assert isinstance(words, list), f"{label} must be a list, got {type(words).__name__}"
    assert all(isinstance(w, str) for w in words), f"{label} must contain only strings"
    assert all(w is not None for w in words), f"{label} must not contain None"
    assert all(w != "" for w in words), f"{label} must not contain empty-string words"


def assert_lookup_shapes(lookup, eng_lookup):
    assert isinstance(lookup, dict), f"lookup must be dict, got {type(lookup).__name__}"
    assert isinstance(eng_lookup, dict), f"eng_lookup must be dict, got {type(eng_lookup).__name__}"


def assert_unknown_word_shape(words, label="words"):
    for w in words:
        if w.startswith("["):
            assert w.endswith("]"), f"{label} contains malformed unknown word: {w}"


def validate_pipeline_step_result(words, label):
    assert_word_list(words, label)
    assert_unknown_word_shape(words, label)


def apply_grammar_pipeline(words, lookup, eng_lookup, tokens, debug=False):
    """
    Apply the English grammar cleanup pipeline.

    CONTRACT
    --------
    Expects:
    - words: list[str] (tokenized English glosses / unknown-token forms)
    - lookup / eng_lookup: valid dictionary structures
    - tokens: parallel token list
      - MUST be aligned with words on entry
      - alignment may be broken by pipeline steps, and so until
        technical debt is removed should be treated as reference-only while
        in the pipeline

    Guarantees:
    - returns list[str]
    - no step introduces None or empty words
    - unknown bracketed tokens remain bracketed
    - fix_verb_agreement is the FINAL authority on verb/copula form

    PIPELINE PHASES
    ---------------
    1. Lexical cleanup (no structure changes)
      - resolve_hab_ambiguity

    2. Subject normalization (structure-changing, early)
      - simplify_subject

    3. Local grammar normalization (no agreement decisions)
      - fix_possession
      - fix_object_pronouns
      - collapse_repeated_pronouns
      - fix_determiners
      - fix_prepositions

    4. Structure completion (may insert tokens)
      - insert_copula
      - insert_articles
      - dedupe_function_words
      - fix_am_progressive

    5. Final agreement authority
      - fix_verb_agreement

    ORDERING INVARIANTS
    -------------------
    - No step before fix_verb_agreement may rely on correct verb agreement
    - No step after fix_verb_agreement may modify verbs or copulas
    - simplify_subject MUST run before any subject-dependent logic
    - insert_copula MUST run before fix_verb_agreement

    TOKEN CONTRACT (TEMPORARY TECH DEBT)
    -----------------------------------
    - tokens are treated as read-only reference data
    - pipeline steps may desynchronize words and tokens
    - helpers must fall back to lookup-based POS when token alignment fails

    DEBUG LEVELS
    ------------
    - 0: no debug output
    - 1: show only steps that changed the token stream
    - 2: show every step
    """

    # --- Input validation ---
    assert_word_list(words, "pipeline input")
    assert_lookup_shapes(lookup, eng_lookup)
    assert_unknown_word_shape(words, "pipeline input")

    # tokens must align 1:1 with words on input, though the pipeline
    # in its current form might change that.  This is temporary technical
    # debt.
    # Real Zamgrh-derived tokens are not yet passed here due to
    # known multi-word gloss alignment issues.

    assert len(tokens) == len(words), "tokens must align with words"

    # --- Define pipeline steps ---
    PIPELINE = [
        ("resolve_hab_ambiguity", resolve_hab_ambiguity),
        ("simplify_subject", simplify_subject),
        ("fix_possession", fix_possession),
        ("fix_object_pronouns", fix_object_pronouns),
        ("collapse_repeated_pronouns", collapse_repeated_pronouns),
        ("fix_determiners", fix_determiners),
        ("fix_prepositions", fix_prepositions),
        ("insert_copula", insert_copula),
        ("insert_articles", insert_articles),
        ("dedupe_function_words", dedupe_function_words),
        ("fix_am_progressive", fix_am_progressive),
        ("fix_verb_agreement", fix_verb_agreement),
    ]

    # enforce structural phase ordering
    names = [name for name, _ in PIPELINE]
    assert "simplify_subject" in names
    assert "insert_copula" in names
    assert "fix_verb_agreement" in names
    assert names.index("simplify_subject") < names.index("insert_copula")
    assert names.index("insert_copula") < names.index("fix_verb_agreement")
    # Final authority lock
    assert names[-1] == "fix_verb_agreement"

    # --- Helper for debug rendering ---
    def render(words):
        return " ".join(words) if words else "<empty>"

    # --- Debug: initial state ---
    if debug:
        print("\n=== DEBUG: GRAMMAR PIPELINE ===")
        print("[INPUT]")
        print(f"  words: {render(words)}")

    # CONTRACT: tokens are reference-only and may become misaligned
    assert tokens is not None, "tokens must be provided (even if imperfect)"

    # --- Run pipeline ---
    for name, step in PIPELINE:
        before = list(words)

        # Apply step with current words + tokens
        words, tokens = step(words, lookup, eng_lookup, tokens=tokens)

        # Validate output integrity
        validate_pipeline_step_result(words, f"{name} output")
        assert_unknown_word_shape(words, f"{name} output")

        # --- Debug output ---
        changed = before != words
        should_print = (debug >= 2) or (debug >= 1 and changed)
        if should_print:
            print(f"\n[STEP] {name}")
            print(f"  input:   {render(before)}")
            print(f"  output:  {render(words)}")
            print(f"  status:  {'CHANGED' if changed else 'unchanged'}")

    # --- Post-pipeline contract checks ---
    assert_word_list(words, "pipeline final output")


    # --- Debug: final state ---
    if debug:
        print("\n[FINAL]")
        print(f"  words: {render(words)}")
        print("=== END DEBUG ===")

    return words

def question_postprocess(text, structure, original_text):
    """
    Post-process question output.

    Expects:
    - text is already translated
    - structure is a structure dict from zamgrh_to_structure

    Guarantees:
    - preserves trailing question semantics
    - does not alter non-question text
    """
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

def is_going_to_sequence(words, i):
    if i + 2 < len(words) and words[i+1] == "going" and words[i+2] == "to":
        return 2
    if i + 1 < len(words) and words[i+1] == "going to":
        return 1
    return 0

def fix_am_progressive(words, lookup, eng_lookup, tokens):
    """
    Owns: narrow repair of 'I going to' -> 'I am going to'.

    Expects:
    - tokenized English glosses

    Guarantees:
    - inserts 'am' only for the specific 'I going to' pattern
    - does not attempt general tense/aspect handling
    """
    assert_word_list(words, "fix_am_progressive input")
    result = []
    i = 0

    while i < len(words):
        w = words[i]
        if w == "I":
            span = is_going_to_sequence(words, i)
            if span:
                result.append("I")
                result.append("am")
                i += 1
                continue
        result.append(w)
        i += 1

    validate_pipeline_step_result(result, "fix_am_progressive output")
    return result, tokens


def resolve_hab_ambiguity(words, lookup, eng_lookup, tokens):
    """
    Owns: lexical ambiguity cleanup for specific known collisions.

    Expects:
    - tokenized English glosses

    Guarantees:
    - rewrites 'help' -> 'have' only in known local contexts
    - does not reorder tokens or infer broader syntax

    MUST run before:
    - any stage that relies on correct verb identity (e.g., agreement)
    """
    assert_word_list(words, "resolve_hab_ambiguity input")
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

    validate_pipeline_step_result(result, "resolve_hab_ambiguity output")
    return result, tokens


def simplify_subject(words, lookup, eng_lookup, tokens):
    """
    Owns: Zamgrh-specific redundant subject cleanup.

    Expects:
    - tokenized English glosses, including possible 'I zombie' sequence

    Guarantees:
    - removes redundant 'zombie' after 'I'
    - does not otherwise rewrite clause structure

    MUST run before:
        - insert_copula
        - fix_verb_agreement
          because it defines the canonical subject form
    """
    assert_word_list(words, "simplify_subject input")
    result = []
    i = 0

    while i < len(words):
        if i < len(words)-1 and words[i] == "my" and words[i+1] == "zombie":
            result.append("I")
            i += 2
            continue
        result.append(words[i])
        i += 1

    validate_pipeline_step_result(result, "simplify_subject output")
    return result, tokens


def fix_possession(words, lookup, eng_lookup, tokens):
    """
    Owns: possessive pronoun conversion for narrow lexical patterns.

    THIS FUNCTION IS NOW A NO-OP!  Its original purpose was to fix a problem
    that no longer exists.

    It is being kept in the pipeline as a placeholder should it be necessary
    to fix possessive pronouns of other sorts than the one it no longer
    needs to fix.

    Expects:
    - tokenized English glosses

    Guarantees:
      - returns a list of glosses with any needed fixes applied

    """
    assert_word_list(words, "fix_possession input")
    result = words

    validate_pipeline_step_result(result, "fix_possession output")
    return result, tokens


def fix_object_pronouns(words, lookup, eng_lookup, tokens):
    """
    Owns: object pronoun case after selected verbs.

    Expects:
    - tokenized English glosses

    Guarantees:
    - converts 'verb I' -> 'verb me' for known verbs
    - does not own possessive or prepositional pronoun case
    """
    assert_word_list(words, "fix_object_pronouns input")
    verbs = {"give", "help", "shoot", "eat", "smash", "have"}
    result = []

    for i, w in enumerate(words):
        if w == "I" and i > 0 and words[i - 1] in verbs:
            result.append("me")
        else:
            result.append(w)

    validate_pipeline_step_result(result, "fix_object_pronouns output")
    return result, tokens

def has_future_verb(words, start_idx, lookup, eng_lookup, tokens):
    for w in words[start_idx + 1:]:
        token = find_token_for_word(w, tokens)
        pos = set(token["pos"]) if token else get_pos(w, lookup, eng_lookup)

        if "verb" in pos or "aux" in pos:
            return True

    return False

def choose_copula(prev, prev_token):
    if prev == "I":
        return "am"
    if has_s_suffix(prev, prev_token):
        return "are"
    return "is"

def insert_copula(words, lookup, eng_lookup, tokens):
    """
    Owns: local missing-copula insertion.

    Expects:
    - tokenized English glosses with usable POS lookup

    Guarantees:
    - inserts 'is/are' between noun + adjective when no earlier verb was seen
    - inserts auxiliary before progressive -ing predicates when safe
    - does not handle full clause repair or late agreement decisions
    - prefers token POS when available, falls back to lookup
    Ordering:
    - MUST run after simplify_subject (subject must be canonical)
    - MUST run before fix_verb_agreement (output is not final)
    - SHOULD run after basic lexical normalization

    Notes:
    - Relies on POS (token-first, lookup fallback)
    - Uses heuristic "no earlier verb seen" to decide insertion
    - May insert incorrect copula forms; correctness is enforced later

    ASSUMPTION:
     - subject normalization already applied
     - this step must not rely on final agreement correctness
    """
    assert_word_list(words, "insert_copula input")

    result = []
    seen_verb = False

    for i, w in enumerate(words):
        # Token-first POS
        token = find_token_for_word(w, tokens)
        pos = set(token["pos"]) if token else get_pos(w, lookup, eng_lookup)
        is_ing = token and has_ing_form(token["features"])

        if ("verb" in pos or "aux" in pos) and not is_ing:
            seen_verb = True

        if i > 0:
            prev = result[-1]

            prev_token = find_token_for_word(prev, tokens)
            prev_pos = (
                set(prev_token["pos"])
                if prev_token
                else get_pos(prev, lookup, eng_lookup)
            )

            is_noun = "noun" in prev_pos
            is_adj = "adj" in pos
            is_unknown = w.startswith("[")
            is_ing = token and has_ing_form(token["features"])

            # Progressive auxiliary insertion (e.g., "I reporting" → "I am reporting")
            # NOTE:
            # This is an early structural insertion.
            # Final agreement (is/are/am correctness) is handled later.
            if (
                not seen_verb
                and is_ing
                and not has_future_verb(words, i, lookup, eng_lookup, tokens)
            ):
                if "noun" in prev_pos or prev in SUBJECT_PRONOUNS:
                    # Avoid modifier case like "the eating zombies"
                    if prev not in DETERMINERS:
                        result.append(choose_copula(prev, prev_token))
                        seen_verb = True

            # Noun + adjective copula insertion
            if not seen_verb and is_noun and is_adj and not is_unknown:
                result.append(choose_copula(prev, prev_token))

        result.append(w)

    validate_pipeline_step_result(result, "insert_copula output")
    return result, tokens

def fix_prepositions(words, lookup, eng_lookup, tokens):
    """
    Owns: pronoun case after prepositions.

    Expects:
    - tokenized English glosses

    Guarantees:
    - converts 'to I' -> 'to me'
    - does not own possessive determiner conversion
    """
    assert_word_list(words, "fix_prepositions input")
    result = []

    for i, w in enumerate(words):
        if w == "I" and i > 0 and words[i - 1] == "to":
            result.append("me")
        else:
            result.append(w)

    validate_pipeline_step_result(result, "fix_prepositions output")
    return result, tokens


def fix_verb_agreement(words, lookup, eng_lookup, tokens):
    """
    Owns: final verb and copula agreement normalization.

    Expects:
    - token stream after earlier cleanup / insertion steps

    Guarantees:
    - is the last writer on verb/copula form
    - does not reorder tokens
    - uses helper functions to keep ownership localized

    Ordering:
    - MUST run after all structural modification stages
    - MUST be the final pipeline step

    Notes:
    - Performs both early and late copula correction
    - Relies on subject detection via build_context
    """
    assert_word_list(words, "fix_verb_agreement input")

    result = []

    for w in words:
        context = build_context(w, result, lookup, eng_lookup, tokens)
        w, changed_word = handle_copula(context)
        result_word = w

        if not changed_word:
            w, changed_word = handle_auxiliary(context)
            if changed_word:
                result_word = w
            else:
                w, changed_word = handle_main_verb(context)
                result_word = w


        # Only update word here; late copula correction depends on subject/prev context,
        # not current-token morphology.
        # Late copula correction is intentional:
        # fix_verb_agreement is the final authority on agreement.
        context["word"] = result_word
        result_word, _ = handle_copula_late(context)
        result.append(result_word)

    validate_pipeline_step_result(result, "fix_verb_agreement output")
    return result, tokens


# ---------------------------
# Utility functions for pipeline
# ---------------------------

def build_context(current_word, result, lookup, eng_lookup, tokens):
    """
    Build a context object for agreement helpers.

    Guarantees:
    - returns a dict with word/POS/previous-token information
    - result_so_far preserves left-to-right emitted token history
    - tokens are passed through to subject-head discovery
    - prefers token POS when available, falls back to lookup POS
    """
    assert isinstance(current_word, str), (
        f"current_word must be str, got {type(current_word).__name__}"
    )
    assert_word_list(result, "build_context.result")

    current_token = find_token_for_word(current_word, tokens)
    pos = (
        set(current_token["pos"])
        if current_token
        else get_pos(current_word, lookup, eng_lookup)
    )

    prev = result[-1] if result else None
    prev_token = find_token_for_word(prev, tokens)

    prev2 = result[-2] if len(result) > 1 else None
    prev2_token = find_token_for_word(prev2, tokens)

    subject_word = find_subject_head({
        "result_so_far": result,
        "lookup": lookup,
        "eng_lookup": eng_lookup,
        "context_tokens": tokens,
    })

    subject_token = find_token_for_word(subject_word, tokens)

    return {
        "word": current_word,
        "pos": pos,
        "prev": prev,
        "prev2": prev2,
        "result_so_far": result,
        "lookup": lookup,
        "eng_lookup": eng_lookup,
        "context_tokens": tokens,
        "context_current_token": current_token,
        "context_previous_token": prev_token,
        "context_previous2_token": prev2_token,
        "context_subject_token": subject_token,
        "context_subject_word": subject_word,
    }

def apply_ing_override(word, token, pos):
    """
    return "verb" as the pos if we've got a word that has an "ing" suffix
    that was either:
      - recognized as a verb with suffix already
      - unrecognized and has "ing" at the end
    Otherwise return the pos passed in
    """
    is_ing = (token and has_ing_form(token["features"]))

    if is_ing:
        retpos = {"verb"}
    else:
        retpos = pos
    return retpos

def find_subject_head(context):
    """
    Owns: local subject-head discovery for agreement.
    Expects:
    - helper context produced by build_context
    Guarantees:
    - returns best-effort local subject candidate or None
    - stops scanning at verb/aux boundaries
    - prefers token POS when available, falls back to lookup POS
    """
    words = context["result_so_far"]
    lookup = context["lookup"]
    eng_lookup = context["eng_lookup"]
    tokens = context.get("context_tokens")

    idx = len(words) - 1
    candidate = None

    while idx >= 0:
        word = words[idx]

        token = find_token_for_word(word, tokens)
        pos = set(token["pos"]) if token else get_pos(word, lookup, eng_lookup)
        pos = apply_ing_override(word, token, pos)

        if "aux" in pos:
            return None

        if "verb" in pos:
            if has_ing_suffix(word, token):
                idx -= 1
                continue
            break

        # Treat leftmost unknown with no POS as potential candidate
        if len(pos) == 0:
            candidate = word
            idx -= 1
            continue

        if pos & SKIP_POS:
            idx -= 1
            continue

        if "noun" in pos:
            candidate = word

            # Check if this noun is governed by a gerund.
            if idx - 1 >= 0:
                prev_word = words[idx - 1]
                prev_token = find_token_for_word(prev_word, tokens)
                prev_pos = (
                    set(prev_token["pos"])
                    if prev_token
                    else get_pos(prev_word, lookup, eng_lookup)
                )
                prev_pos = apply_ing_override(prev_word, prev_token, prev_pos)

                if "verb" in prev_pos and has_ing_suffix(prev_word, prev_token):
                    # Check if this is part of a larger noun phrase.
                    if idx - 2 >= 0:
                        prev2_word = words[idx - 2]
                        prev2_token = find_token_for_word(prev2_word, tokens)
                        prev2_pos = (
                            set(prev2_token["pos"])
                            if prev2_token
                            else get_pos(prev2_word, lookup, eng_lookup)
                        )

                        if ("noun" in prev2_pos) or (prev2_word in DETERMINERS):
                            # Modifier, e.g. "the eating zombies"
                            pass
                        else:
                            candidate = prev_word
                    else:
                        # Start of sentence → safe to promote gerund.
                        candidate = prev_word

            idx -= 1
            continue

        elif word in SUBJECT_PRONOUNS:
            if candidate is None:
                candidate = word
            break

        idx -= 1

    return candidate

def has_compound_subject(context):
    """
    Owns: narrow detection of noun ... and ... noun compound subjects.

    Guarantees:
    - returns True only for simple local compound-subject pattern
    - does not perform full clause parsing
    - prefers token POS when available, falls back to lookup
    """
    words = context["result_so_far"]
    lookup = context["lookup"]
    eng_lookup = context["eng_lookup"]
    tokens = context.get("context_tokens")

    idx = len(words) - 1
    seen_noun = False
    seen_and = False

    while idx >= 0:
        word = words[idx]

        token = find_token_for_word(word, tokens)
        pos = set(token["pos"]) if token else get_pos(word, lookup, eng_lookup)
        pos = apply_ing_override(word, token, pos)

        if "verb" in pos or "aux" in pos:
            break

        if "noun" in pos:
            if seen_and:
                return True
            seen_noun = True

        elif word == "and":
            if seen_noun:
                seen_and = True

        idx -= 1

    return False

# ---------------------------
# fix_verb_agreement helper functions
# ---------------------------

def handle_copula(context):
    """
    Owns: early local copula normalization.

    Guarantees:
    - normalizes explicit is/are/am based on immediate left context
    - may be overridden by late copula correction
    """
    current_word = context["word"]
    previous_word = context["prev"]
    subject_word = context.get("context_subject_word")
    subject_token = context.get("context_subject_token")
    prev_token = context.get("context_previous_token")

    if current_word in {"is", "are", "am"}:
        if previous_word == "I":
            return "am", True

        if subject_word == "I":
            return "am", True

        if subject_token is not None:
            features = subject_token.get("features")
            if has_s_form(features):
                return "are", True
            else:
                return "is", True

        if prev_token is not None:
            features = prev_token.get("features")
            if has_s_form(features):
                return "are", True
            else:
                return "is", True

        # fallback to old logic
        has_subject, is_third_person = detect_subject(context)
        if has_subject and not is_third_person:
            return "are", True

        return "is", True

    return current_word, False

def handle_copula_late(context):
    """
    Owns: final copula correction after subject detection.

    Guarantees:
    - resolves copula form using detected subject if available
    - leaves token unchanged if no subject is detected

    NOTE:
    In absence of morphology, we fall back to detect_subject
    and assume third-person singular unless plural is explicitly marked.
    """
    word = context["word"]
    if word not in {"is", "are", "am"}:
        return word, False

    previous_word = context.get("prev")
    subject_token = context.get("context_subject_token")

    if previous_word == "I":
        return "am", True

    if subject_token and has_s_form(subject_token["features"]):
        return "are", True

    has_subject, is_third_person = detect_subject(context)
    if not has_subject:
        return word, False

    if is_third_person:
        return "is", word != "is"
    else:
        return "are", word != "are"

def handle_auxiliary(context):
    """
    Owns: auxiliary recognition.

    Guarantees:
    - returns auxiliaries unchanged
    - marks them as handled so main-verb logic does not own them
    """
    w = context["word"]
    pos = context["pos"]
    if w in AUX_WORDS or "aux" in pos:
        return w, True
    return w, False


def handle_main_verb(context):
    """
    Owns: main-verb inflection using subject and auxiliary context.

    Guarantees:
    - inflects only verb tokens
    - forces base form after auxiliaries
    """
    token = context["context_current_token"]
    token_pos = set(token["pos"]) if token else set()
    fallback_pos = get_pos(context["word"], context["lookup"], context["eng_lookup"])
    pos = token_pos | fallback_pos
    if "verb" not in pos:
        return context["word"], False

    current_token = context.get("context_current_token")
    if current_token and has_ing_form(current_token["features"]):
        return context["word"], False

    context["has_subject"], context["is_third_person"] = detect_subject(context)
    context["has_aux"] = detect_auxiliary(context)

    if context["has_aux"]:
        if not context["has_subject"] and context["prev"] == "is":
            return context["word"], False
        context["is_third_person"] = False
        return inflect_verb(context)

    if context["has_subject"]:
        return inflect_verb(context)

    return context["word"], False


def detect_subject(context):
    """
    Owns: local subject presence / plurality detection for agreement.

    Guarantees:
    - returns (has_subject, is_third_person)
    - compound subjects are treated as non-third-person singular
    """
    if has_compound_subject(context):
        return True, False

    subject = find_subject_head(context)
    if not subject:
        return False, False

    is_third_person = classify_subject_with_context(subject, context)
    return True, is_third_person

def classify_subject_with_context(word, context):
    """
    Enhanced subject classification using morphology when available.
    Falls back to classify_subject.
    """
    token = context.get("context_subject_token")

    if token and token.get("features"):
        if has_s_form(token["features"]):
            return False  # plural → not 3rd person singular
        pos = token.get("pos", set())
        if "noun" not in pos:
            return classify_subject(word, token)

    return classify_subject(word, token)

def classify_subject(word, token):
    """
    Classify whether a subject should trigger third-person singular agreement.
    """
    if word in {"he", "she", "it"}:
        return True
    if word in {"I", "you", "we", "they"}:
        return False
    if (not token or not token.get("features")) and  word.endswith("s"):
        return False
    return True


def detect_auxiliary(context):
    """
    Detect whether a main verb is governed by a nearby auxiliary.
    """
    prev2_token = context.get("context_previous2_token")
    prev2_pos = set(prev2_token["pos"]) if prev2_token else set()

    return (
        ("aux" in prev2_pos) or
        (context["prev"] in AUX_WORDS if context["prev"] else False)
    )


def inflect_verb(context):
    """
    Owns: narrow English present-tense inflection / deinflection.

    Guarantees:
    - applies local orthographic rules only
    - does not perform semantic or tense analysis
    """
    word = context["word"]
    is_third_person = context.get("is_third_person")

    token = context.get("context_current_token")
    features = token["features"] if token else {}
    has_s = has_s_suffix(word, token)

    if is_third_person:
        if not has_s:
            if word.endswith("y"):
                word = word[:-1] + "ies"
            elif word.endswith(("s", "sh", "ch", "x", "z", "o")):
                word = word + "es"
            else:
                word = word + "s"
    else:
        if has_s:
            if word.endswith("ies"):
                word = word[:-3] + "y"
            elif word.endswith("es") and word[:-2].endswith(("s", "sh", "ch", "x", "z", "o")):
                word = word[:-2]
            elif word.endswith("s"):
                word = word[:-1]

    return word, (word != context["word"])


def dedupe_function_words(words, lookup, eng_lookup, tokens):
    """
    Owns: duplicate collapsible function-word cleanup.

    Guarantees:
    - removes only adjacent duplicates for selected function words
    - does not collapse content-word repetition
    """
    assert_word_list(words, "dedupe_function_words input")
    result = []
    prev = None

    for w in words:
        if w == prev and w in COLLAPSIBLE_WORDS:
            continue
        result.append(w)
        prev = w

    validate_pipeline_step_result(result, "dedupe_function_words output")
    return result, tokens


# Define currently permitted features
ALLOWED_FEATURES = {
    "form": ["ing","s"],
}

def is_safe_plural_candidate(word, base):
    # Reject very short words (prevents anz → an)
    if len(base) < 3:
        return False

    return True

def validate_features(features: dict) -> None:
    for key, value in features.items():
        assert key in ALLOWED_FEATURES, f"Unknown feature: {key}"
        assert type(value) == type(ALLOWED_FEATURES[key]), f"Invalid type for {key}: {value}"
        if isinstance(ALLOWED_FEATURES[key],list):
            assert all(v in ALLOWED_FEATURES[key] for v in value), f"invalid value in {value} for {key}"

def set_feature_s_suffix(features: dict):
    features.setdefault("form",[]).append("s")

def has_s_form(features: dict):
    return "form" in features and "s" in features["form"]

def has_s_suffix(word, token: dict):
    """
    Return true if morphology has identified an "s" suffix OR there is no
    token associated with this word and the word ends in "s"

    Use "has_s_form" for strict observance of morphology, only use this
    when the fallback rule is needed.
    """
    return ((token and "form" in token["features"]
             and "s" in token["features"]["form"])
            or
            (word and word.endswith("s")))

def set_feature_ing_suffix(features: dict):
    features.setdefault("form",[]).append("ing")

def has_ing_form(features: dict):
    return "form" in features and "ing" in features["form"]

def has_ing_suffix(word, token: dict):
    """
    Return true if morphology has identified an "ing" suffix OR there is no
    token associated with this word and the word ends in "ing"

    Use "has_ing_form" for strict observance of morphology, only use this
    when the fallback rule is needed.
    """
    return ((token and "form" in token["features"]
             and "ing" in token["features"]["form"])
            or
            (word and word.endswith("ing")))

def normalize_morphology(word, lookup):
    """
    Owns: minimal morphology normalization.

    Guarantees:
    - returns (base_word, features_dict)
    - currently supports only:
      - narrow plural-z normalization
      - recognition of "!ng" as a suffix representing "ing" in English
    - features contains only recognized keys and values
    - function is no-op by default
    - transformations depend only on lookup
    - POS is never changed; function emits features based on lookup

    """
    assert isinstance(word, str), f"word must be str, got {type(word).__name__}"

    retword = word
    features = {}

    if word in lookup:
        retword = word
        features = {}

    else:
        changed = True
        stripped_once = False

        while changed:
            changed = False

            if retword in lookup:
                break

            # handle plural
            if (not has_s_form(features)
                and retword.endswith("z")
                and len(retword) > 1):
                base = retword[:-1]
                entry = lookup.get(base)

                if stripped_once and not entry:
                    continue

                if entry:
                    retword = base
                    if any(p in {"noun", "pron"} for p in entry.get("pos", [])):
                        set_feature_s_suffix(features)
                        changed = True
                        stripped_once = True
                        continue
                elif (retword == word
                      and is_safe_plural_candidate(retword, base)):
                    if stripped_once:
                        continue
                    retword = base
                    set_feature_s_suffix(features)
                    changed = True
                    stripped_once = True
                    continue

            # handle "!ng" suffix
            if (not has_ing_form(features)
                and retword.endswith("!ng")
                and len(retword) > 3):
                base = retword[:-3]
                entry = lookup.get(base)
                if entry and "verb" in entry.get("pos",[]):
                    retword = base
                    set_feature_ing_suffix(features)
                    changed = True
                    continue

    validate_features(features)
    return retword, features

def apply_plural(word, features):
    if not word:
        return word
    if not has_s_form(features):
        return word
    if word.endswith("s"):
        return word
    return word + "s"

# ---------------------------
# Helpers for dictionary-driven POS logic
# ---------------------------

def get_pos(word, lookup, eng_lookup):
    """
    Get POS tags for a token using direct lookup plus narrow fallbacks.

    Guarantees:
    - returns set[str]
    - never raises on missing token
    """
    if not word:
        return set()

    word = word.lower()

    entry = lookup.get(word)
    if entry:
        return set(entry.get("pos", []))

    if word in eng_lookup:
        return eng_lookup[word]

    if word.endswith("s"):
        base = word[:-1]
        if base in eng_lookup:
            return eng_lookup[base]

    base, _features = normalize_morphology(word, lookup)
    if base != word:
        entry = lookup.get(base)
        if entry:
            return set(entry.get("pos", []))

    return set()


def insert_articles(words, lookup, eng_lookup, tokens):
    """
    Owns: local article insertion for object-like noun phrases.

    Expects:
    - tokenized English glosses
    - usable POS lookup from get_pos()
    - earlier steps have already handled pronoun/determiner/preposition cleanup

    Guarantees:
    - inserts "a/an" for supported singular noun phrases in local contexts
    - can place the article before a modifier+noun phrase (e.g. "a big brain")
    - does not perform full clause parsing or broad token reordering

    Does NOT:
    - resolve subject/verb agreement
    - fully understand multi-clause boundaries
    - perform deep noun-phrase analysis
    """
    assert_word_list(words, "insert_articles input")

    result = []
    seen_verb = False
    consumed_object = False

    for i, w in enumerate(words):
        token = find_token_for_word(w, tokens)
        token_pos = set(token["pos"]) if token else set()
        fallback_pos = get_pos(w, lookup, eng_lookup)
        pos = token_pos | fallback_pos

        # --- PRONOUN GUARD ---
        if w in SUBJECT_PRONOUNS:
            result.append(w)
            continue

        is_noun = "noun" in pos
        is_ing = token and has_ing_form(token.get("features", {}))
        is_verb = ("verb" in pos or "aux" in pos) and not is_ing
        is_pure_noun = (
            is_noun
            and not is_verb
            and w not in AUX_WORDS
            and w not in VERB_LIKE_WORDS
        )

        nxt = words[i + 1] if i + 1 < len(words) else None
        nxt_pos = get_pos(nxt, lookup, eng_lookup) if nxt else set()
        next_is_noun = (
            nxt is not None
            and "noun" in nxt_pos
            and "verb" not in nxt_pos
            and "aux" not in nxt_pos
        )

        # Verbs reset object-tracking state.
        if is_verb or w in AUX_WORDS or w in VERB_LIKE_WORDS:
            seen_verb = True
            consumed_object = False
            result.append(w)
            continue

        should_article_after_to = (
            is_pure_noun
            and i > 0
            and result
            and result[-1] == "to"
            and not has_s_suffix(w, token)
            and not next_is_noun
        )

        should_article_as_object = (
            is_pure_noun
            and seen_verb
            and not consumed_object
            and not next_is_noun
            and not has_s_suffix(w, token)
        )

        if should_article_as_object or should_article_after_to:
            prev = result[-1] if result else None
            prev_token = find_token_for_word(prev, tokens)
            prev_token_pos = set(prev_token["pos"]) if prev_token else set()
            prev_fallback_pos = get_pos(prev, lookup, eng_lookup) if prev else set()
            prev_pos = prev_token_pos | prev_fallback_pos

            # If the previous token looks like a local modifier, insert the
            # article before that modifier so we get "a big brain" instead of
            # "big a brain".
            prev_is_modifier = (
                prev is not None
                and prev not in DETERMINERS
                and prev not in {"to", "and", "or"}
                and prev not in SUBJECT_PRONOUNS
                and "verb" not in prev_pos
                and "aux" not in prev_pos
                and "noun" not in prev_pos
                and "conj" not in prev_pos
            )

            article = "an" if w[0].lower() in "aeiou" else "a"

            if prev_is_modifier:
                result.insert(len(result) - 1, article)
            elif "det" not in prev_pos:
                result.append(article)

            consumed_object = True

        result.append(w)

    validate_pipeline_step_result(result, "insert_articles output")
    return result, tokens

def fix_determiners(words, lookup, eng_lookup, tokens):
    """
    Owns: determiner / possessive interpretation for local noun phrases.

    Expects:
    - tokenized English glosses

    Guarantees:
    - converts 'I noun' -> 'my noun' in clearly possessive environments
    - does not override clear subject uses of 'I'
    """
    assert_word_list(words, "fix_determiners input")
    result = []

    for i, w in enumerate(words):
        if w == "I":
            nxt = words[i + 1] if i + 1 < len(words) else None
            nxt2 = words[i + 2] if i + 2 < len(words) else None
            nxt_pos = get_pos(nxt, lookup, eng_lookup) if nxt else set()
            nxt2_pos = get_pos(nxt2, lookup, eng_lookup) if nxt2 else set()

            if nxt and (
                "verb" in nxt_pos
                or "aux" in nxt_pos
                or nxt in AUX_WORDS
                or nxt in VERB_LIKE_WORDS
            ):
                result.append(w)
                continue

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

    validate_pipeline_step_result(result, "fix_determiners output")
    return result, tokens


def collapse_repeated_pronouns(words, lookup, eng_lookup, tokens):
    """
    Owns: cleanup of repeated adjacent pronouns.

    Guarantees:
    - collapses repeated 'I' / 'me'
    - leaves non-pronoun repetition alone
    """
    assert_word_list(words, "collapse_repeated_pronouns input")
    result = []
    prev = None

    for w in words:
        if w == prev and w in {"I", "me", "my"}:
            continue
        result.append(w)
        prev = w

    validate_pipeline_step_result(result, "collapse_repeated_pronouns output")
    return result, tokens


# ---------------------------
# Normalization helpers
# ---------------------------

def clean(word):
    """
    Clean a raw word while preserving internal ! markers used by Zamgrh words.
    """
    assert isinstance(word, str), f"word must be str, got {type(word).__name__}"
    word = word.lower()
    word = re.sub(r"^[^\w!]+", "", word)
    word = re.sub(r"[^\w]+$", "", word)
    return word


def grammar_postprocess(text, debug=False):
    """
    Final surface cleanup after the grammar pipeline.

    Guarantees:
    - expands 'not' -> 'do not'
    - capitalizes the first output word if present
    """
    assert isinstance(text, str), f"text must be str, got {type(text).__name__}"
    words = text.split()
    result = []
    i = 0

    while i < len(words):
        w = words[i]
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


def pick_gloss(entry, desired_pos=None):
    """
    Pick a gloss from a dictionary entry.

    NOTE:
    POS filtering is minimal and future-facing; current translation logic
    mostly uses the first gloss.
    """
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
    """
    Infer a desired POS from local translated context.

    Current status:
    - helper for possible future gloss selection improvements
    - not central to current pipeline contracts
    """
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


def select_gloss(entry):
    english = entry.get("english", [])

    # if there are multiple glosses, find the one with the highest weight
    if english:
        return sorted(english, key=lambda x: -x.get("weight", 0))[0]["gloss"]

    return None

def render_gloss_with_features(gloss, features, pos):
    """
    Render a gloss using morphology-derived features.
    """
    if has_ing_form(features) and has_s_form(features):
        retval = gloss + "ings"
    elif has_s_form(features):
        if gloss == "you" and "pron" in pos:
            retval = "you"
        else:
            retval = gloss + "s"
    elif has_ing_form(features):
        retval = gloss + "ing"
    else:
        retval = gloss

    return retval

def zamgrh_to_gloss_tokens(text,lookup, eng_lookup):
    """
    Look up Zamgrh text words and return a list of corresponding
    English glosses

    Expects:
      - raw Zamgrh input string
      - valid lookup tables

    Guarantees:
     - Returns a list of token structures
     - unknown input words are bracketed
    - Morphology may normalize unknown tokens internally, but surface form is
      preserved during gloss rendering.
    """
    assert isinstance(text, str), f"text must be str, got {type(text).__name__}"
    assert_lookup_shapes(lookup, eng_lookup)

    tokens = []
    words = text.split()

    for raw in words:
        w = clean(raw)
        base, features = normalize_morphology(w, lookup)
        entry = lookup.get(base)

        if entry:
            gloss = select_gloss(entry)
            pos = set(entry.get("pos", []))
            gloss = render_gloss_with_features(gloss, features, pos)
        else:
            gloss = f"[{raw}]"
            pos = set()

        tokens.append({
            "raw": raw,
            "word": gloss,
            "base": base,
            "pos": pos,
            "features": dict(features),
        })

    return tokens

def find_token_for_word(word, tokens):
    if not tokens or not word:
        return None
    for t in tokens:
        if t["word"] == word:
            return t
    return None

def zamgrh_to_english(text, lookup, eng_lookup, debug=0):
    """
    Translate Zamgrh text to English.

    Expects:
    - raw Zamgrh input string
    - valid lookup tables

    Guarantees:
    - returns a string
    - unknown tokens are bracketed
    - grammar pipeline and postprocess are always applied
    """
    assert isinstance(text, str), f"text must be str, got {type(text).__name__}"
    assert_lookup_shapes(lookup, eng_lookup)

    is_question = text.strip().endswith("?")

    tokens = zamgrh_to_gloss_tokens(text, lookup, eng_lookup)
    words = [t["word"] for t in tokens]

    words = apply_grammar_pipeline(words, lookup, eng_lookup, tokens=tokens, debug=debug)
    sentence = " ".join(words)
    sentence = grammar_postprocess(sentence, debug=debug)

    if is_question and sentence and not sentence.endswith("?"):
        sentence += "?"

    return sentence


def is_plural_subject_word(word, features):
    """
    Detect whether a subject word should be treated as plural.
    """
    if has_s_form(features):
        return True
    return word in {"we", "they"}


def normalize_pronoun_subject(tokens):
    result = []
    i = 0
    while i < len(tokens):
        if (
            i + 1 < len(tokens)
            and tokens[i]["word"] == "my"
            and tokens[i + 1]["word"] == "zombie"
        ):
            result.append({
                **tokens[i],
                "word": "I",
                "pos": {"pron"},
                "features": {},
            })
            i += 2
            continue
        result.append(tokens[i])
        i += 1
    return result

def zamgrh_to_structure(text, lookup, eng_lookup):
    """
    Extract a lightweight structure view from Zamgrh input.

    Guarantees:
    - returns dict with subject / verb / object / plural / negated / imperative
    - mirrors some simplification logic used by the main translator
    """
    assert isinstance(text, str), f"text must be str, got {type(text).__name__}"
    assert_lookup_shapes(lookup, eng_lookup)

    structure = {
        "subject": None,
        "verb": None,
        "object": None,
        "plural": False,
        "negated": False,
        "imperative": False,
    }

    initial_tokens = zamgrh_to_gloss_tokens(text, lookup, eng_lookup)
    tokens = normalize_pronoun_subject(initial_tokens)

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
            elif t["word"] == "you" and has_s_form(t["features"]):
                structure["plural"] = True
            break

        if "noun" in t["pos"]:
            structure["subject"] = apply_plural(t["word"],t["features"])
            has_explicit_subject = True
            if has_s_form(t["features"]):
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
            structure["object"] = apply_plural(t["word"],t["features"])
            break

    return structure


def main():
    """
    CLI entry point for interactive translation.
    """
    debug = 0
    for arg in sys.argv[1:]:
        if arg.startswith("--debug"):
            if "=" in arg:
                try:
                    debug = int(arg.split("=", 1)[1])
                except ValueError:
                    print("Invalid debug value. Use --debug=0,1,2")
                    return
            else:
                debug = 2  # default if just "--debug"

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

        print(zamgrh_to_english(text, lookup, eng_lookup, debug))
        if debug:
            print(zamgrh_to_structure(text, lookup, eng_lookup))


if __name__ == "__main__":
    main()
