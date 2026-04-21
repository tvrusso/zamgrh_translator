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
    resolve_hab_ambiguity,
    simplify_subject,
    fix_possession,
    fix_object_pronouns,
    collapse_repeated_pronouns,
    fix_determiners,
    fix_prepositions,
    insert_copula,
    insert_articles,
    dedupe_function_words,
    fix_am_progressive,
    fix_verb_agreement,
    handle_copula,
    handle_auxiliary,
    handle_main_verb,
    detect_subject,
    detect_auxiliary,
    inflect_verb,
    normalize_morphology,
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
                "subject": "zombies",
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
                "subject": "humans",
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
                "subject": "humans",
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
                "subject": "zombies",
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
            "gah g!b mah zambah bra!nz",
            {
                "subject": "you",
                "verb": "give",
                "object": "brains",
                "plural": False,
                "negated": False,
                "imperative": False,
            },
        ),
]
}
TEST_GROUPS = {
    # =========================
    # LEXICAL (word-level)
    # =========================
    "lexical": [
        ("BRA!NZ!", "Brains"),
        ("an", "And"),
        ("anz", "End"),
        ("bang!ng", "Shooting"),
        ("barg", "Eat"),
        ("bargz", "Eat"),
        ("barg!ng", "Eating"),
        ("barg!ngz", "Eatings"),
        ("bra!n", "Brain"),
        ("bra!nz", "Brains"),
        ("bra!nz.", "Brains"),
        ("flargh", "[flargh]"),
        ("flarghz", "[flarghz]"),
        ("flargh!ng", "[flargh!ng]"),
        ("gahz", "You"),
        ("harman", "Human"),
        ("harmanz", "Humans"),
        ("haz", "Have"),
        ("hazzz", "[hazzz]"),
        ("maz", "Must"),
        ("mazzz", "[mazzz]"),
        ("nah", "Do not"),
        ("nah?", "Do not?"),
        ("zambah", "Zombie"),
        ("zambah,", "Zombie"),
        ("zambahz", "Zombies"),
        ("zambahzz", "[zambahzz]")
    ],
    # =========================
    # GRAMMAR (core behavior)
    # =========================
    "grammar": [
        ("!z raam azza !nn?", "Is a room at the inn?"),
        ("barg bra!nz", "Eat brains"),
        ("g!b bra!nz", "Give brains"),
        ("g!b gaa bra!nz", "Give you brains"),
        ("gaa g!b mah zambah bra!nz", "You give me brains"),
        ("gab m!z ahz", "Speak with us"),
        ("harman bah", "Human is bad"),
        ("harman barg bra!nz", "Human eats brains"),
        ("harmanz bah", "Humans are bad"),
        ("harmanz barg bra!nz", "Humans eat brains"),
        ("mah zambah", "I"),
        ("mah zambah bargz bra!nz", "I eat brains"),
        ("nah g!b bra!nz", "Do not give brains"),
        ("nah nah g!b bra!nz", "Do not do not give brains"),
        ("nah ran nahaarh", "Do not go away"),
        ("za harman", "The human"),
        ("zambah !z !z", "Zombie is"),
        ("zambah !z bah", "Zombie is bad"),
        ("zambah !z n!z", "Zombie is nice"),
        ("zambah barg bra!n", "Zombie eats a brain"),
        ("zambah barg bra!nz?", "Zombie eats brains?"),
        ("zambah bargz bra!nz", "Zombie eats brains"),
        ("zambah n!z", "Zombie is nice"),
        ("zambahz !z bah", "Zombies are bad"),
        ("zambahz barg bra!nz", "Zombies eat brains"),
        ("zambahz maz barg bra!nz", "Zombies must eat brains"),
        ("zambahz zmazh barragahz", "Zombies smash barricades")
    ],
    # =========================
    # INTERACTIONS (multi-feature)
    # =========================
    "interactions": [
        ("Harmanz azza barragahz", "Humans at the barricades"),
        ("Mah zambah nah zrazz zam", "I do not trust them"),
        ("Zmazh zah barragah", "Smash the barricade"),
        ("abbarz barg", "Apples eat"),
        ("g!b bra!nz an g!b zarram", "Give brains and give a serum"),
        ("g!b bra!nz arh g!b zarram", "Give brains or give a serum"),
        ("g!b bra!nz zaa harman", "Give brains to a human"),
        ("g!b bra!nz zaa zah harman", "Give brains to the human"),
        ("g!b mah zambah bra!nz", "Give me brains"),
        ("gaa zaa gaa", "You to you"),
        ("gaam zaa mah zambah", "Come to me"),
        ("gahz g!b mah zambah bra!nz", "You give me brains"),
        ("gahz gan barg bra!nz", "You will eat brains"),
        ("harmanz gan ran nahaarh", "Humans will go away"),
        ("harmanz zmazh zambahz", "Humans smash zombies"),
        ("mah gang", "My group"),
        ("mah zambah bargz", "I eat"),
        ("mah zambah gan barg bra!nz", "I will eat brains"),
        ("mah zambah ganna barg bra!nz", "I am going to eat brains"),
        ("mah zambah haz barg bra!nz", "I have eat brains"),
        ("mah zambah maz barg bra!nz", "I must eat brains"),
        ("mah zambah maz hab bra!nz", "I must have brains"),
        ("nah nah", "Do not do not"),
        ("za zah harman", "The human"),
        ("za zah harman barg", "The human eats"),
        ("zah harman", "The human"),
        ("zah za harman", "The human"),
        ("zah za harman barg", "The human eats"),
        ("zambahz gan ran nahaarh", "Zombies will go away"),
        ("zambahz zmazh harmanz", "Zombies smash humans")
    ],
    # =========================
    # ROBUSTNESS / EDGE CASES
    # =========================
    "robustness": [
        ("", ""),
        ("   ", ""),
        ("Barg!ng bra!nz", "Eating brains"),
        ("G!B BRA!NZ!", "Give brains"),
        ("HARRAH!", "Hello"),
        ("Mah zambah maz ma!g razbarh zaa za narz", "I must make report to the nurse"),
        ("Zah barg!ng zambah !z habbah", "The eating zombie is happy"),
        ("Zah zambah !z brh!ng!ng barhah", "The zombie is bringing barhah"),
        ("arh zambah barg bra!nz", "Or zombie eats brains"),
        ("bangbangman nah bang mah zambah mah zambah !z n!z",
         "Headhunter do not shoot me I am nice"),
        ("barg zambah bra!nz", "Eat zombie brains"),
        ("bargz zambah", "Eat a zombie"),
        ("bargz bargz", "Eat eat"),
        ("bra!nz bra!nz", "Brains brains"),
        ("bra!nz bra!nz bra!nz", "Brains brains brains"),
        ("bra!nz mah zambah g!b", "Brains I give"),
        ("bra!nz zambah bargz", "Brains zombie eat"),
        ("eats the zombie", "[eats] [the] [zombie]"),
        ("flargh an zambah barg bra!nz", "[flargh] and zombie eats brains"),
        ("flargh flargh", "[flargh] [flargh]"),
        ("flargh maz nah barg", "[flargh] must do not eat"),
        ("flargh zambah", "[flargh] zombie"),
        ("flargh!ng zambah", "[flargh!ng] zombie"),
        ("flarghz barg", "[flarghz] eat"),
        ("g!b", "Give"),
        ("g!b an bra!nz", "Give and brains"),
        ("g!b bra!nz an g!b zarram an g!b gaa harman",
         "Give brains and give a serum and gives you a human"),
        ("g!b bra!nz arh g!b zarram arh g!b barragahz",
         "Give brains or give a serum or gives barricades"),
        ("g!b flargh zaa harman", "Give [flargh] to a human"),
        ("g!b gaa zaa mah zambah", "Give you to me"),
        ("gaa g!b gaa bra!nz", "You give you brains"),
        ("gab flargh ahz", "Speak [flargh] us"),
        ("gahz gahz", "You you"),
        ("gahz gahz g!b bra!nz", "You you give brains"),
        ("mah flargh maz barg bra!nz", "My [flargh] must eat brains"),
        ("mah mah bra!nz", "My brains"),
        ("mah zambah !z barg", "I am eat"),
        ("mah zambah flargh an gaa flargh", "I [flargh] and you [flargh]"),
        ("mah zambah maz barg bra!nz an nah g!b gaa",
         "I must eat brains and do not give you"),
        ("mah zambah maz barg bra!nz an zmazh harman an ran nahaarh",
         "I must eat brains and smash a human and goes away"),
        ("maz bra!nz barg", "Must brains eat"),
        ("maz gan barg bra!nz", "Must will eat brains"),
        ("maz maz", "Must"),
        ("maz nah gan barg bra!nz", "Must do not will eat brains"),
        ("nah G!B BRA!NZ!", "Do not give brains"),
        ("nah flargh ran nahaarh", "Do not [flargh] go away"),
        ("nah g!b bra!nz an nah ran nahaarh", "Do not give brains and do not go away"),
        ("nah maz gan barg bra!nz", "Do not must will eat brains"),
        ("nah nah nah", "Do not do not do not"),
        ("nah nah nah g!b bra!nz", "Do not do not do not give brains"),
        ("nam nam nam", "Eat eat eat"),
        ("ran", "Go"),
        ("the zombie eats", "[the] [zombie] [eats]"),
        ("za harman barg", "The human eats"),
        ("zambah !z !z bah", "Zombie is bad"),
        ("zambah !z maz", "Zombie is must"),
        ("zambah an arh barg", "Zombie and or eats"),
        ("zambah barg bra!nz", "Zombie eats brains"),
        ("zambah barg bra!nz an harman ran nahaarh",
         "Zombie eats brains and a human go away"),
        ("zambah barg bra!nz arh harman barg zarram",
         "Zombie eats brains or a human eat a serum"),
        ("zambah flargh harman", "Zombie [flargh] human"),
        ("zambah maz !z", "Zombie must is"),
        ("zambah the eats", "Zombie [the] [eats]"),
        ("zambah za barg", "Zombie the eats"),
        ("zambah zah barg", "Zombie the eats"),
        ("zambah zambah", "Zombie zombie"),
        ("zambahz flargh bra!nz", "Zombies [flargh] brains"),
        ("zambahz zambahz barg bra!nz", "Zombies zombies eat brains"),
        ("zambahz zmazh harmanz an harmanz gan ran nahaarh arh zambah barg bra!nz",
         "Zombies smash humans and humans will go away or a zombie eats brains"),
        ("zombie the eats", "[zombie] [the] [eats]")
    ],
    # =========================
    # LONG / STRESS
    # =========================
    "stress": [
        ("bra!nz maz barg", "Brains must eat"),
        ("flarghz barg!ng bra!nz", "[flarghz] eating brains"),
        ("mah zambah gan maz barg bra!nz", "I will must eat brains"),
        ("mah zambah ganna barg bra!nz an g!b gaa zaa harman",
         "I am going to eat brains and give you to a human"),
        ("mah zambah maz barg bra!nz an zmazh harman", "I must eat brains and smash a human"),
        ("mah zambah maz gan barg bra!nz", "I must will eat brains"),
        ("maz maz maz barg bra!nz", "Must eat brains"),
        ("maz nah barg bra!nz", "Must do not eat brains"),
        ("nah g!b bra!nz arh zambahz zmazh gaa an harman ran nahaarh",
         "Do not give brains or zombies smash you and a human goes away"),
        ("nah mah zambah maz gan barg bra!nz an flargh zaa gaa",
         "Do not I must will eat brains and [flargh] to you"),
        ("nah maz barg bra!nz", "Do not must eat brains"),
        ("nah nah maz barg bra!nz", "Do not do not must eat brains"),
        ("zambah maz maz barg bra!nz", "Zombie must eat brains")
    ],
    # =========================
    # LEXICON / COVERAGE
    # =========================
    "lexicon_expansion": [
        ("abbar", "Apple"),
        ("abbarz", "Apples"),
        ("ambra!z barhah", "Embrace barhah"),
        ("anz ahb rarr", "End of world"),
        ("arrh zah bra!nz", "All the brains"),
        ("arrh zambahz maz barg bra!nz", "All zombies must eat brains"),
        ("brh!ng", "Bring"),
        ("g!az g!b arrh zah bra!nz", "Just give all the brains"),
        ("g!az g!b bra!nz", "Just give brains"),
        ("gannarazarh", "Generator"),
        ("graab", "Grab"),
        ("habbahnazz", "Happiness"),
        ("harmanbargar", "Humanburger"),
        ("harmanbargarz", "Humanburgers"),
        ("mabb", "Move"),
        ("nabazz!h g!az ran", "Nobody just go"),
        ("nabazz!h mabb", "Nobody move"),
        ("nabazz!h ran", "Nobody go"),
        ("z!z bag", "This bag"),
        ("zah anz ahb zah rarr", "The end of the world"),
        ("zgam", "Scum")
    ],
    # =========================
    # KNOWN BAD
    # =========================
    "known_bad": [
        ("G!b mah zambah abbar", "Give an me apple"),
        ("Grahm haarh harman, mah habbah gang maz barg bra!nz",
         "Come a here human my happy group must eat brains"),
        ("Na, gaa maz nah bang zambahz, bangbangman",
         "No you must do not shoot zombies a headhunter"),
        ("ambra!z!ng", "Embraceing"),
        ("nah gahz g!b mah zambah bra!nz", "Do not you give me brains"),
        ("z!z !z zah anz ahb zah rarr", "This are the end of the world")]
 }

