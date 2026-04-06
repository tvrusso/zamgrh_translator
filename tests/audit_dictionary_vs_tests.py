import ast
import sys
from pathlib import Path

# Adjust paths if needed
ROOT = Path(__file__).parent.parent
SRC_DIR = ROOT / "src"
DATA_PATH = ROOT / "data" / "zamgrh_dictionary.json"
TEST_PATH = ROOT / "tests" / "test_translator.py"

sys.path.append(str(SRC_DIR))

from translator import (  # noqa: E402
    load_dictionary,
    build_lookup,
    build_english_pos_lookup,
    clean,
    normalize_morphology,
    AUX_WORDS,
    VERB_LIKE_WORDS,
    DETERMINERS,
)


KNOWN_ENGLISH_LITERALS = {
    # Common English-side tokens used in pipeline/helper/unit tests
    "i", "me", "you", "he", "she", "it", "we", "they",
    "am", "is", "are", "was", "were",
    "eat", "eats", "give", "gives", "go", "goes",
    "try", "tries", "smash", "speak", "come", "run",
    "must", "will", "can", "should", "have", "has", "had",
    "do", "does", "not",
    "a", "an", "the", "my", "your", "his", "her", "our", "their",
    "to", "and", "or", "with", "of", "in", "on",
    "happy", "nice", "bad", "big", "quickly", "often", "alone", "together",
    "group", "gang", "brains", "brain", "human", "humans", "zombie", "zombies",
    "serum", "barricades", "food", "house", "room", "inn", "away", "going",
    "eating", "more", "fast", "scar", "scars",
}

# These "words" are used as nonsense in some helper tests to assure they are
# passed through
KNOWN_FAKE_WORDS = {
    "flargh", "frobnitz",
}

def load_test_ast(test_path: Path) -> ast.AST:
    return ast.parse(test_path.read_text(encoding="utf-8"), filename=str(test_path))


def extract_dict_literal(module: ast.AST, name: str):
    for node in module.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    return ast.literal_eval(node.value)
    raise ValueError(f"Could not find {name} in {TEST_PATH}")


def iter_case_inputs(mapping):
    for _group, cases in mapping.items():
        for case in cases:
            if isinstance(case, (list, tuple)) and len(case) >= 1:
                yield case[0]


def tokenize_zamgrh_input(text: str) -> list[str]:
    return [clean(tok) for tok in text.split() if clean(tok)]


def tokenize_english_input(text: str) -> list[str]:
    tokens = []
    for raw in text.split():
        w = clean(raw)
        if not w:
            continue
        if w == "i":
            w = "I"
        tokens.append(w)
    return tokens


def is_bracket_unknown(expected_output: str, raw_token: str) -> bool:
    return f"[{raw_token}]" in expected_output


def audit_zamgrh_test_vocab(test_groups, lookup):
    missing = {}
    missing_pos = {}
    missing_gloss = {}
    known_unknowns = set()

    for group, cases in test_groups.items():
        for case in cases:
            if not isinstance(case, (list, tuple)) or len(case) < 2:
                continue
            zamgrh_input, expected_output = case[0], case[1]

            for raw in zamgrh_input.split():
                token = clean(raw)
                if not token:
                    continue

                base, _features = normalize_morphology(token, lookup)
                entry = lookup.get(base)

                if entry is None:
                    if is_bracket_unknown(expected_output, raw):
                        known_unknowns.add(token)
                    else:
                        missing.setdefault(token, set()).add(group)
                    continue

                pos = entry.get("pos", [])
                english = entry.get("english", [])

                if not pos:
                    missing_pos.setdefault(base, set()).add(group)

                has_gloss = any(sense.get("gloss") for sense in english)
                if not has_gloss:
                    missing_gloss.setdefault(base, set()).add(group)

    return missing, missing_pos, missing_gloss, known_unknowns


