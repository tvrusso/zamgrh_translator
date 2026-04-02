import sys
from pathlib import Path

# Ensure src/ is on path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from translator import (
    load_dictionary,
    build_lookup,
    build_english_pos_lookup,
    zamgrh_to_english,
    zamgrh_to_structure,
    get_pos,
    clean,
    fix_verb_agreement,
    handle_copula,
    handle_auxiliary,
    handle_main_verb,
    detect_subject,
    detect_auxiliary,
    inflect_verb,
)


# ---------------------------
# Translator helper
# ---------------------------

def build_translator():
    data = load_dictionary()
    lookup = build_lookup(data)
    eng_lookup = build_english_pos_lookup(data)

    def run(text, debug=False):
        return zamgrh_to_english(text, lookup, eng_lookup, debug=debug)

    return run, lookup, eng_lookup

# ---------------------------
# Grouped test cases
# ---------------------------

STRUCTURE_TESTS = {
    "basic_structure": [
        (
            "zambah barg bra!nz",
            {
                "subject": "zombie",
                "verb": "eat",
                "object": "brains",
                "plural": False,
                "negated": False,
                "imperative": False,
            },
        ),
        (
            "zambahz barg bra!nz",
            {
                "subject": "zombie",
                "verb": "eat",
                "object": "brains",
                "plural": True,
                "negated": False,
                "imperative": False,
            },
        ),
        (
            "nah g!b bra!nz",
            {
                "subject": None,
                "verb": "give",
                "object": "brains",
                "plural": False,
                "negated": True,
                "imperative": True,
            },
        ),
        (
            "harmanz bah",
            {
                "subject": "human",
                "verb": None,
                "object": None,
                "plural": True,
                "negated": False,
                "imperative": False,
            },
        ),
        (
            "nah ran nahaarh",
            {
                "subject": None,
                "verb": "go",
                "object": None,
                "plural": False,
                "negated": True,
                "imperative": True,
            },
        ),
        (
            "g!b mah bra!nz",
            {
                "subject": None,
                "verb": "give",
                "object": "brains",
                "plural": False,
                "negated": False,
                "imperative": True,
            },
        ),
        (
            "harmanz barg bra!nz",
            {
                "subject": "human",
                "verb": "eat",
                "object": "brains",
                "plural": True,
                "negated": False,
                "imperative": False,
            },
        ),
        (
            "zambahz !z bah",
            {
                "subject": "zombie",
                "verb": "is",
                "object": None,
                "plural": True,
                "negated": False,
                "imperative": False,
            },
        ),
        (
            "nah maz barg bra!nz",
            {
                "subject": None,
                "verb": "eat",
                "object": "brains",
                "plural": False,
                "negated": True,
                "imperative": True,
            },
        ),
        (
            "maz nah barg bra!nz",
            {
                "subject": None,
                "verb": "eat",
                "object": "brains",
                "plural": False,
                "negated": True,
                "imperative": True,
            },
        ),
        (
            "bra!nz maz barg",
            {
                "subject": "brains",
                "verb": "eat",
                "object": None,
                "plural": True,
                "negated": False,
                "imperative": False,
            },
        ),
        (
            "g!b bra!nz",
            {
                "subject": None,
                "verb": "give",
                "object": "brains",
                "plural": False,
                "negated": False,
                "imperative": True,
            },
        ),
    ],
    "subject_pronouns": [
        (
            "mah zambah barg bra!nz",
            {
                "subject": "I",
                "verb": "eat",
                "object": "brains",
                "plural": False,
                "negated": False,
                "imperative": False,
            },
        ),
        (
            "mah zambah maz barg bra!nz",
            {
                "subject": "I",
                "verb": "eat",
                "object": "brains",
                "plural": False,
                "negated": False,
                "imperative": False,
            },
        ),
        (
            "gahz g!b mah bra!nz",
            {
                "subject": "you",
                "verb": "give",
                "object": "brains",
                "plural": True,
                "negated": False,
                "imperative": False,
            },
        ),
]
}