# Format for pipeline unit tests:
# "function_name" : [
#      ("input","expected output"),
#      ...
#      ],
# ...
PIPELINE_UNIT_TESTS = {
    "resolve_hab_ambiguity": [
        ("help me","help me"),
        ("I help a brain", "I have a brain"),
        ("help the human", "help the human"),
        ("zombies help humans", "zombies help humans"),
        ## BAD  These unit tests indicate problems that must be ultimately
        ##      be fixed
        # in these cases, "help" is inappropriately changed to "have"
        ("I help a human","I have a human"),
        ("I help a zombie", "I have a zombie"),
        ("the zombie must help the human", "the zombie must have the human"),
    ],
    # Note that "simplify" subject does NOT fix object pronouns and is not
    # supposed to!
    "simplify_subject": [
        ("My zombie", "I"),
        ("My zombie must", "I must"),
        ("give a brain to my zombie", "give a brain to I"),
    ],
    "fix_possession": [
        # This function is currently a no-op
    ],
    "fix_object_pronouns": [
        ("give I brains", "give me brains"),
        ("eat I", "eat me"),
        ("smash I", "smash me"),
        ("have I brains", "have me brains"),
        ("I give brains", "I give brains"),
        ("the I brains", "the I brains"),
        ("give you brains", "give you brains"),
    ],
    "collapse_repeated_pronouns": [
        ("I I brain", "I brain"),
        ("give a brain to me me me","give a brain to me"),
        ("I I I want my mtv", "I want my mtv"),
    ],
    "fix_determiners": [
        ("I brains", "my brains"),
        ("I brain", "my brain"),
        ("I group", "my group"),
        ("I gang", "my gang"),
        ("I eat brains", "I eat brains"),
        ("I will eat brains", "I will eat brains"),
        ("I zombie eat brains", "I zombie eat brains"),
        ("give I brains", "give my brains"),
    ],
    "fix_prepositions": [
        ("to I", "to me"),
        ("go to I", "go to me"),
        ("give brains to I", "give brains to me"),
        ("I go", "I go"),
        ("to you", "to you"),
    ],
    "insert_copula": [
        ("zombie bad", "zombie is bad"),
        ("zombies bad", "zombies are bad"),
        ("human nice", "human is nice"),
        ("brains nice", "brains are nice"),
        ("zombie is bad", "zombie is bad"),
        ("zombie eat bad", "zombie eat bad"),
        ("[flargh] bad", "flargh bad"),
    ],
    "insert_articles": [
        ("eat brain", "eat a brain"),
        ("eat brains", "eat brains"),
        ("give brain", "give a brain"),
        ("go to human", "go to a human"),
        ("go to humans", "go to humans"),
        ("eat the brain", "eat the brain"),
        ("zombie eat brain", "zombie eat a brain"),
        ("zombie eat big brain", "zombie eat a big brain"),
    ],
    "dedupe_function_words": [
        ("the the human", "the human"),
        ("a a brain", "a brain"),
        ("an an inn", "an inn"),
        ("is is bad", "is bad"),
        ("are are bad", "are bad"),
        ("must must eat", "must eat"),
        ("will will go", "will go"),
        ("brains brains", "brains brains"),
        ("bad bad", "bad bad"),
    ],
    "fix_am_progressive": [
        ("I going to eat brains", "I am going to eat brains"),
        ("I going to go", "I am going to go"),
        ("I going fast", "I going fast"),
        ("you going to eat brains", "you going to eat brains"),
        ("I am going to eat brains", "I am going to eat brains"),
        ("zombie going to eat brains", "zombie going to eat brains"),
    ],
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
        ("Brains and human is nice", "brains and human are nice"),
        # pronoun + modifier separation
        ("He alone eat brains", "he alone eats brains"),
        ("They together eats brains", "they together eat brains"),
        # inverted or unusual order
        ("In the room the zombie eat brains", "in the room the zombie eats brains"),
        # gerund/verb confusion blockers
        ("The zombie eating brains eat more", "the zombie eating brains eats more"),
        ("The zombie in the house eat brains", "the zombie in the house eats brains"),
    ],

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