def audit_english_side_inputs(pipeline_unit_tests, helper_unit_tests, eng_lookup):
    missing_eng_pos = {}

    def maybe_flag(token: str, context_name: str):
        if not token:
            return
        low = token.lower()
        if low.endswith("ing"):
            return
        if low.startswith("[") and low.endswith("]"):
            return
        if low in KNOWN_ENGLISH_LITERALS:
            return
        if low in KNOWN_FAKE_WORDS:
            return
        if low in eng_lookup:
            return
        if low.endswith("s") and low[:-1] in eng_lookup:
            return
        if low in {"more", "most"}:
            return
        missing_eng_pos.setdefault(low, set()).add(context_name)

    for step_name, cases in pipeline_unit_tests.items():
        for inp, _expected in cases:
            for token in tokenize_english_input(inp):
                maybe_flag(token, f"PIPELINE_UNIT_TESTS.{step_name}")

    for helper_name, cases in helper_unit_tests.items():
        for context, _expected in cases:
            for key in ("word", "prev", "prev2"):
                token = context.get(key)
                if isinstance(token, str):
                    maybe_flag(token, f"HELPER_UNIT_TESTS.{helper_name}")

    return missing_eng_pos

def fmt_pos(pos_list):
    return ",".join(pos_list) if pos_list else "?"

def find_potential_plural_pairs(entries):
    pairs = set()
    word_map = {e["word"]: e for e in entries if "word" in e}

    for word, entry in word_map.items():
        if word.endswith("z"):
            base = word[:-1]
            if base in word_map:
                base_pos = word_map[base].get("pos", [])
                word_pos = entry.get("pos", [])
                pairs.add(f"{base} ({fmt_pos(base_pos)}) ↔ {word} ({fmt_pos(word_pos)})")

    return pairs

def build_synonym_map(entries):
    synonym_map = {}

    for entry in entries:
        word = entry.get("word")
        synonyms = entry.get("synonyms", []) or []

        for syn in synonyms:
            synonym_map.setdefault(word, set()).add(syn)
            synonym_map.setdefault(syn, set()).add(word)

    return synonym_map

def is_known_synonym_cluster(words, synonym_map):
    word_set = set(words)

    for w in word_set:
        known = synonym_map.get(w, set())
        # If any word is missing links to others → not fully explained
        if not word_set.issubset(known.union({w})):
            return False

    return True

def filter_unexplained_clusters(clusters, synonym_map):
    result = {}

    for gloss, entries in clusters.items():
        words = [word for word, _pos in entries]

        if not is_known_synonym_cluster(words, synonym_map):
            result[gloss] = entries

    return result

def build_gloss_clusters(entries):
    gloss_map = {}

    for entry in entries:
        word = entry.get("word")
        pos = entry.get("pos", [])
        english = entry.get("english", [])

        for gloss_entry in english:
            gloss = gloss_entry.get("gloss")
            if not gloss:
                continue

            gloss_map.setdefault(gloss, []).append((word, pos))

    return gloss_map

def find_multi_word_glosses(gloss_map):
    return {
        gloss: entries
        for gloss, entries in gloss_map.items()
        if len(entries) > 1
    }

def print_section(title: str, items: dict[str, set[str]]):
    print(f"\n=== {title} ===")
    if not items:
        print("None")
        return
    for token in sorted(items):
        groups = ", ".join(sorted(items[token]))
        print(f"- {token}: {groups}")


def print_set_section(title: str, items: set[str], per_line: int = 10):
    print(f"\n=== {title} ===")
    if not items:
        print("None")
        return

    sorted_items = sorted(items)
    for i in range(0, len(sorted_items), per_line):
        chunk = sorted_items[i:i + per_line]
        print(", ".join(chunk))

def print_gloss_clusters(title: str, clusters: dict):
    print(f"\n=== {title} ===")
    if not clusters:
        print("None")
        return

    for gloss in sorted(clusters):
        entries = clusters[gloss]
        formatted = ", ".join(
            f"{word} ({','.join(pos) if pos else '?'})"
            for word, pos in entries
        )
        print(f"- {gloss}: {formatted}")

