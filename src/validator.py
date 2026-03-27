import json

ALLOWED_POS = {"noun", "verb", "adj", "adv", "interj", "aux", "pron", "conj"}

def validate_entry(entry):
    required_fields = ["word", "pos", "english"]

    for field in required_fields:
        if field not in entry:
            raise ValueError(f"Missing field: {field}")

    if not isinstance(entry["word"], str):
        raise TypeError("word must be string")

    if not isinstance(entry["pos"], list):
        raise TypeError("pos must be list")

    for pos in entry["pos"]:
        if pos not in ALLOWED_POS:
            raise ValueError(f"Invalid POS: {pos}")

    if not isinstance(entry["english"], list):
        raise TypeError("english must be list")

    for gloss in entry["english"]:
        if "gloss" not in gloss:
            raise ValueError("Missing gloss")
        if "weight" not in gloss:
            raise ValueError("Missing weight")

def validate_dictionary(data):
    if not isinstance(data, list):
        raise TypeError("Dictionary must be a list")

    for entry in data:
        validate_entry(entry)

    print("✅ Dictionary is valid")


def load_and_validate(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    validate_dictionary(data)
    return data


if __name__ == "__main__":
    load_and_validate("../data/zamgrh_dictionary.json")