TEST_GROUPS = {

    "core": [
        ("zambahz maz barg bra!nz", "Zombies must eat brains"),
        ("mah zambah bargz bra!nz", "I eat brains"),
        ("zambahz zmazh barragahz", "Zombies smash barricades"),
    ],

    "pronouns": [
        ("g!b gaa bra!nz", "Give you brains"),
        ("gaa g!b mah bra!nz", "You give me brains"),
        ("gab m!z ahz", "Speak with us"),
    ],

    "morphology": [
        ("zambah", "Zombie"),
        ("zambahz", "Zombies"),
        ("harman", "Human"),
        ("harmanz", "Humans"),
        ("bra!n", "Brain"),
        ("bra!nz", "Brains"),
        ("maz", "Must"),
        ("haz", "Have"),
        ("gahz", "Yous"),
    ],

    "MORPHOLOGY_SENTENCES": [
        ("zambahz barg bra!nz", "Zombies eat brains"),
        ("harmanz barg bra!nz", "Humans eat brains"),
        ("zambah barg bra!n", "Zombie eats a brain"),
        ("harman barg bra!nz", "Human eats brains"),
    ],

    "MORPHOLOGY_GUARDRAILS": [
        ("maz", "Must"),
        ("haz", "Have"),
        ("flarghz", "[flarghz]"),
        ("zambahzz", "[zambahzz]"),
        ("mazzz", "[mazzz]"),
        ("hazzz", "[hazzz]"),
    ],

    "MORPHOLOGY_INTERACTIONS": [
        ("harmanz gan ran nahaarh", "Humans will go away"),
        ("zambahz zmazh harmanz", "Zombies smash humans"),
        ("gahz g!b mah bra!nz", "Yous give me brains"),
        ("harmanz zmazh zambahz", "Humans smash zombies"),
        ("zambahz gan ran nahaarh", "Zombies will go away"),
        ("mah zambah maz barg bra!nz", "I must eat brains"),
        ("nah gahz g!b mah bra!nz", "Do not yous give me brains"),
        ("gahz gan barg bra!nz", "Yous will eat brains"),
    ],

    "MORPHOLOGY_REPETITION": [
        ("zambahz zambahz barg bra!nz", "Zombies zombies eat brains"),
        ("gahz gahz g!b bra!nz", "Yous yous give brains"),
    ],

    "gloss_picker": [
        ("mah zambah gan barg bra!nz", "I will eat brains"),
        ("mah gang", "My group"),
        ("g!b mah bra!nz", "Give me brains"),
        ("mah zambah", "I"),
        ("za harman", "The human"),
    ],

     "negation": [
        ("nah g!b bra!nz", "Do not give brains"),
        ("nah ran nahaarh", "Do not go away"),
        ("nah nah g!b bra!nz", "Do not do not give brains"),
    ],

    "questions": [
        ("!z raam azza !nn?", "Is a room at the inn?"),
        ("zambah barg bra!nz?", "Zombie eats brains?"),
    ],

    "imperatives": [
        ("g!b bra!nz", "Give brains"),
        ("g!b mah bra!nz", "Give me brains"),
        ("barg bra!nz", "Eat brains"),
    ],

    "articles_and_plural": [
        ("zambahz barg bra!nz", "Zombies eat brains"),
        ("zambah barg bra!n", "Zombie eats a brain"),
    ],

    "agreement": [
        ("zambah bargz bra!nz", "Zombie eats brains"),
        ("harmanz bah", "Humans are bad"),
        ("harman bah", "Human is bad"),
    ],

    "conjunctions": [
        ("g!b bra!nz an g!b zarram", "Give brains and give a serum"),
        ("g!b bra!nz arh g!b zarram", "Give brains or give a serum"),
    ],

    "unknown_words": [
        ("zambahz flargh bra!nz", "Zombies [flargh] brains"),
    ],

    "edge_cases": [
        ("", ""),
        ("nah", "Do not"),
        ("bra!nz", "Brains"),
    ],

    "duplicate_grammar_triggers": [
        ("zambah !z bah", "Zombie is bad"),          # no double copula
        ("zambahz !z bah", "Zombies are bad"),       # explicit copula + plural normalization
        ("mah zambah gonna barg bra!nz", "I am going to eat brains"),  # no missing "am"
    ],

    "preposition_and_article_collisions": [
        ("g!b bra!nz zaa harman", "Give brains to a human"),
        ("g!b bra!nz zaa zah harman", "Give brains to the human"),
        ("gaam zaa mah", "Come to me"),              # no "to I"
    ],

    "auxiliary_collisions": [
        ("mah zambah maz hab bra!nz", "I must have brains"),
        ("mah zambah gan barg bra!nz", "I will eat brains"),
        ("mah zambah haz barg bra!nz", "I have eat brains"),  # useful as a current-behavior lock if parser is imperfect
    ],

    "copula_vs_lexical_is": [
        ("zambah n!z", "Zombie is nice"),
        ("zambah !z n!z", "Zombie is nice"),
        ("zambah !z !z", "Zombie is"),
    ],

    "unknown_word_mixed_with_known": [
        ("gab flargh ahz", "Speak [flargh] us"),
        ("flargh zambah", "[flargh] zombie"),
        ("zambah flargh harman", "Zombie [flargh] human"),
    ],

    "punctuation_and_case": [
        ("HARRAH!", "Hello"),
        ("G!B BRA!NZ!", "Give brains"),
        ("nah G!B BRA!NZ!", "Do not give brains"),
    ],

    "repeated_words": [
        ("nam nam nam", "Eat eat eat"),
        ("bra!nz bra!nz bra!nz", "Brains brains brains"),
        ("nah nah nah g!b bra!nz", "Do not do not do not give brains"),
    ],

    "plural_normalization_edges": [
        ("harmanz", "Humans"),
        ("zambahz", "Zombies"),
        ("gahz", "Yous"),   # useful if this breaks incorrectly; catches over-eager plural stripping
    ],

    "empty_and_whitespace": [
        ("", ""),
        ("   ", ""),
    ],

    "long_sentences": [
        (
            "mah zambah maz barg bra!nz an zmazh harman",
            "I must eat brains and smash a human"
        ),
        (
            "nah g!b bra!nz arh zambahz zmazh gaa an harman ran nahaarh",
            "Do not give brains or zombies smash you and a human goes away"
        ),
    ],

   "normalization": [
       ("bra!nz.", "Brains"),
       ("BRA!NZ!", "Brains"),
       ("zambah,", "Zombie"),
       ("nah?", "Do not?"),
   ],

   "dictionary_integrity": [
    ("zambah", "Zombie"),
    ("barg", "Eat"),
    ("bra!nz", "Brains"),
   ],

   "stress_tests":  [
    ("zambah maz maz barg bra!nz", "Zombie must eat brains"),
    ("nah maz barg bra!nz", "Do not must eat brains"),
    ("bra!nz maz barg", "Brains must eat"),  # weird structure
   ],

   "stress_pipeline_interactions": [
       # AUX stacking chaos
       ("mah zambah maz gan barg bra!nz", "I must will eat brains"),
       ("mah zambah gan maz barg bra!nz", "I will must eat brains"),

       # NEGATION + AUX conflicts
       ("nah maz barg bra!nz", "Do not must eat brains"),
       ("maz nah barg bra!nz", "Must do not eat brains"),

       # PRONOUN + PREPOSITION collision
       ("g!b gaa zaa mah", "Give you to me"),
       ("gaa zaa gaa", "You to you"),

       # ARTICLE stacking
       ("za zah harman", "The human"),
       ("zah za harman", "The human"),

       # COPULA conflicts
       ("zambah !z maz", "Zombie is must"),
       ("zambah maz !z", "Zombie must is"),

       # WORD ORDER chaos
       ("bra!nz mah g!b", "Brains I give"),
       ("maz bra!nz barg", "Must brains eat"),

       # UNKNOWN + STRUCTURE interaction
       ("mah flargh maz barg bra!nz", "I [flargh] must eat brains"),
       ("flargh maz nah barg", "[flargh] must do not eat"),

       # MULTI-PHRASE chaining
       ("mah zambah maz barg bra!nz an nah g!b gaa",
        "I must eat brains and do not give you"),

       # REPETITION with structure
       ("maz maz maz barg bra!nz", "Must eat brains"),
       ("nah nah maz barg bra!nz", "Do not do not must eat brains"),

       # Determiner repetition
       ("mah mah bra!nz", "My brains"),

   ],

   "decision_tests": [
       # AUX ordering should matter
       ("mah zambah gan barg bra!nz", "I will eat brains"),
       ("mah zambah maz barg bra!nz", "I must eat brains"),

       # Now ambiguous stacking — should NOT behave identically
       ("mah zambah maz gan barg bra!nz", "I must will eat brains"),

       # Pronoun ambiguity
       ("gaa g!b gaa bra!nz", "You give you brains"),

       # Article choice must be consistent
       ("za harman", "The human"),
       ("zah harman", "The human"),  # if both map to "the", fine — but must be consistent

       # Singular vs plural must diverge
       ("zambah barg bra!nz", "Zombie eats brains"),
       ("zambahz barg bra!nz", "Zombies eat brains"),

       # Negation scope ambiguity
       ("nah maz barg bra!nz", "Do not must eat brains"),
       ("maz nah barg bra!nz", "Must do not eat brains"),
   ],
   ## We *could* add these tests in order to guard against breakage
   ## by the agreement refactor, but in fact every one of them is already
   ## tested by tests in a different block and these would be redundant
   # "agreement_refactor_lock": [
   #    ("mah zambah barg bra!nz", "I eat brains"),
   #    ("gaa g!b mah bra!nz", "You give me brains"),
   #    ("gahz g!b mah bra!nz", "Yous give me brains"),
   #    ("zambah barg bra!nz", "Zombie eats brains"),
   #    ("zambahz barg bra!nz", "Zombies eat brains"),
   #    ("harmanz bah", "Humans are bad"),
   #    ("harman bah", "Human is bad"),
}

