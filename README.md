# Zamgrh-Angr!zh Zranzra!zar (Zamgrh-English Translator)

A structured translator and linguistic toolkit for the zombie language "Zamgrh".

## What is Zamgrh?  (Rhaz !z Zamgrh?)

Zamgrh is the language spoken by zombies in the low-tech browser game
Urban Dead (now defunct) and its successor, World Wide Dead
(https://wwdead.com)

### Huh?  (Hah?)

See, in the game, zombie players start off being basically unable to
speak at all.   With sufficient levels of experience, they can buy the
"Death Rattle" skill, which allows them to speak, but only sorta.
Anything you type gets garbled into generally incomprehensible
patterns of characters bearing no resemblance to what you typed.
However, the letters "z", "a", "m", "g", "r", "h", "n", and "b", plus
some punctuation marks are passed through unmodified.

As a result, some zombie players created a "language" we call "zamgrh"
that involves only those characters.   A surprising range of
communication becomes possible.   Rarr!h!  Zah zambahz gan gab, ahn
zah harmanz gan annarzanz!

The basic concept of Zamgrh is described
[on this page of the archived Urban Dead wiki](https://wiki.urbandead.com/index.php/Zamgrh).

## Why make a translator?  (Hra! ma!g an zranzra!zar?)

The Urban Dead zombie horde ["Babble Rabble"](https://wiki.urbandead.com/index.php/Babble_Rabble) was created to advance the
art of zamgrh communication and spread joy to the residents of the city of
Malton with their babbling.  Right before we eat their brains.

Members of Babble Rabble decided that having a translator would be
helpful to new members and to those who don't really speak the
language fluently.  Also, it is helpful when the food can understand
us.  BARHAH!  Zambahz maz gab ahn barg bra!nz!

## Where does it stand?  (Hra!r !z !h?)

Right now the translator is in early development and only translates
from Zamgrh to English but with
only a very limited dictionary of Zamgrh words.  Development is
progressing fast, but is currently focused on improving the grammar
engine, refining the dictionary schema, and developing tools to audit
and validate the dictionary.  We're also working on refining the
translator's morphology rules so that we don't have to have a
dictionary entry for every single inflection of words.

Most canonical Zamgrh words are not recognized yet, so some
of the most fun in-game speech still can't be decoded.  But it's
pretty good with the words it does know, and can recognize some
advanced sentence structures in Zamgrh and translate them to nearly
correct English.  Mah zambah gan gab an zah harmanz gan ran nahaarh,
arh mah zambah barg bra!nz!

We are also able to generate a human readable "Zombie Dictionary"
directly from our JSON dictionary with a script in the tools
directory.  You can find that rendition of our ccurrent dictionary in
the wiki.

Harmanz maz gab zamgrh!

## Planned Features  (Brannz hr!!zarz)

- Zamgrh → English translation
- English → Zamgrh generation
- Curated JSON dictionary
- Validator and auditor for dictionary integrity
- Phonetic approximation support

## Project Structure (Brazhag Zzragzahr)

- `data/` — dictionary files
- `src/` — core logic
- `tools/` — helper scripts
- `tests/` — test cases

## Getting Started  (Zarz zhambar!ng)

```bash
python src/translator.py
