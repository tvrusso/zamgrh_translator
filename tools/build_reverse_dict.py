import json

INPUT = "../data/zamgrh_dictionary.json"
OUTPUT = "../data/reverse_dictionary.json"

with open(INPUT, "r", encoding="utf-8") as f:
    data = json.load(f)

reverse = {}

for entry in data:
    for gloss in entry["english"]:
        g = gloss["gloss"]
        reverse.setdefault(g, []).append(entry["word"])

with open(OUTPUT, "w", encoding="utf-8") as f:
    json.dump(reverse, f, indent=2)

print("✅ Reverse dictionary built")