# Format for pipeline unit tests:
# "function_name" : [
#      ("input","expected output"),
#      ...
#      ],
# ...
PIPELINE_UNIT_TESTS = {
    "fix_verb_agreement": [
        # If already inflected properly, keep it that way
        ("I eat brains", "I eat brains"),
        ("You eat brains", "you eat brains"),
        ("He eats brains", "he eats brains"),
        ("We eat brains", "we eat brains"),
        ("They eat brains", "they eat brains"),
        ("The zombie eats brains", "the zombie eats brains"),
        ("The human eats food", "the human eats food"),
        # no over inflection in input, properly handled on output
        ("He will eat humans", "he will eat humans"),
        ("Zombies will eat brains", "zombies will eat brains"),
        # You edge cases
        ("You give brains", "you give brains"),
        ("You gives brains", "you give brains"),
        # plural, non-pronoun noun subjects
        ("Humans eat brains", "humans eat brains"),
        ("Humans eats brains", "humans eat brains"),
        # Bare noun vs. determiner noun
        ("Zombie eat brains", "zombie eats brains"),
        ("Zombie eats brains", "zombie eats brains"),
        # Auxiliary interference
        ("He must eat brains", "he must eat brains"),
        ("He can eat brains", "he can eat brains"),
        # multi-word subject
        ("The big zombie eats brains", "the big zombie eats brains"),
        ("The big zombie eat brains", "the big zombie eats brains"),
        # Sentence start verbs
        ("Eat brains", "eat brains"),
        ("Eats brains", "eats brains"),
        # copula interaction
        ("I is happy", "I am happy"),
        ("He are happy", "he is happy"),
        ("They is happy", "they are happy"),
        # improperly inflected input
        ("It go away", "it goes away"),
        ("He give brains", "he gives brains"),
        ("She eat brains", "she eats brains"),
        ("Zombies will eats brains", "zombies will eat brains"),
        ("He must eats brains", "he must eat brains"),
        ("The zombie eat brains", "the zombie eats brains"),
        ("Zombie eat brains", "zombie eats brains"),
        # subject separated by prepositional phrase
        ("The zombie with scars eat brains", "the zombie with scars eats brains"),
        ("The zombies with a scar eats brains", "the zombies with a scar eat brains"),
        # "of" phrases
        ("The group of zombies eat brains", "the group of zombies eats brains"),
        ("A group of zombies gab", "a group of zombies gabs"),
        # intervening adverbs
        ("The zombie quickly eat brains", "the zombie quickly eats brains"),
        ("Zombies often eats brains", "zombies often eat brains"),
        # compound subjects
        ("The zombie and the human eats brains", "the zombie and the human eat brains"),
        ("Brains and blood is tasty", "brains and blood are tasty"),
        # pronoun + modifier separation
        ("He alone eat brains", "he alone eats brains"),
        ("They together eats brains", "they together eat brains"),
        # inverted or unusual order
        ("In the room the zombie eat brains", "in the room the zombie eats brains"),
        # gerund/verb confusion blockers
        ("The zombie eating brains eat more", "the zombie eating brains eats more"),
        ("The zombie in the house eat brains","the zombie in the house eats brains"),
    ]
}