MORPHOLOGY_UNIT_TESTS = [
    # base case
    ("zambah", ("zambah", {})),

    # plural (known word)
    ("zambahz", ("zambah", {"form": ["s"]})),

    # known word not noun or pronoun so not plural
    ("bargz", ("barg",{})),

    # plural (unknown word — critical for Story 5)
    ("flarghz", ("flargh", {"form": ["s"]})),

    # gerund
    ("barg!ng", ("barg", {"form": ["ing"]})),

    # combined (future-proofing)
    # ("flargh!ng", ("flargh", {"form": ["ing"]})),

    # guardrails
    ("anz", ("anz", {})),  # NOT plural
    ("haz", ("haz", {})),  # NOT plural
    ("maz", ("maz", {})),  # NOT plural
    ("hazzz", ("hazz",{"form": ["s"]})),
    ("flargh!ng", ("flargh!ng", {})),   # unknown word, not recognized as "ing"

    # stacking !ng and -z
    ("barg!ngz", ("barg", {"form":["s", "ing"]})),
    # current behavior, no "ing" recognized for unknown words
    ("flargh!ngz", ("flargh!ng", {"form": ["s"]})),

    # --- safety boundaries ---
    ("abz", ("abz", {})),     # base too short → not plural
    ("z", ("z", {})),         # single char ignored

    # --- unknown baseline ---
    ("flargh", ("flargh", {})),

    # --- robustness ---
    ("flarghzz", ("flarghz", {"form": ["s"]})),  # no double-strip
]

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
        group_passed = 0
        group_failed = 0

        for zamgrh, expected in cases:
            result = translator(zamgrh)

            # don't bother checking invariants on known_bad, coz, well,
            # they are bad translations and might actually be bad because
            # they don't conform to the invariants
            if group != "known_bad":
                inv_errors = check_invariants(result, lookup, eng_lookup)

                if inv_errors:
                    print(f"FAIL (invariant): {zamgrh}")
                    print(f"  result: {result}")
                    print(f"  issues: {inv_errors}")
                    print(f"\n--- DEBUG TRACE ---")
                    print(f"[input] {zamgrh}")
                    translator(zamgrh, debug=True)
                    structure = zamgrh_to_structure(zamgrh, lookup, eng_lookup)
                    print(f"[structure] {structure}")
                    print(f"--- END DEBUG TRACE ---")
                    failed += 1
                    group_failed += 1
                    continue

            if result == expected:
                if verbose:
                    print(f"PASS: {zamgrh}")
                passed += 1
                group_passed += 1
            else:
                print(f"FAIL: {zamgrh}")
                print(f"  expected: {expected}")
                print(f"  got:      {result}")
                print(f"\n--- DEBUG TRACE ---")
                print(f"[input] {zamgrh}")
                translator(zamgrh, debug=True)
                structure = zamgrh_to_structure(zamgrh, lookup, eng_lookup)
                print(f"[structure] {structure}")
                print(f"--- END DEBUG TRACE ---")
                failed += 1
                group_failed += 1

        print(f"Group tests passed: {group_passed}")
        print(f"Group tests failed: {group_failed}")

    print("\n---")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    return failed == 0, passed, failed

