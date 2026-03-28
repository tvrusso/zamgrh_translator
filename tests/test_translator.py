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

    return run, lookup

# ---------------------------
# Fix verb agreement
# ---------------------------

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

                if is_sentence_start and is_prev_noun:
                    result.append(w)
                    continue

                is_subject_noun = "noun" in prev_pos
                is_pronoun = prev in {"I", "you", "we", "they"}
                is_third_person = is_subject_noun and not prev.endswith("s")

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

                # special handling for copula
                if w in {"is", "are"}:
                    if prev == "I":
                        w = "am"
                    elif prev.endswith("s") or prev in {"you", "we", "they"}:
                        w = "are"
                    else:
                        w = "is"
                    result.append(w)
                    continue

                if not has_aux:
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

# ---------------------------
# Fix Progressive
# ---------------------------

def fix_am_progressive(words, lookup, eng_lookup):
    result = []
    i = 0

    while i < len(words):
        w = words[i]

        if w == "I" and i + 1 < len(words):
            nxt = words[i + 1]
            if nxt == "going":
                result.append("I")
                result.append("am")
                i += 1
                continue

        result.append(w)
        i += 1

    return result

# ---------------------------
# Grouped test cases
# ---------------------------

TEST_GROUPS = {
    "core": [
        ("zambahz maz barg bra!nz", "Zombies must eat brains"),
        ("mah zambah bargz bra!nz", "I eat brains"),
        ("zambahz zmazh barragahz", "Zombies smash barricades"),
        ("habbah zambah", "Happy zombie"),
        ("g!gg azz", "Kick ass"),
        ("ragz armz nagg", "Legs arms neck"),
        ("gh!!z", "Cheese"),
        ("graan gh!rrh!h", "Green chile"),
    ],

    "pronouns": [
        ("g!b gaa bra!nz", "Give you brains"),
        ("gaa g!b mah bra!nz", "You give me brains"),
        ("gab m!z ahz", "Speak with us"),
        ("!h", "It"),
        ("aarh", "Our"),
        ("zamz!ng", "Something"),
    ],

    "gloss_picker": [
        ("mah zambah gan barg bra!nz", "I will eat brains"),
        ("nam nam nam", "Eat eat eat"),
        ("mah gang", "My group"),
        ("g!b mah bra!nz", "Give me brains"),
        ("za harman", "The human"),
    ],

    "negation": [
        ("nah g!b bra!nz", "Do not give brains"),
        ("nah ran nahaarh", "Do not go away"),
        ("nah nah g!b bra!nz", "Do not do not give brains"),
        ("nah rh!gh!ng", "Not liking"),
        ("nah !hn garh graaz", "Not in your claws"),
    ],

    "questions": [
        ("!z raam azza !nn?", "Is a room at the inn?"),
        ("zambah barg bra!nz?", "Zombie eat brains?"),
        ("Nah baarz?", "No bears?"),
        ("arrh marmazaz nammah?", "Are marmosets nummy?"),
    ],

    "imperatives": [
        ("g!b bra!nz", "Give brains"),
        ("g!b mah bra!nz", "Give me brains"),
        ("barg bra!nz", "Eat brains"),
        ("azzahm zah bazz!zh!an", "Assume the position"),
        ("b!!h habbah", "Be happy"),
    ],

    "articles_and_plural": [
        ("zambah", "Zombie"),
        ("harman", "Human"),
        ("zambahz barg bra!nz", "Zombies eat brains"),
        ("zambah barg bra!n", "Zombie eat a brain"),
        ("harmanz", "Humans"),
        ("zambahz", "Zombies"),
    ],

    "agreement": [
        ("zambah bargz bra!nz", "Zombie eats brains"),
        ("harmanz bah", "Humans are bad"),
        ("harman bah", "Human is bad"),
        ("zambah n!z", "Zombie is nice"),
        ("zambah !z n!z", "Zombie is nice"),
    ],

    "conjunctions": [
        ("g!b bra!nz an g!b zarram", "Give brains and give a serum"),
        ("g!b bra!nz arh g!b zarram", "Give brains or give a serum"),
    ],

    "unknown_words": [
        ("zambahz flargh bra!nz", "Zombies [flargh] brains"),
        ("gab flargh ahz", "Speak [flargh] us"),
        ("flargh zambah", "[flargh] zombie"),
        ("zambah flargh harman", "Zombie [flargh] human"),
    ],

    "edge_cases": [
        ("", ""),
        ("nah", "Do not"),
        ("bra!nz", "Brains"),
        ("   ", ""),
    ],

    "duplicate_grammar_triggers": [
        ("zambah !z bah", "Zombie is bad"),
        ("zambahz !z bah", "Zombies are bad"),
        ("mah zambah ganna barg bra!nz", "I am going to eat brains"),
    ],

    "preposition_and_article_collisions": [
        ("g!b bra!nz zaa harman", "Give brains to a human"),
        ("g!b bra!nz zaa zah harman", "Give brains to the human"),
        ("gaam zaa mah", "Come to me"),
        ("!hn z!z bagbarn", "In this hospital"),
        ("!nz!hz !h", "Inside it"),
        ("zah bra!n !nz!hz !h", "The brain inside it"),
        ("!hn haarh", "In here"),
        ("m!z gh!!z", "With cheese"),
    ],

    "auxiliary_collisions": [
        ("mah zambah maz hab bra!nz", "I must have brains"),
        ("mah zambah gan barg bra!nz", "I will eat brains"),
        ("mah zambah haz barg bra!nz", "I have eat brains"),
        ("maz hab b!!n", "Must have been"),
        ("maz b!h bra!nz", "Must be brains"),
        ("ganna b!!h z!g", "Going to be sick"),
        ("maz barg", "Must eat"),
    ],

    "copula_vs_lexical_is": [
        ("zambah !z !z", "Zombie is is"),
        ("!z n!ghma!!r", "Is nightmare"),
    ],

    "punctuation_and_case": [
        ("HARRAH!", "Hello"),
        ("G!B BRA!NZ!", "Give brains"),
        ("nah G!B BRA!NZ!", "Do not give brains"),
        ("HARRA!H.", "Hooray"),
        ("!Z N!GHMA!!R!", "Is nightmare"),
    ],

    "repeated_words": [
        ("nam nam nam", "Eat eat eat"),
        ("bra!nz bra!nz bra!nz", "Brains brains brains"),
        ("nah nah nah g!b bra!nz", "Do not do not do not give brains"),
    ],

    "infinitives_and_time": [
        ("n!z zah z!!h gah", "Nice to see you"),
        ("n!z zah barg", "Nice to eat"),
        ("n!z zah b!!h zambah", "Nice to be zombie"),
        ("aga!n", "Again"),
        ("zan mah gang", "Then my group"),
        ("n!gh", "Night"),
        ("n!z z!z n!gh", "Nice this night"),
        ("hrarrz", "First"),
        ("naa h!aar", "New year"),
        ("habbah naa h!aar", "Happy new year"),
    ],

    "abstracts_and_descriptors": [
        ("zagh brh!ghnazz", "Such brightness"),
        ("aggz!hzaz", "Excited"),
        ("!nnarazz!ng am!narz", "Interesting animals"),
        ("azbazharrh!h", "Especially"),
        ("an!maarh", "Anymore"),
        ("z!rr!h", "Silly"),
        ("harrabarh", "Horrible"),
        ("barrah hangrah", "Very hungry"),
        ("rabbrh!h zanza!h", "Lovely Sunday"),
    ],

    "body_and_spatial": [
        ("marrz", "Melt"),
        ("maaz", "Mouth"),
        ("graaz", "Claws"),
        ("!hn gaarh maaz", "In your mouth"),
        ("zah bra!n !nz!hz !h", "The brain inside it"),
        ("zaa", "Too"),
        ("bra!nbag", "Hat"),
    ],

    "food_and_consumption": [
        ("barbagah zarz", "Barbecue sauce"),
        ("banz!barh hrh!!z", "Bountiful feast"),
        ("abah zah ganzaam", "About to consume"),
        ("rh!bz", "Ribs"),
        ("g!argh!h", "Jerky"),
        ("brh!!z", "Please"),
    ],

    "sensory_and_emotion": [
        ("zmarrz", "Smell"),
        ("zz!ng!h", "Stinky"),
        ("agh", "Ick"),
        ("ranz!z", "Rancid"),
        ("z!g", "Sick"),
        ("n!ghma!!r", "Nightmare"),
        ("zangz", "Thanks"),
        ("zang", "Thank you"),
    ],

    "location_emergency_and_reassurance": [
        ("za!rh", "There"),
        ("hr!rh!", "Fire"),
        ("hrh!ghz", "Fight"),
        ("za!g gaah ga!rh", "Take good care"),
        ("ahb", "Of"),
        ("zga!rz", "Worry"),
        ("zrazz ahz", "Trust us"),
        ("r!!rh!h", "Really"),
        ("ahmahgah", "Oh my god"),
    ],

    "shopping_and_commands": [
        ("zhabbarz", "Shoppers"),
        ("zhabb!ng", "Shopping"),
        ("barga!nz", "Bargains"),
        ("zhabb!ng hrarh barga!nz", "Shopping for bargains"),
        ("azzahm", "Assume"),
        ("bazz!zh!an", "Position"),
        ("azzahm zah bazz!zh!an", "Assume the position"),
        ("bragg hrh!hza!h", "Black Friday"),
    ],

    "animals_and_places": [
        ("manah am!narz", "Many animals"),
        ("r!anz", "Lions"),
        ("marmazaz", "Marmosets"),
        ("z!garz", "Tigers"),
        ("baarz", "Bears"),
        ("arran", "Alone"),
        ("bagbarn", "Hospital"),
        ("agzbarn", "Firestation"),
        ("abbarnaan", "Afternoon"),
        ("zanza!h", "Sunday"),
    ],

    "possessives_and_social_phrases": [
        ("gaarh", "Your"),
        ("aarh", "Our"),
        ("ba!h aarh razbagz", "Pay our respects"),
        ("m!!nz", "Mean"),
        ("gamman!an gabraz", "Communion goblets"),
        ("zanzhah", "Dante"),
    ],
}

# ---------------------------
# Test runner
# ---------------------------

def run_tests():
    translator, lookup = build_translator()

    passed = 0
    failed = 0

    for group, cases in TEST_GROUPS.items():
        print(f"\n=== {group.upper()} ===")

        for zamgrh, expected in cases:
            result = translator(zamgrh)

            if result == expected:
                print(f"PASS: {zamgrh}")
                passed += 1
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

    print("\n---")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")

    return failed == 0


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)