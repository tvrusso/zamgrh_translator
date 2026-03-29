#!/usr/bin/env python3

import json
import sys
from pathlib import Path


def load_dictionary(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def format_entry(entry):
    word = entry.get("word", "[unknown]")
    pos = ", ".join(entry.get("pos", []))

    # English glosses
    english_list = entry.get("english", [])

    # sort by weight descending (default 0 if missing)
    english_list = sorted(
        english_list,
        key=lambda e: e.get("weight", 0),
        reverse=True
    )

    glosses = [e.get("gloss", "") for e in english_list if e.get("gloss")]

    gloss_str = ", ".join(glosses) if glosses else "[no gloss]"

    lines = []

    # Header
    lines.append(f"### {word}")
    lines.append("")
    lines.append(f"**Part of speech:** {pos if pos else 'unknown'}")
    lines.append("")
    lines.append(f"**Meaning:** {gloss_str}")

    # Optional fields
    if "source" in entry:
        lines.append(f"**Source:** {entry['source']}")

    if "confidence" in entry:
        lines.append(f"**Confidence:** {entry['confidence']:.2f}")

    if "synonyms" in entry and entry["synonyms"]:
        lines.append(f"**Synonyms:** {', '.join(entry['synonyms'])}")

    if entry.get("preferred") is True:
        lines.append(f"**Preferred:** yes")

    if "usage" in entry and "tone" in entry["usage"]:
        tones = ", ".join(entry["usage"]["tone"])
        lines.append(f"**Tone:** {tones}")

    if "phonetic" in entry:
        approx = entry["phonetic"].get("approx")
        syllables = entry["phonetic"].get("syllables")
        if approx:
            lines.append(f"**Pronunciation:** {approx}")
        if syllables:
            lines.append(f"**Syllables:** {'-'.join(syllables)}")

    if "examples" in entry and entry["examples"]:
        lines.append("")
        lines.append("**Examples:**")
        for ex in entry["examples"]:
            z = ex.get("zamgrh", "")
            en = ex.get("english", "")
            lines.append(f"- *{z}* — {en}")

    if "notes" in entry:
        lines.append("")
        lines.append(f"**Notes:** {entry['notes']}")

    lines.append("")  # spacing between entries

    return "\n".join(lines)


def generate_markdown(data):
    # Sort alphabetically by word
    data_sorted = sorted(data, key=lambda x: x.get("word", ""))

    lines = []
    lines.append("# Zamgrh–English Dictionary")
    lines.append("")
    lines.append("_Generated from dictionary JSON_")
    lines.append("")
    lines.append("---")
    lines.append("")

    for entry in data_sorted:
        lines.append(format_entry(entry))
        lines.append("---")
        lines.append("")

    return "\n".join(lines)


def main():
    if len(sys.argv) != 3:
        print("Usage: generate_dictionary_md.py input.json output.md")
        sys.exit(1)

    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])

    data = load_dictionary(input_path)
    md = generate_markdown(data)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(md)

    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