def run_structure_tests(verbose=False):
    data = load_dictionary()
    lookup = build_lookup(data)
    eng_lookup = build_english_pos_lookup(data)

    passed = 0
    failed = 0

    for group, cases in STRUCTURE_TESTS.items():
        group_passed=0
        group_failed=0
        print(f"\n=== STRUCTURE: {group.upper()} ===")
        for zamgrh, expected in cases:
            result = zamgrh_to_structure(zamgrh, lookup, eng_lookup)

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
    return failed == 0, passed, failed

def run_pipeline_unit_tests(verbose=False):
    data = load_dictionary()
    lookup = build_lookup(data)
    eng_lookup = build_english_pos_lookup(data)
    passed = 0
    failed = 0

    for step_name, cases in PIPELINE_UNIT_TESTS.items():
        func = globals()[step_name]
        print(f"\n=== PIPELINE: {step_name} ===")
        step_passed = 0
        step_failed = 0

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
                if verbose:
                    print(f"PASS: {inp}->{sentence}")
                passed += 1
                step_passed += 1
            else:
                print(f"FAIL: {inp}")
                print(f"  expected: {expected}")
                print(f"  got:      {sentence}")
                print(f"  tokens:   {words}")
                failed += 1
                step_failed += 1

        print(f"Step tests passed: {step_passed}")
        print(f"Step tests failed: {step_failed}")

    print("\n---")
    print(f"Unit tests Passed: {passed}")
    print(f"Unit tests Failed: {failed}")
    return failed == 0, passed, failed

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
    return failed == 0, passed, failed

