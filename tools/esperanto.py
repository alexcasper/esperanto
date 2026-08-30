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


def peel_affixes(stem, roots, max_depth=4):
    """Strip affixes until a known root falls out, searching rather than
    peeling greedily.

    Greedy peeling picks whichever affix matches first and cannot back out of
    a wrong choice. That mangles words whose root merely begins or ends like an
    affix: reĝin- loses the "prefix" re- and becomes ĝin, so reĝino — plainly
    reĝ + in + o — is reported as unknown vocabulary. Trying every single-step
    strip breadth-first and stopping at the first known root fixes it, because
    the correct decomposition is reachable even when a wrong one is tried
    first.
    """
    if stem in roots:
        return stem
    affixes = sorted(set(PREFIX + PARTICIPLE + SUFFIX), key=len, reverse=True)
    seen = {stem}
    frontier = [stem]
    for _ in range(max_depth):
        nxt = []
        for current in frontier:
            for affix in affixes:
                for candidate in (
                        current[len(affix):] if current.startswith(affix) else None,
                        current[:-len(affix)] if current.endswith(affix) else None):
                    if not candidate or len(candidate) < 2 or candidate in seen:
                        continue
                    if candidate in roots:
                        return candidate
                    seen.add(candidate)
                    nxt.append(candidate)
        if not nxt:
            break
        frontier = nxt
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
            peeled = peel_affixes(stem, words)
            if peeled in words:
                return peeled, 'known'
    peeled = peel_affixes(low, roots)
    if peeled in roots:
        return peeled, 'known'
    # Some derivations rest on a grammatical word rather than a UV root —
    # treege is tre + eg + e — so retry against the whole-word vocabulary.
    peeled = peel_affixes(low, words)
    if peeled in words:
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

    Two mistakes to avoid, both found by reviewers reading the output:

    * Not every final -n is an accusative. It attaches to nouns, adjectives
      and adverbs, so it follows o/a/e/u/j — never i. Stripping it blindly
      turned the name Martin into 'marti' and Komintern into 'kominter'.
    * Stripping -en must leave the adverb, not a bare stem: malsupren is
      malsupre + n, so it files under malsupre, not 'malsupr'.

    Finite verbs are filed as infinitives, so envenis, envenas and envenos
    are one entry (enveni) rather than three.
    """
    low = token.lower()
    # An apostrophe replaces the elided noun ending: hord' is hordo, mens' is
    # menso. Stripping it alone leaves a bare stem that is not a word.
    if low.endswith("'"):
        return low[:-1] + 'o'
    low = low.strip("'")
    # The imperative is not a citation form either: eliru files under eliri.
    if low.endswith('u') and len(low) > 3:
        return low[:-1] + 'i'
    for tense in ('as', 'is', 'os', 'us'):
        if low.endswith(tense) and len(low) > len(tense) + 1:
            return low[:-len(tense)] + 'i'
    for ending, replacement in (('ojn', 'o'), ('ajn', 'a'), ('ojn', 'o'),
                                ('oj', 'o'), ('aj', 'a'),
                                ('on', 'o'), ('an', 'a'), ('en', 'e')):
        if low.endswith(ending) and len(low) > len(ending) + 1:
            return low[:-len(ending)] + replacement
    if low.endswith('j') and len(low) > 2 and low[-2] in 'oa':
        return low[:-1]
    # A bare final -n is only an accusative after a vowel that can carry one.
    if low.endswith('n') and len(low) > 2 and low[-2] in 'oaeu':
        return low[:-1]
    return low


def strip_ending(word):
    """Remove one grammatical ending, leaving the stem.

    vortojn -> vort, estas -> est, granda -> grand. Inflection only: any
    derivational affix stays, so reĝino -> reĝin, which is what distinguishes
    a derivation from a mere inflected form.
    """
    low = word.lower()
    for ending in ENDINGS:
        if low.endswith(ending) and len(low) > len(ending) + 1:
            return low[:-len(ending)]
    return low
