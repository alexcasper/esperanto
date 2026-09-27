#!/usr/bin/env python3
"""Enrich DICT/ from O'Connor & Hayes, English-Esperanto Dictionary (c.1906).

Usage: python3 tools/parse_oconnor.py [--dry-run] [--min-plausible]

Outputs:
  DICT/entries.jsonl        new entries, tagged source: oconnor-1906
  DICT/english-index.jsonl  English -> Esperanto, the lookup direction the
                            dictionary could not serve at all
  DICT/affix-examples.jsonl morpheme-segmented affix demonstrations

Why this source is treated differently from the corpus. The mined entries rest
on attested usage: a count, a number of independent sources, real citations.
O'Connor is an editorially compiled word list, so its entries have authority
of a different kind and no attestation at all. They are tagged distinctly and
carry no `attestation` field, so a consumer can tell at a glance which claim
rests on what. Nothing here overwrites a corpus-mined or Fundamento entry.

The file holds two datasets with opposite directions, and reading it as one
would corrupt both:

  main section    'English = esperanto.'  — 12914 lines, the dictionary
  affix preface   'esperanto = English'   — 60 lines demonstrating affixes,
                  with apostrophes marking morpheme boundaries (bo'patro =
                  father-in-law). These are segmentation evidence, not
                  headwords, so they go to their own file; 56 parse, and the
                  remaining 4 are phrasal (via reĝa moŝto = your Majesty).

Esperanto sides are checked for plausibility before being written: the word
must be spellable in the Esperanto alphabet and end in a real ending or be a
known grammatical word. A 1906 scan yields enough debris to make that worth
enforcing rather than assuming.
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import esperanto  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE = os.path.join(ROOT, 'CORPUS', 'pg-16967.txt')
ENTRIES = os.path.join(ROOT, 'DICT', 'entries.jsonl')
INDEX = os.path.join(ROOT, 'DICT', 'english-index.jsonl')
AFFIXES = os.path.join(ROOT, 'DICT', 'affix-examples.jsonl')
SOURCE_TAG = 'oconnor-1906'

# 'Headword (sense) = esperanto, esperanto.'
MAIN = re.compile(r"^([A-Z][A-Za-z' -]{1,40}?)\s*(\([^)]{1,40}\))?\s*=\s*"
                  r"([a-zĉĝĥĵŝŭ,\s'-]{2,60})\.\s*$")
# 'radiko = gloss, derivaĵo = gloss.' from the affix preface.
AFFIX = re.compile(r"^([a-zĉĝĥĵŝŭ']{2,20})\s*=\s*([^,;]{2,40})[,;]\s*"
                   r"([a-zĉĝĥĵŝŭ']{2,25})\s*=\s*([^.;]{2,50})")

ALPHA = 'abcĉdefgĝhĥijĵklmnoprsŝtuŭvz'
ENDINGS = ('o', 'a', 'e', 'i', 'oj', 'aj', 'as', 'is', 'os', 'us', 'u',
           'aŭ', 'eŭ')
ENDING_POS = {'o': 'noun', 'a': 'adj', 'e': 'adv', 'i': 'verb'}


def plausible(word):
    """Spellable in Esperanto and ending like an Esperanto word.

    Single words only — this gates dictionary headwords. Phrasal translations
    ('Abaft = posta parto') are perfectly good Esperanto and go to the English
    index, but they are not headwords, so they are separated rather than
    thrown away.
    """
    if len(word) < 2 or any(c not in ALPHA for c in word):
        return False
    if word in esperanto.GRAMMATICAL or esperanto.CORRELATIVE.match(word):
        return True
    return word.endswith(ENDINGS)


def is_phrase(text):
    """A multi-word Esperanto translation: index-worthy, not a headword."""
    parts = text.split()
    return len(parts) > 1 and all(
        p and all(c in ALPHA for c in p) for p in parts)


def parse(path):
    pairs, affixes, phrases, skipped = [], [], [], 0
    for line in open(path, encoding='utf-8'):
        text = line.strip()
        if not text:
            continue
        match = MAIN.match(text)
        if match:
            english, sense, esperanto_side = match.groups()
            for word in (w.strip() for w in esperanto_side.split(',')):
                word = word.replace("'", '')
                if not word:
                    continue
                sense_text = (sense or '').strip('() ')
                if plausible(word):
                    pairs.append((english.strip(), sense_text, word))
                elif is_phrase(word):
                    phrases.append((english.strip(), sense_text, word))
                else:
                    skipped += 1
            continue
        match = AFFIX.match(text)
        if match:
            base, base_gloss, derived, derived_gloss = match.groups()
            affixes.append({
                'base': base.replace("'", ''), 'base_gloss': base_gloss.strip(),
                'derived': derived.replace("'", ''),
                'derived_gloss': derived_gloss.strip(),
                'segmentation': derived,
            })
    return pairs, affixes, phrases, skipped


# Period-dated English terms in O'Connor's 1906 glosses, mapped to neutral
# present-day wording (esp-54v, option b). The source's own wording is kept
# verbatim in a `dated_gloss` field on the affected entries, and the English
# headwords / english-index keep the source's terms — they are the lookup
# direction into the 1906 source and their provenance is already tagged by
# `source: oconnor-1906`. Replacement is gloss-only, whole-term.
DATED_GLOSSES = {
    'negro': 'Black person',
    'heathenism': 'paganism, idol worship',
    'heathen': 'pagan',
    'lunatic': 'person with mental illness',
    'imbecile': 'person with intellectual disability',
    'crippled': 'disabled',
    'idiot': 'person with intellectual disability',
    'oaf': 'fool, simpleton',
    'dumbness': 'inability to speak',
    'dumb show': 'pantomime (performance without speech)',
    'dumb': 'unable to speak',
    'savage': 'wild, untamed',
    'oriental': 'eastern, of the East',
}


def modernise_gloss(gloss, pos):
    """Replace dated terms whole-term (case-insensitive), preserving the rest.

    Returns (new_gloss, changed). Word-boundary regex, longest term first so
    'dumb show' wins over 'dumb'. 'cripple' is POS-dependent: the verb sense
    is 'disable', the noun a person. Senses are deduplicated after
    replacement ('savage; untamed' and 'wild, untamed' collapse)."""
    def repl_for(term):
        if term == 'cripple':
            return 'disable' if pos == 'verb' else 'person with physical disability'
        return DATED_GLOSSES[term]
    changed = False
    for term in sorted(DATED_GLOSSES, key=len, reverse=True) + ['cripple']:
        pattern = re.compile(r'\b%s\b' % re.escape(term), re.IGNORECASE)
        if pattern.search(gloss):
            gloss = pattern.sub(repl_for(term), gloss)
            changed = True
    if changed:
        seen, parts = set(), []
        for part in gloss.split('; '):
            if part not in seen:
                seen.add(part)
                parts.append(part)
        # A replacement can subsume other senses ('savage' -> 'wild, untamed'
        # next to headwords Untamed and Wild): drop parts whose words are all
        # contained in a longer part.
        def subsumed(p):
            words = set(re.findall(r'\w+', p))
            return any(p != q and words <= set(re.findall(r'\w+', q))
                       for q in parts)
        parts = [p for p in parts if not subsumed(p)]
        gloss = '; '.join(parts)
    return gloss, changed


def build_entry(word, senses, roots, words):
    """One dictionary entry from every English headword pointing at a word."""
    glosses = []
    for english, sense in senses:
        gloss = english.lower()
        if sense:
            gloss += ' (%s)' % sense
        if gloss not in glosses:
            glosses.append(gloss)
    entry = {
        'word': word,
        'pos': ENDING_POS.get(word[-1:], 'unknown'),
        'gloss_en': '; '.join(glosses[:6]),
    }
    modern, changed = modernise_gloss(entry['gloss_en'], entry['pos'])
    if changed:
        entry['dated_gloss'] = entry['gloss_en']  # O'Connor's own wording
        entry['gloss_en'] = modern
    if entry['pos'] in ENDING_POS.values() and word[-1:] in ENDING_POS:
        entry['root'] = word[:-1]
        entry['morphology'] = {'stem': word[:-1], 'ending': word[-1:]}
    entry['source'] = SOURCE_TAG
    entry['english_headwords'] = [e for e, _ in senses][:8]
    bare = word[:-1] if word[-1:] in ENDING_POS else word
    if bare not in roots and esperanto.peel_affixes(bare, roots) in roots:
        entry['derived'] = True
    return entry


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    pairs, affixes, phrases, skipped = parse(SOURCE)

    with open(ENTRIES, encoding='utf-8') as fh:
        existing = [json.loads(line) for line in fh if line.strip()]
    existing = [e for e in existing if e.get('source') != SOURCE_TAG]
    held = {e['word'].lower() for e in existing}
    roots, words = set(), set()
    for entry in existing:
        words.add(entry['word'].lower())
        if entry.get('root'):
            roots.add(entry['root'].lower())
        stem = (entry.get('morphology') or {}).get('stem')
        if stem:
            roots.add(stem.lower())

    by_word = {}
    for english, sense, word in pairs:
        by_word.setdefault(word, []).append((english, sense))

    promoted = [build_entry(word, senses, roots, words)
                for word, senses in sorted(by_word.items())
                if word not in held]
    promoted = [e for e in promoted if e['pos'] != 'unknown']

    merged = sorted(existing + promoted,
                    key=lambda e: [ALPHA.index(c) if c in ALPHA else 99
                                   for c in e['word'].lower()])

    by_english = {}
    for english, sense, word in pairs + phrases:
        key = english.lower() + (' (%s)' % sense if sense else '')
        by_english.setdefault(key, []).append(word)

    if not args.dry_run:
        for path, rows in ((ENTRIES, merged),):
            tmp = path + '.tmp'
            with open(tmp, 'w', encoding='utf-8') as fh:
                for row in rows:
                    fh.write(json.dumps(row, ensure_ascii=False) + '\n')
            os.replace(tmp, path)
        with open(INDEX, 'w', encoding='utf-8') as fh:
            for english in sorted(by_english):
                fh.write(json.dumps(
                    {'english': english, 'esperanto': by_english[english],
                     'source': SOURCE_TAG}, ensure_ascii=False) + '\n')
        with open(AFFIXES, 'w', encoding='utf-8') as fh:
            for row in affixes:
                row['source'] = SOURCE_TAG
                fh.write(json.dumps(row, ensure_ascii=False) + '\n')

    print('%sparsed %d English-Esperanto pairs (%d Esperanto sides rejected '
          'as implausible)' % ('[dry run] ' if args.dry_run else '',
                               len(pairs), skipped))
    print('  %d distinct Esperanto words, %d already held' %
          (len(by_word), sum(1 for w in by_word if w in held)))
    print('  dictionary: %d → %d entries (%d new from O\'Connor, %d derived)'
          % (len(existing), len(merged), len(promoted),
             sum(1 for e in promoted if e.get('derived'))))
    print('  english index: %d headwords → %s (%d phrasal translations)'
          % (len(by_english), INDEX, len(phrases)))
    print('  affix examples: %d → %s' % (len(affixes), AFFIXES))
    return 0


if __name__ == '__main__':
    sys.exit(main())