def build_result_stub(context):
    result = []

    if context.get("prev2"):
        result.append(context["prev2"])
    if context.get("prev"):
        result.append(context["prev"])

    return result

def run_morphology_unit_tests(verbose=False):
    data = load_dictionary()
    lookup = build_lookup(data)
    passed = 0
    failed = 0

    print("\n=== MORPHOLOGY UNIT TESTS ===")

    for inp, expected in MORPHOLOGY_UNIT_TESTS:
        result = normalize_morphology(inp, lookup)

        if result == expected:
            if verbose:
                print(f"PASS: {inp} -> {result}")
            passed += 1
        else:
            print(f"FAIL: {inp}")
            print(f"  expected: {expected}")
            print(f"  got:      {result}")
            failed += 1

    print("\n---")
    print(f"Morphology Passed: {passed}")
    print(f"Morphology Failed: {failed}")

    return failed == 0, passed, failed

def check_duplicates():
    seen = {}
    duplicates = []

    for group, tests in TEST_GROUPS.items():
        for t in tests:
            if t in seen:
                duplicates.append((t, seen[t], group))
            else:
                seen[t] = group
    return duplicates


def flatten_tests(groups: dict):
    """Return set of all (input, output) pairs."""
    return {
        (inp, out)
        for tests in groups.values()
        for (inp, out) in tests
    }


