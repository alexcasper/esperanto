#!/usr/bin/env python3
"""Score how much of a text is recognisable Esperanto, to gate corpus candidates.

Usage: python3 tools/score_esperanto_text.py FILE [FILE ...]

Written to answer a specific question: the pre-1929 Esperanto books on
archive.org are Google page scans, and OCR errors ("soidaton" for "soldaton",
"PARAONO" for "FARAONO") would enter DICT/ as fake lemmas. Eyeballing does not
scale to hundreds of candidates, so this measures a candidate against
vocabulary we already trust — the 2911 Universala Vortaro entries in
DICT/entries.jsonl — plus regular Esperanto morphology.

A token counts as recognised if, after stripping the regular endings
(o/a/e/j/n and the verb endings), its stem is a known UV root, a known
grammatical word, or a compound of known roots. Proper nouns are unavoidable
false negatives, so a clean text does not score 100%; calibrate against the
reference texts already in CORPUS/ rather than against an absolute target.
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENTRIES = os.path.join(ROOT, 'DICT', 'entries.jsonl')

TOKEN = re.compile(r"[a-zĉĝĥĵŝŭ]+", re.IGNORECASE)
# Longest first, so 'ojn' is stripped before 'o'.
ENDINGS = ['ajn', 'ojn', 'aj', 'oj', 'an', 'on', 'en', 'as', 'is', 'os', 'us',
           'ad', 'a', 'o', 'e', 'i', 'u', 'n', 'j']
VERB_SUFFIX = ['ant', 'int', 'ont', 'at', 'it', 'ot']
AFFIX = ['mal', 'ne', 'ge', 'bo', 'ek', 'el', 're', 'dis', 'for', 'pra',
         'eg', 'et', 'ar', 'er', 'ej', 'ec', 'aĵ', 'ist', 'an', 'ul', 'in',
         'id', 'ig', 'iĝ', 'em', 'ind', 'ebl', 'estr', 'uj', 'op', 'obl']


def load_vocabulary():
    roots, words = set(), set()
    with open(ENTRIES, encoding='utf-8') as fh:
        for line in fh:
            entry = json.loads(line)
            word = entry['word'].lower()
            words.add(word)
            if entry.get('root'):
                roots.add(entry['root'].lower())
            stem = (entry.get('morphology') or {}).get('stem')
            if stem:
                roots.add(stem.lower())
    return roots, words


def strip_affixes(stem, roots):
    """Peel regular affixes off a stem, longest match first."""
    changed = True
    while changed and len(stem) > 2:
        changed = False
        for affix in sorted(AFFIX + VERB_SUFFIX, key=len, reverse=True):
            if stem in roots:
                return stem
            if stem.startswith(affix) and len(stem) > len(affix) + 1:
                stem, changed = stem[len(affix):], True
                break
            if stem.endswith(affix) and len(stem) > len(affix) + 1:
                stem, changed = stem[:-len(affix)], True
                break
    return stem


def recognised(token, roots, words):
    token = token.lower()
    if token in words or token in roots:
        return True
    for ending in ENDINGS:
        if token.endswith(ending) and len(token) > len(ending) + 1:
            stem = token[:-len(ending)]
            if stem in roots or stem in words:
                return True
            if strip_affixes(stem, roots) in roots:
                return True
    if strip_affixes(token, roots) in roots:
        return True
    # Compounds: split into two known roots (fervojo, samideano).
    for cut in range(3, len(token) - 2):
        head, tail = token[:cut], token[cut:]
        if head in roots and (tail in roots or tail in words
                              or strip_affixes(tail, roots) in roots):
            return True
    return False


def score(path, roots, words):
    with open(path, encoding='utf-8', errors='replace') as fh:
        text = fh.read()
    tokens = [t for t in TOKEN.findall(text) if len(t) > 1]
    if not tokens:
        return None
    hits = sum(1 for t in tokens if recognised(t, roots, words))
    # Cheap OCR tells that the vocabulary check alone can miss.
    lines = text.splitlines()
    double_spaced = sum(1 for line in lines if '  ' in line.strip())
    return {
        'file': os.path.basename(path),
        'tokens': len(tokens),
        'recognised': 100.0 * hits / len(tokens),
        'singletons': 100.0 * sum(1 for t in TOKEN.findall(text)
                                  if len(t) == 1) / max(len(tokens), 1),
        'double_spaced_lines': 100.0 * double_spaced / max(len(lines), 1),
    }


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__.strip().splitlines()[2])
    roots, words = load_vocabulary()
    print('%-40s %8s %10s %10s %12s'
          % ('file', 'tokens', 'known%', 'singles%', 'dbl-spaced%'))
    for path in sys.argv[1:]:
        result = score(path, roots, words)
        if result is None:
            print('%-40s (no tokens)' % os.path.basename(path))
            continue
        print('%(file)-40s %(tokens)8d %(recognised)9.1f%% %(singletons)9.1f%% '
              '%(double_spaced_lines)11.1f%%' % result)
    return 0


if __name__ == '__main__':
    sys.exit(main())
