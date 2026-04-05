import json
import sys
from pathlib import Path
from collections import Counter

DATA_PATH = Path(__file__).parent.parent / "data" / "zamgrh_dictionary.json"

ALLOWED_POS = {
    "noun",
    "verb",
    "adj",
    "adv",
    "prep",
    "pron",
    "det",
    "aux",
    "interj",
    "conj",
    "phrase",
    "proper_noun",
    "insult",
}

REQUIRED_TOP_LEVEL_FIELDS = {"word", "pos", "english"}

ALLOWED_ZAMGRH_CHARS = set("zamgrhnb!")

def load_dictionary(path: Path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"ERROR: Dictionary file not found: {path}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON in dictionary file: {e}")
        sys.exit(1)

    if not isinstance(data, list):
        print("ERROR: Dictionary root must be a JSON list.")
        sys.exit(1)

    return data


def is_nonempty_string(value):
    return isinstance(value, str) and value.strip() != ""


def validate_entry(entry, index, seen_words, errors, warnings):
    if not isinstance(entry, dict):
        errors.append(f"Entry #{index}: entry must be a JSON object.")
        return

    missing_fields = REQUIRED_TOP_LEVEL_FIELDS - set(entry.keys())
    for field in sorted(missing_fields):
        errors.append(f"Entry #{index}: missing required field '{field}'.")

    word = entry.get("word")
    if not is_nonempty_string(word):
        errors.append(f"Entry #{index}: 'word' must be a non-empty string.")
        return

    normalized_word = word.strip()

    if normalized_word != word:
        warnings.append(
            f"Word '{word}': leading/trailing whitespace detected; consider trimming."
        )

    # Lowercase recommendation (warning only)
    if normalized_word != normalized_word.lower():
        warnings.append(
            f"Word '{normalized_word}': should be lowercase (recommended)."
        )

    seen_words.append(normalized_word)

    pos = entry.get("pos")
    if not isinstance(pos, list) or not pos:
        errors.append(f"Word '{normalized_word}': 'pos' must be a non-empty list.")
    else:
        for p in pos:
            if not is_nonempty_string(p):
                errors.append(
                    f"Word '{normalized_word}': POS values must be non-empty strings."
                )
                continue
            # Optional normalization warning
            if p != p.strip():
                warnings.append(
                    f"Word '{normalized_word}': POS '{p}' has extra whitespace."
                )
            if p not in ALLOWED_POS:
                errors.append(
                    f"Word '{normalized_word}': invalid POS '{p}'. "
                    f"Allowed: {sorted(ALLOWED_POS)}"
                )

    english = entry.get("english")
    if not isinstance(english, list) or not english:
        errors.append(f"Word '{normalized_word}': 'english' must be a non-empty list.")
    else:
        for i, gloss_entry in enumerate(english):
            if not isinstance(gloss_entry, dict):
                errors.append(
                    f"Word '{normalized_word}': english[{i}] must be an object."
                )
                continue

            # Enforce required fields in gloss entry
            required_gloss_fields = {"gloss"}
            missing = required_gloss_fields - set(gloss_entry.keys())
            for field in missing:
                errors.append(
                    f"Word '{normalized_word}': english[{i}] missing required field '{field}'."
                )

            gloss = gloss_entry.get("gloss")
            if not is_nonempty_string(gloss):
                errors.append(
                    f"Word '{normalized_word}': english[{i}] missing non-empty 'gloss'."
                )

            weight = gloss_entry.get("weight")
            # weight is optional, but must be numeric if present
            if weight is not None:
                if not isinstance(weight, (int, float)):
                    errors.append(
                        f"Word '{normalized_word}': english[{i}] 'weight' must be numeric."
                    )

        # Optional: warn if multiple glosses but no weights
        if len(english) > 1:
            has_any_weight = any(
                isinstance(g.get("weight"), (int, float)) for g in english
            )
            if not has_any_weight:
                warnings.append(
                    f"Word '{normalized_word}': multiple glosses without weights (recommended)."
                )
    synonyms = entry.get("synonyms")
    if synonyms is not None:
        if not isinstance(synonyms, list):
            errors.append(f"Word '{normalized_word}': 'synonyms' must be a list.")
        else:
            for i, s in enumerate(synonyms):
                if not is_nonempty_string(s):
                    errors.append(
                        f"Word '{normalized_word}': synonyms[{i}] must be a non-empty string."
                    )

    examples = entry.get("examples")
    if examples is not None:
        if not isinstance(examples, list):
            errors.append(f"Word '{normalized_word}': 'examples' must be a list.")
        else:
            for i, ex in enumerate(examples):
                if not isinstance(ex, dict):
                    errors.append(
                        f"Word '{normalized_word}': examples[{i}] must be an object."
                    )
                    continue
                if "zamgrh" in ex and not is_nonempty_string(ex["zamgrh"]):
                    errors.append(
                        f"Word '{normalized_word}': examples[{i}].zamgrh must be a non-empty string."
                    )
                if "english" in ex and not is_nonempty_string(ex["english"]):
                    errors.append(
                        f"Word '{normalized_word}': examples[{i}].english must be a non-empty string."
                    )

    if "confidence" in entry and not isinstance(entry["confidence"], (int, float)):
        errors.append(f"Word '{normalized_word}': 'confidence' must be numeric.")

    if "preferred" in entry and not isinstance(entry["preferred"], bool):
        errors.append(f"Word '{normalized_word}': 'preferred' must be true or false.")