import pprint

def rebuild_and_export(old_groups, new_groups):
    old_set = {
        (inp, out)
        for tests in old_groups.values()
        for (inp, out) in tests
    }

    new_set = {
        (inp, out)
        for tests in new_groups.values()
        for (inp, out) in tests
    }

    missing = old_set - new_set

    if missing:
        print(f"Adding {len(missing)} missing tests...\n")

        for inp, out in missing:
            # same heuristic as before
            if len(inp.split()) == 1:
                target = "lexical"
            elif any(x in inp for x in ["!", ".", ",", "?"]):
                target = "robustness"
            elif "flargh" in inp or "[" in out:
                target = "robustness"
            elif any(w in inp for w in ["maz", "gan", "nah", "zaa", "an", "arh"]):
                target = "interactions"
            else:
                target = "grammar"

            new_groups.setdefault(target, []).append((inp, out))

    # Optional: sort for stability
    for group in new_groups:
        new_groups[group] = sorted(set(new_groups[group]))

    print("\n=== FINAL TEST_GROUPS ===\n")
    print("TEST_GROUPS = ")
    pprint.pprint(new_groups, width=100, sort_dicts=True)

def compare_test_sets(old_groups: dict, new_groups: dict):
    old_set = flatten_tests(old_groups)
    new_set = flatten_tests(new_groups)

    missing = old_set - new_set
    added = new_set - old_set

    print("=== TEST SET COMPARISON ===")
    print(f"Original count: {len(old_set)}")
    print(f"New count:      {len(new_set)}")

    if not missing and not added:
        print("✅ PERFECT MATCH: No tests lost or added")
        return

    if missing:
        print("\n❌ MISSING TESTS:")
        for t in sorted(missing):
            print(t)

    if added:
        print("\n➕ EXTRA TESTS:")
        for t in sorted(added):
            print(t)