HELPER_UNIT_TESTS = {
    "handle_copula": [
        ({"word":"is","pos":set(),
          "prev":"I","prev_pos":set(),
          "prev2":None,"prev2_pos":set()},
         ("am", True)),
        ({"word":"is","pos":set(),
          "prev":"they","prev_pos":set(),
          "prev2":None,"prev2_pos":set()},
         ("are", True)),
        ({"word":"are","pos":set(),
          "prev":"he","prev_pos":set(),
          "prev2":None,"prev2_pos":set()},
         ("is", True)),
        ({"word":"eat","pos":set(),
          "prev":"I","prev_pos":set(),
          "prev2":None,"prev2_pos":set()},
         ("eat", False)),
        ({"word":"is","pos":set(),
          "prev":"Zombies","prev_pos":set(),
          "prev2":None,"prev2_pos":set()},
         ("are", True)),
        ({"word":"are","pos":set(),
          "prev":"Zombie","prev_pos":set(),
          "prev2":None,"prev2_pos":set()},
         ("is", True)),
    ],
    "handle_auxiliary": [
        ({"word":"must","pos":set(),
          "prev":None,"prev_pos":set(),
          "prev2":None,"prev2_pos":set()},
         ("must",True)),
        # Not a real word, but we're testing that if we say it's an aux
        # then it's treated as an aux
        ({"word":"frobnitz","pos":"aux",
          "prev":None,"prev_pos":set(),
          "prev2":None,"prev2_pos":set()},
         ("frobnitz",True)),
        # We shouldn't handle this in this helper
        ({"word":"frobnitz","pos":"noun",
          "prev":None,"prev_pos":set(),
          "prev2":None,"prev2_pos":set()},
         ("frobnitz",False)),
    ],
    "handle_main_verb": [
        # --- No subject → no change ---
        (
            {"word":"eat","pos":{"verb"},
             "prev":None,"prev_pos":set(),
             "prev2":None,"prev2_pos":set()},
            ("eat", False)
        ),

        # --- Simple pronoun subjects ---
        (
            {"word":"eat","pos":{"verb"},
             "prev":"he","prev_pos":set(),
             "prev2":None,"prev2_pos":set()},
            ("eats", True)
        ),
        (
            {"word":"eats","pos":{"verb"},
             "prev":"they","prev_pos":set(),
             "prev2":None,"prev2_pos":set()},
            ("eat", True)
        ),
        (
            {"word":"eat","pos":{"verb"},
             "prev":"I","prev_pos":set(),
             "prev2":None,"prev2_pos":set()},
            ("eat", False)
        ),

        # --- Noun subjects ---
        (
            {"word":"eat","pos":{"verb"},
             "prev":"Zombie","prev_pos":{"noun"},
             "prev2":None,"prev2_pos":set()},
            ("eats", True)
        ),
        (
            {"word":"eats","pos":{"verb"},
             "prev":"Zombies","prev_pos":{"noun"},
             "prev2":None,"prev2_pos":set()},
            ("eat", True)
        ),

        # --- Verb-like previous blocks subject detection ---
        (
            {"word":"eat","pos":{"verb"},
             "prev":"must","prev_pos":{"aux"},
             "prev2":None,"prev2_pos":set()},
            ("eat", False)
        ),

        # --- Auxiliary blocking (prev) ---
        # "he must eats" -> "eat"
        (
            {"word":"eats","pos":{"verb"},
             "prev":"must","prev_pos":{"aux"},
             "prev2":"he","prev2_pos":set()},
            ("eat", True) 
        ),

        # --- Auxiliary blocking (prev2) ---
        # must eat eats -> eat
        (
            {"word":"eats","pos":{"verb"},
             "prev":"eat","prev_pos":{"verb"},
             "prev2":"must","prev2_pos":{"aux"}},
            ("eat", True)
        ),

        # --- Inflection rules: y → ies ---
        (
            {"word":"try","pos":{"verb"},
             "prev":"he","prev_pos":set(),
             "prev2":None,"prev2_pos":set()},
            ("tries", True)
        ),

        # --- Inflection rules: es endings ---
        (
            {"word":"go","pos":{"verb"},
             "prev":"he","prev_pos":set(),
             "prev2":None,"prev2_pos":set()},
            ("goes", True)
        ),

        # --- Reverse inflection (plural subject) ---
        (
            {"word":"tries","pos":{"verb"},
             "prev":"they","prev_pos":set(),
             "prev2":None,"prev2_pos":set()},
            ("try", True)
        ),

        # --- Edge: already correct, no change ---
        (
            {"word":"eats","pos":{"verb"},
             "prev":"he","prev_pos":set(),
             "prev2":None,"prev2_pos":set()},
            ("eats", False)
        ),

        # --- Non-verb should be ignored ---
        (
            {"word":"brains","pos":{"noun"},
             "prev":"he","prev_pos":set(),
             "prev2":None,"prev2_pos":set()},
            ("brains", False)
        ),
    ],
    "detect_subject": [
        # pronouns
        (
            {"prev": "he", "prev_pos": set(), "word": "eat", "pos": {"verb"}},
            (True, True)  # has_subject, is_third_person
        ),
        (
            {"prev": "they", "prev_pos": set(), "word": "eat", "pos": {"verb"}},
            (True, False)
        ),
        (
            {"prev": "I", "prev_pos": set(), "word": "eat", "pos": {"verb"}},
            (True, False)
        ),

        # noun subjects
        (
            {"prev": "zombie", "prev_pos": {"noun"}, "word": "eat", "pos": {"verb"}},
            (True, True)
        ),
        (
            {"prev": "zombies", "prev_pos": {"noun"}, "word": "eat", "pos": {"verb"}},
            (True, False)
        ),

        # blocked by verb-like previous word
        (
            {"prev": "will", "prev_pos": {"aux"}, "word": "eat", "pos": {"verb"}},
            (False, False)
        ),
        (
            {"prev": "eat", "prev_pos": {"verb"}, "word": "brains", "pos": {"noun"}},
            (False, False)
        ),

        # no subject
        (
            {"prev": None, "prev_pos": set(), "word": "eat", "pos": {"verb"}},
            (False, False)
        ),
    ],
    "inflect_verb": [
        # third person singular
        (
            {"word": "eat", "is_third_person": True, "has_subject": True, "has_aux": False},
            ("eats", True)
        ),
        (
            {"word": "go", "is_third_person": True, "has_subject": True, "has_aux": False},
            ("goes", True)
        ),
        (
            {"word": "try", "is_third_person": True, "has_subject": True, "has_aux": False},
            ("tries", True)
        ),

        # plural / non-third-person
        (
            {"word": "eats", "is_third_person": False, "has_subject": True, "has_aux": False},
            ("eat", True)
        ),

        # already correct → no change
        (
            {"word": "eat", "is_third_person": False, "has_subject": True, "has_aux": False},
            ("eat", False)
        ),

        # blocked by auxiliary
        (
            {"word": "eat", "is_third_person": True, "has_subject": True, "has_aux": True},
            ("eats", True)
        ),
        (
            {"word": "eats", "is_third_person": True, "has_subject": True, "has_aux": True},
            ("eats", False)
        ),

        # no subject → no change
        (
            {"word": "eat", "is_third_person": True, "has_subject": False, "has_aux": False},
            ("eats", True)
        ),
    ],
    "detect_auxiliary": [
        (   # he must eat
            {"word": "eat", "prev": "must", "prev2": "he", "prev2_pos": set()},
            True
        ),
        (   # zombies will eat
            {"word": "eat", "prev": "will", "prev2": "zombies", "prev2_pos": set()},
            True
        ),
    ],
}