def check_duplicates(words, errors):
    counts = Counter(words)
    duplicates = sorted(word for word, count in counts.items() if count > 1)
    for word in duplicates:
        errors.append(f"Duplicate word entry: '{word}'.")

def build_synonym_map(data):
    synonym_map = {}
    for entry in data:
        word = entry.get("word")
        synonyms = entry.get("synonyms", [])
        if isinstance(word, str) and isinstance(synonyms, list):
            synonym_map[word] = set(synonyms)
        else:
            synonym_map[word] = set()
    return synonym_map


def are_synonyms_fully_linked(words, synonym_map):
    """
    Check if all words are mutually connected via synonyms.
    (Strict mode, but only used for warning suppression for now)
    """
    word_set = set(words)

    for word in word_set:
        linked = synonym_map.get(word, set())
        # Must at least reference all other words in the group
        if not word_set - {word} <= linked:
            return False

    return True


def check_duplicate_glosses(gloss_map, synonym_map, warnings):
    for gloss, words in sorted(gloss_map.items()):
        if len(words) <= 1:
            continue

        words_sorted = sorted(words)

        # Suppress warning if explicitly modeled as synonyms
        if are_synonyms_fully_linked(words_sorted, synonym_map):
            continue

        # Otherwise warn as before
        if len(words_sorted) <= 3:
            warnings.append(
                f"Gloss '{gloss}' has possible synonyms: {words_sorted}"
            )
        else:
            warnings.append(
                f"Gloss '{gloss}' appears in many entries (possible duplication issue): {words_sorted}"
            )

def check_sort_order(words, warnings):
    sorted_words = sorted(words, key=str.lower)
    if words != sorted_words:
        warnings.append("Dictionary is not alphabetically sorted by 'word'.")

def check_invalid_characters(words, errors):
    for word in words:
        invalid_chars = {c for c in word.lower() if c not in ALLOWED_ZAMGRH_CHARS}
        if invalid_chars:
            errors.append(
                f"Word '{word}' contains invalid Zamgrh characters: {sorted(invalid_chars)}"
            )

def main():
    data = load_dictionary(DATA_PATH)

    errors = []
    warnings = []
    seen_words = []
    gloss_map = {}
    synonym_map = build_synonym_map(data)

    for index, entry in enumerate(data, start=1):
        validate_entry(entry, index, seen_words, errors, warnings)

        word = entry.get("word")
        english = entry.get("english", [])

        for gloss_entry in english:
            gloss = gloss_entry.get("gloss")
            if is_nonempty_string(gloss):
                gloss_map.setdefault(gloss, set()).add(word)

    check_duplicates(seen_words, errors)
    check_invalid_characters(seen_words, errors)
    check_sort_order(seen_words, warnings)
    check_duplicate_glosses(gloss_map, synonym_map, warnings)

    if errors:
        print("VALIDATION FAILED")
        print("-" * 40)
        for err in errors:
            print(f"ERROR: {err}")

    if warnings:
        if not errors:
            print("VALIDATION PASSED WITH WARNINGS")
            print("-" * 40)
        else:
            print("-" * 40)
        for warning in warnings:
            print(f"WARNING: {warning}")

    if not errors and not warnings:
        print("VALIDATION PASSED")

    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