if __name__ == "__main__":
    verbose = False
    command_line_args = sys.argv
    if ("--verbose" in command_line_args):
        verbose=True

    success_translation, trans_passed, trans_failed = run_tests(verbose)
    success_structure, struct_passed, struct_failed = run_structure_tests(verbose)
    success_pipeline_helper_unit, phelp_passed, phelp_failed = run_pipeline_helper_unit_tests(verbose)
    success_pipeline_unit, pipeline_unit_passed, pipeline_unit_failed = run_pipeline_unit_tests(verbose)
    success_morphology_unit, morph_passed, morph_failed = run_morphology_unit_tests(verbose)

    # These lines are here to remind us that if we do a major restructure
    # of TEST_GROUPS, we can uncomment these and make sure that no tests got
    # lost.
    # ----
    # print(f"--- Comparing test sets ---")
    # compare_test_sets(TEST_GROUPS_old, TEST_GROUPS)
    # print(f"--- Merging test sets ---")
    # rebuild_and_export(TEST_GROUPS_old, TEST_GROUPS)
    # print(f"--- Comparing test sets ---")
    # compare_test_sets(TEST_GROUPS_old, TEST_GROUPS)
    # ----

    duplicates = check_duplicates()
    if len(duplicates) > 0:
        print(f"==========WARNING: duplicate tests in test suite ====")
        for dup, first_group, dup_group in duplicates:
            print(f"{dup} -> first: {first_group}, duplicate: {dup_group}")
        print(f"==========WARNING: duplicate tests in test suite ====")

    if (not success_pipeline_helper_unit):
        print(f"{phelp_failed} pipeline helper unit tests failed!")
    else:
        print(f"Ran and passed {phelp_passed} pipeline helper unit tests")

    if (not success_pipeline_unit):
        print(f"{pipeline_unit_failed} pipeline unit tests failed!")
    else:
        print(f"Ran and passed {pipeline_unit_passed} pipeline unit tests")

    if (not success_structure):
        print(f"{struct_failed} structure tests failed!")
    else:
        print(f"Ran and passed {struct_passed} structure tests")

    if (not success_translation):
        print(f"{trans_failed} translation tests failed!")
    else:
        print(f"Ran and passed {trans_passed} translation tests")

    if (not success_morphology_unit):
        print(f"{morph_failed} morphology tests failed!")
    else:
        print(f"Ran and passed {morph_passed} morphology tests")

    if (success_translation and success_structure and success_pipeline_unit
        and success_pipeline_helper_unit and success_morphology_unit):
        print(f"All test types passed.")


    sys.exit(0 if (success_translation and success_structure and success_pipeline_unit and success_pipeline_helper_unit and success_morphology_unit) else 1)