# Invariant tests
def check_invariants(sentence: str, lookup, eng_lookup) -> list[str]:
    issues = []
    words = sentence.lower().split()

    COLLAPSIBLE = {"must", "will", "can", "should", "have", "is", "are", "am", "the", "a", "an"}
    ARTICLES = {"a", "an", "the"}
    VOWELS = set("aeiou")

    for i in range(1, len(words)):
        if words[i] == words[i - 1] and words[i] in COLLAPSIBLE:
            issues.append(f"duplicate '{words[i]}'")

    for i in range(len(words) - 1):
        if words[i] in {"a", "an"} and words[i + 1].endswith("s"):
            issues.append("article before plural")

    for i in range(len(words) - 1):
        if words[i] == "a" and words[i + 1][0] in VOWELS:
            issues.append("use 'an' before vowel")
        if words[i] == "an" and words[i + 1][0] not in VOWELS:
            issues.append("use 'a' before consonant")

    for i in range(len(words) - 1):
        if words[i] in ARTICLES and words[i + 1] in ARTICLES:
            issues.append("stacked determiners")

    if sentence and sentence[0].islower():
        issues.append("sentence not capitalized")

    VERB_LIKE = {"eat", "give", "go", "smash", "speak", "come", "run", "have", "is", "are", "am", "must", "will", "can", "should", "do", "does"}

    if "i" in words:
        for idx, w in enumerate(words[:-1]):
            if w == "i":
                nxt = words[idx + 1]
                nxt_pos = get_pos(nxt, lookup, eng_lookup)

                next_is_noun = "noun" in nxt_pos
                next_is_verb_like = (
                    "verb" in nxt_pos
                    or "aux" in nxt_pos
                    or nxt in VERB_LIKE
                )

                if next_is_noun and not next_is_verb_like:
                    issues.append("'I' before noun (likely missing determiner conversion)")

    return issues