def main():
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"Dictionary file not found: {DATA_PATH}")
    if not TEST_PATH.exists():
        raise FileNotFoundError(f"Test file not found: {TEST_PATH}")

    data = load_dictionary()
    lookup = build_lookup(data)
    eng_lookup = build_english_pos_lookup(data)

    plural_pairs = find_potential_plural_pairs(data)
    gloss_map = build_gloss_clusters(data)
    multi_glosses = find_multi_word_glosses(gloss_map)

    synonym_map = build_synonym_map(data)
    unexplained_clusters = filter_unexplained_clusters(multi_glosses, synonym_map)

    module = load_test_ast(TEST_PATH)
    test_groups = extract_dict_literal(module, "TEST_GROUPS")
    pipeline_unit_tests = extract_dict_literal(module, "PIPELINE_UNIT_TESTS")
    helper_unit_tests = extract_dict_literal(module, "HELPER_UNIT_TESTS")

    used_zamgrh = set()
    used_english = set()

    # --- Collect usage from TEST_GROUPS ---
    for group, cases in test_groups.items():
        for case in cases:
            if not isinstance(case, (list, tuple)) or len(case) < 2:
                continue

            zamgrh_input, expected_output = case[0], case[1]

            # Zamgrh tokens
            for tok in tokenize_zamgrh_input(zamgrh_input):
                base, _ = normalize_morphology(tok, lookup)
                if base:
                    used_zamgrh.add(base)

            # English tokens
            for tok in tokenize_english_input(expected_output):
                used_english.add(tok.lower())

    # --- Collect usage from PIPELINE_UNIT_TESTS ---
    for step_name, cases in pipeline_unit_tests.items():
        for inp, expected in cases:
            for tok in tokenize_english_input(inp):
                used_english.add(tok.lower())
            for tok in tokenize_english_input(expected):
                used_english.add(tok.lower())

    # --- Collect usage from HELPER_UNIT_TESTS ---
    for helper_name, cases in helper_unit_tests.items():
        for context, expected in cases:
            for key in ("word", "prev", "prev2"):
                token = context.get(key)
                if isinstance(token, str):
                    used_english.add(token.lower())

            if isinstance(expected, tuple):
                for val in expected:
                    if isinstance(val, str):
                        used_english.add(val.lower())

    missing, missing_pos, missing_gloss, known_unknowns = audit_zamgrh_test_vocab(
        test_groups, lookup
    )
    missing_eng_pos = audit_english_side_inputs(
        pipeline_unit_tests, helper_unit_tests, eng_lookup
    )

    dict_words = set()
    dict_glosses = set()

    for entry in data:
        word = entry.get("word")
        if word:
            dict_words.add(word)

            for sense in entry.get("english", []):
                gloss = sense.get("gloss")
                if gloss:
                    dict_glosses.add(gloss.lower())

    unused_words = sorted(dict_words - used_zamgrh)
    unused_glosses = sorted(dict_glosses - used_english)

    print("Dictionary vs Test Audit")
    print("========================")
    print(f"Dictionary entries: {len(data)}")
    print(f"Test groups: {len(test_groups)}")
    print(f"Pipeline unit groups: {len(pipeline_unit_tests)}")
    print(f"Helper unit groups: {len(helper_unit_tests)}")

    print("\n=== STRUCTURAL ISSUES ===")
    print_section("Missing dictionary entries (used in tests)", missing)
    print_section("Entries missing POS", missing_pos)
    print_section("Entries missing English gloss", missing_gloss)
    print_section("English tokens missing POS support", missing_eng_pos)

    print("\n=== LEXICAL SIGNALS ===")
    print_set_section("Intentional unknown tokens (bracketed in tests)", known_unknowns)

    print_set_section("Dictionary entries NOT used in tests", set(unused_words))
    print_set_section("English glosses NOT exercised in tests", set(unused_glosses))
    print_set_section("Potential plural duplicates (consider normalization)", plural_pairs)
    print_gloss_clusters(
        "Gloss clusters needing synonym annotation or review",
        unexplained_clusters
    )

    total_problems = (
        len(missing)
        + len(missing_pos)
        + len(missing_gloss)
        + len(missing_eng_pos)
    )

    coverage_notes = (
        len(unused_words)
        + len(unused_glosses)
    )

    print("\n=== COVERAGE ===")
    print(f"Dictionary coverage: {len(dict_words) - len(unused_words)}/{len(dict_words)} entries used")
    print(f"Gloss coverage: {len(dict_glosses) - len(unused_glosses)}/{len(dict_glosses)} used")

    print("\n=== SUMMARY ===")
    if total_problems == 0:
        print("No structural dictionary-alignment problems found.")
    else:
        print(f"Found {total_problems} structural alignment issue categories.")

    print("\nNote:")
    print("- Intentional nonsense tokens like 'flargh' are okay if tests expect bracketed output.")
    print("- English-side missing POS entries often indicate test literals that bypass the Zamgrh dictionary.")
    print("- This is a light-pass audit, not a full lexical cleanup.")


if __name__ == "__main__":
    main()
