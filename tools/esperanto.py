#!/usr/bin/env python3
"""Shared Esperanto morphology and vocabulary, used by the corpus tools.

The dictionary we already trust is DICT/entries.jsonl — 2911 entries from the
Universala Vortaro of the Fundamento (1905). Everything here answers one
question against it: is this token a word Esperanto morphology can build from a
root we know?

Esperanto is regular enough that this is tractable without a parser. A word is
[prefix*] root [suffix*] ending, endings mark part of speech, and compounds
join roots directly. So we peel and look up.
"""
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENTRIES = os.path.join(ROOT, 'DICT', 'entries.jsonl')

TOKEN = re.compile(r"[a-zA-ZĉĝĥĵŝŭĈĜĤĴŜŬ']+")

# Longest first so 'ojn' is stripped before 'oj' and 'o'.
ENDINGS = ['ajn', 'ojn', 'aj', 'oj', 'an', 'on', 'en', 'as', 'is', 'os', 'us',
           'a', 'o', 'e', 'i', 'u', 'n', 'j']
PARTICIPLE = ['ant', 'int', 'ont', 'at', 'it', 'ot']
PREFIX = ['mal', 'ne', 'ge', 'bo', 'ek', 'el', 're', 'dis', 'for', 'pra',
          'eks', 'mis', 'fi', 'retro']
SUFFIX = ['estr', 'ebl', 'ind', 'em', 'ec', 'aĵ', 'ist', 'an', 'ul', 'in',
          'id', 'ig', 'iĝ', 'uj', 'op', 'obl', 'on', 'eg', 'et', 'ar', 'er',
          'ej', 'ad', 'aĉ', 'ĉj', 'nj', 'um', 'end', 'ism']

# Closed classes that carry no root: they are words in their own right.
GRAMMATICAL = {
    'la', 'kaj', 'aŭ', 'ke', 'ĉu', 'se', 'ĉar', 'ol', 'nek', 'do', 'sed',
    'ne', 'jes', 'ja', 'ankaŭ', 'eĉ', 'nur', 'jam', 'ankoraŭ', 'plu', 'tre',
    'tro', 'pli', 'plej', 'tuj', 'nun', 'hodiaŭ', 'hieraŭ', 'morgaŭ', 'baldaŭ',
    'mi', 'vi', 'li', 'ŝi', 'ĝi', 'ni', 'ili', 'si', 'oni', 'ci',
    'al', 'apud', 'ĉe', 'ĉirkaŭ', 'da', 'de', 'dum', 'el', 'en', 'ekster',
    'ĝis', 'inter', 'je', 'kontraŭ', 'krom', 'kun', 'per', 'po', 'por',
    'post', 'preter', 'pri', 'pro', 'sen', 'sub', 'super', 'sur', 'tra',
    'trans', 'anstataŭ', 'antaŭ', 'malgraŭ', 'kvazaŭ', 'laŭ', 'pere',
    'unu', 'du', 'tri', 'kvar', 'kvin', 'ses', 'sep', 'ok', 'naŭ', 'dek',
    'cent', 'mil', 'nulo',
}

CORRELATIVE = re.compile(
    r'^(ki|ti|i|ĉi|neni)(u|o|a|e|am|al|el|om|es)(j?n?)$')


def load_vocabulary(path=ENTRIES):
    """Roots and whole words from the dictionary, lowercased."""
    roots, words = set(), set()
    with open(path, encoding='utf-8') as fh:
        for line in fh:
            if not line.strip():
                continue
            entry = json.loads(line)
            words.add(entry['word'].lower())
            if entry.get('root'):
                roots.add(entry['root'].lower())
            stem = (entry.get('morphology') or {}).get('stem')
            if stem:
                roots.add(stem.lower())
    return roots, words


def peel_affixes(stem, roots):
    """Strip prefixes and suffixes until a known root falls out."""
    peeling = True
    while peeling and len(stem) > 2:
        if stem in roots:
            return stem
        peeling = False
        for affix in sorted(PREFIX + PARTICIPLE + SUFFIX, key=len, reverse=True):
            if stem.startswith(affix) and len(stem) > len(affix) + 1:
                stem, peeling = stem[len(affix):], True
                break
            if stem.endswith(affix) and len(stem) > len(affix) + 1:
                stem, peeling = stem[:-len(affix)], True
                break
    return stem


def analyse(token, roots, words):
    """Return (lemma, kind) for a token.

    kind is one of: grammatical, correlative, known (built on a known root),
    or unknown. The lemma is the citation form we would file it under — the
    root for a known word, the token itself otherwise.
    """
    low = token.lower().strip("'")
    if not low:
        return None, 'unknown'
    if low in GRAMMATICAL:
        return low, 'grammatical'
    if CORRELATIVE.match(low):
        return low, 'correlative'
    if low in words or low in roots:
        return low, 'known'
    for ending in ENDINGS:
        if low.endswith(ending) and len(low) > len(ending) + 1:
            stem = low[:-len(ending)]
            if stem in roots or stem in words:
                return stem, 'known'
            peeled = peel_affixes(stem, roots)
            if peeled in roots:
                return peeled, 'known'
    peeled = peel_affixes(low, roots)
    if peeled in roots:
        return peeled, 'known'
    for cut in range(3, len(low) - 2):
        head, tail = low[:cut], low[cut:]
        if head in roots and (tail in roots or tail in words
                              or peel_affixes(tail, roots) in roots):
            return low, 'known'
    return low, 'unknown'


def guess_pos(token):
    """Part of speech from the ending, which in Esperanto is unambiguous."""
    low = token.lower()
    for ending, pos in (('oj', 'noun'), ('ojn', 'noun'), ('on', 'noun'),
                        ('aj', 'adj'), ('ajn', 'adj'), ('an', 'adj'),
                        ('as', 'verb'), ('is', 'verb'), ('os', 'verb'),
                        ('us', 'verb'), ('anta', 'participle'),
                        ('inta', 'participle'), ('onta', 'participle')):
        if low.endswith(ending):
            return pos
    if low.endswith('o'):
        return 'noun'
    if low.endswith('a'):
        return 'adj'
    if low.endswith('e'):
        return 'adv'
    if low.endswith('i'):
        return 'verb'
    return 'unknown'


ESPERANTO_LETTERS = set('abcĉdefgĝhĥijĵklmnoprsŝtuŭvzABCĈDEFGĜHĤIJĴKLMNOPRSŜTUŬVZ')


def citation_form(token):
    """Reduce an unrecognised token to the form we would file it under.

    analyse() only returns a root for words built on roots we know, so unknown
    vocabulary would otherwise split across its inflections — kongreso,
    kongresoj and kongreson filed as three separate discoveries. Esperanto
    endings are regular, so strip one and re-attach the nominal ending.
    """
    low = token.lower().strip("'")
    for ending in ('ojn', 'ajn', 'oj', 'aj', 'on', 'an', 'en', 'j', 'n'):
        if low.endswith(ending) and len(low) > len(ending) + 2:
            stem = low[:-len(ending)]
            if ending in ('ojn', 'oj', 'on'):
                return stem + 'o'
            if ending in ('ajn', 'aj', 'an'):
                return stem + 'a'
            if ending in ('j', 'n'):
                return stem
            return stem
    return low