# ---------------------------
# Test runner
# ---------------------------

def run_tests(verbose=False):
    translator, lookup, eng_lookup = build_translator()
    passed = 0
    failed = 0

    for group, cases in TEST_GROUPS.items():
        print(f"\n=== {group.upper()} ===")
        group_passed=0
        group_failed=0

        for zamgrh, expected in cases:
            result = translator(zamgrh)

            inv_errors = check_invariants(result, lookup, eng_lookup)
            if inv_errors:
                print(f"FAIL (invariant): {zamgrh}")
                print(f"  result: {result}")
                print(f"  issues: {inv_errors}")
                failed += 1
                group_failed +=1
                continue

            if result == expected:
                if (verbose):
                    print(f"PASS: {zamgrh}")
                passed += 1
                group_passed += 1
            else:
                print(f"FAIL: {zamgrh}")
                print(f"  expected: {expected}")
                print(f"  got:      {result}")

                # 🔍 Debug pipeline
                print(f"\nDEBUG for {zamgrh}:")
                translator(zamgrh, debug=True)

                # 🔍 Structure insight (NEW)
                structure = zamgrh_to_structure(zamgrh, lookup)
                print(f"[structure] {structure}")

                failed += 1
                group_failed +=1
        print(f"Group tests passed: {group_passed}")
        print(f"Group tests failed: {group_failed}")
    print("\n---")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")

    return failed == 0

def run_structure_tests(verbose=False):
    data = load_dictionary()
    lookup = build_lookup(data)

    passed = 0
    failed = 0

    for group, cases in STRUCTURE_TESTS.items():
        group_passed=0
        group_failed=0
        print(f"\n=== STRUCTURE: {group.upper()} ===")
        for zamgrh, expected in cases:
            result = zamgrh_to_structure(zamgrh, lookup)

            if result == expected:
                if (verbose):
                    print(f"PASS: {zamgrh}")
                passed += 1
                group_passed +=1
            else:
                print(f"FAIL: {zamgrh}")
                print(f"  expected: {expected}")
                print(f"  got:      {result}")
                failed += 1
                group_failed +=1

        print(f"Group tests passed: {group_passed}")
        print(f"Group tests failed: {group_failed}")
    print("\n---")
    print(f"Structure Passed: {passed}")
    print(f"Structure Failed: {failed}")
    return failed == 0

def run_pipeline_unit_tests(verbose=False):
    data = load_dictionary()
    lookup = build_lookup(data)
    eng_lookup = build_english_pos_lookup(data)

    passed=0
    failed=0

    for step_name, cases in PIPELINE_UNIT_TESTS.items():
        func = globals()[step_name]

        print(f"\n=== PIPELINE: {step_name} ===")
        step_passed=0
        step_failed=0
        for inp, expected in cases:
            raw_words = inp.split()
            words = []
            for raw in raw_words:
                w = clean(raw)
                if w == "i":
                    w = "I"
                words.append(w)
            result = func(words, lookup, eng_lookup)
            sentence = " ".join(result)
            if sentence == expected:
                if (verbose):
                    print(f"PASS: {inp}->{sentence}")
                passed += 1
                step_passed +=1
            else:
                print(f"FAIL: {inp}")
                print(f"  expected: {expected}")
                print(f"  got:      {sentence}")
                failed += 1
                step_failed +=1
        print(f"Step tests passed: {step_passed}")
        print(f"Step tests failed: {step_failed}")
    print("\n---")
    print(f"Unit tests Passed: {passed}")
    print(f"Unit tests Failed: {failed}")
    return failed == 0

def run_pipeline_helper_unit_tests(verbose=False):
    data = load_dictionary()
    lookup = build_lookup(data)
    eng_lookup = build_english_pos_lookup(data)

    passed=0
    failed=0

    for func_name, cases in HELPER_UNIT_TESTS.items():
        func_passed=0
        func_failed=0
        func = globals()[func_name]
        print(f"\n=== HELPER: {func_name} ===")

        for base_context, expected in cases:
            # augment context
            context = dict(base_context)  # shallow copy

            # ensure required fields exist
            context.setdefault("lookup", lookup)
            context.setdefault("eng_lookup", eng_lookup)
            context.setdefault("result_so_far", build_result_stub(context))

            result = func(context)

            if result == expected:
                if (verbose):
                    print(f"PASS: {base_context}->{result}")
                passed += 1
                func_passed +=1
            else:
                print(f"FAIL: {base_context}")
                print(f"  expected: {expected}")
                print(f"  got:      {result}")
                failed += 1
                func_failed +=1
        print(f"Func tests passed: {func_passed}")
        print(f"Func tests failed: {func_failed}")
    print("\n---")
    print(f"Helper Passed: {passed}")
    print(f"Helper Failed: {failed}")
    return failed == 0

def build_result_stub(context):
    result = []

    if context.get("prev2"):
        result.append(context["prev2"])
    if context.get("prev"):
        result.append(context["prev"])

    return result

if __name__ == "__main__":
    verbose = False
    command_line_args = sys.argv
    if ("--verbose" in command_line_args):
        verbose=True

    success_translation = run_tests(verbose)
    success_structure = run_structure_tests(verbose)
    success_pipeline_helper_unit = run_pipeline_helper_unit_tests(verbose)
    success_pipeline_unit = run_pipeline_unit_tests(verbose)

    if (not success_pipeline_helper_unit):
        print(f"One or more pipeline helper unit tests failed!")

    if (not success_pipeline_unit):
        print(f"One or more pipeline unit tests failed!")

    if (not success_structure):
        print(f"One or more structure tests failed!")

    if (not success_translation):
        print(f"One or more translation tests failed!")

    if (success_translation and success_structure and success_pipeline_unit):
        print(f"All test types passed.")

    sys.exit(0 if (success_translation and success_structure and success_pipeline_unit) else 1)
