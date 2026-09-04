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
# Every preposition also serves as a verbal prefix — enveni, alporti,
# surkudri, trapasi, ĉirkaŭblovi — and leaving them out was the largest single
# source of false 'unknown' verdicts: englutinta failed while glutinta
# resolved, though engluti is a dictionary entry. Three reviewers reported it.
PREFIX = ['mal', 'ne', 'ge', 'bo', 'ek', 'el', 're', 'dis', 'for', 'pra',
          'eks', 'mis', 'fi', 'retro',
          'al', 'antaŭ', 'apud', 'ĉe', 'ĉirkaŭ', 'de', 'en', 'inter',
          'kontraŭ', 'krom', 'kun', 'per', 'post', 'preter', 'pri', 'pro',
          'sen', 'sub', 'super', 'sur', 'tra', 'trans']
# -il- (an instrument: tranĉilo, ventomontrilo) is one of the most productive
# suffixes in the language and was missing outright, as was -ing-.
SUFFIX = ['estr', 'ebl', 'ind', 'em', 'ec', 'aĵ', 'ist', 'an', 'ul', 'in',
          'id', 'ig', 'iĝ', 'uj', 'op', 'obl', 'on', 'eg', 'et', 'ar', 'er',
          'ej', 'ad', 'aĉ', 'ĉj', 'nj', 'um', 'end', 'ism', 'il', 'ing']

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
    'mem',
}

CORRELATIVE = re.compile(
    r'^(ki|ti|i|ĉi|neni)(u|o|a|e|am|al|el|om|es)(j?n?)$')

# Cheap gate for participle_infinitive, which is otherwise 30 vocabulary
# lookups per token and made a mining pass twenty times slower.
PARTICIPLE_ENDING = re.compile(r'(?:ant|int|ont|at|it|ot)(?:ajn|aj|an|a|e)$')


def load_vocabulary(path=ENTRIES):
    """Roots and whole words from the dictionary, lowercased.

    An entry promoted from the corpus usually records no root, so its stem was
    in neither set and only its exact citation form was recognised: laŭtlegi
    was known and laŭtlegis was not. The same lemma then came out 'known' in
    one shard and 'unknown' in another, decided by which surface form that
    shard happened to meet — visible in the round-4 shard files and reported by
    three reviewers. So every whole word contributes its stem as a root.
    """
    roots, words = set(), set()
    with open(path, encoding='utf-8') as fh:
        for line in fh:
            if not line.strip():
                continue
            entry = json.loads(line)
            word = entry['word'].lower()
            words.add(word)
            if entry.get('root'):
                roots.add(entry['root'].lower())
            stem = (entry.get('morphology') or {}).get('stem')
            if stem:
                roots.add(stem.lower())
            # Only for words long enough that the stem is not a fragment: 'la'
            # and 'ke' would otherwise contribute 'l' and 'k'.
            if len(word) > 3 and "'" not in word:
                derived = strip_ending(word)
                if len(derived) > 2:
                    roots.add(derived)
    return roots, words


def peel_affixes(stem, roots, max_depth=4):
    """Strip affixes until a known root falls out, searching rather than
    peeling greedily.

    A prefix is stripped only from the front and a suffix only from the end.
    Stripping either from either end — which is what this did until a reviewer
    traced it — dissolves ordinary roots into affixes that were never there:
    instanco lost the *suffix* -in- from its front and became 'stanc', tunelo
    lost the *prefix* el- from its end and became 'tun', and eksperto, instali,
    kapelano and familiara went the same way. Those words then reach a reviewer
    filed as derivations of a root they have nothing to do with, and the
    obvious verdict on them — inflection — deletes real vocabulary.

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
    prefixes = sorted(set(PREFIX), key=len, reverse=True)
    suffixes = sorted(set(SUFFIX + PARTICIPLE), key=len, reverse=True)
    # An affix is not a root, however faithfully the Fundamento lists it as a
    # headword. Accepting one as the answer dissolved ordinary international
    # words into their own suffixes: ulano (a lancer) peeled to 'ul', etono to
    # 'et'. The word then reads as a derivation of something it has nothing to
    # do with, and the obvious verdict on it deletes real vocabulary.
    endpoints = roots - set(PREFIX) - set(SUFFIX) - set(PARTICIPLE)
    seen = {stem}
    frontier = [stem]
    for _ in range(max_depth):
        nxt = []
        for current in frontier:
            candidates = [current[len(a):] for a in prefixes
                          if current.startswith(a)]
            candidates += [current[:-len(a)] for a in suffixes
                           if current.endswith(a)]
            for candidate in candidates:
                if len(candidate) < 2 or candidate in seen:
                    continue
                if candidate in endpoints:
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
            # The compound test has to see the stem, not the inflected word.
            # Checked only on the whole token, 'banloko' resolved and
            # 'banlokoj' did not, because the tail was matched as 'lokoj'.
            # A reviewer measured 19% of one queue in this class.
            if is_compound(stem, roots, words):
                return stem, 'known'
    peeled = peel_affixes(low, roots)
    if peeled in roots:
        return peeled, 'known'
    # Some derivations rest on a grammatical word rather than a UV root —
    # treege is tre + eg + e — so retry against the whole-word vocabulary.
    peeled = peel_affixes(low, words)
    if peeled in words:
        return peeled, 'known'
    if is_compound(low, roots, words):
        return low, 'known'
    return low, 'unknown'


def known_stem(part, roots, words):
    """True if this piece of a compound is something we recognise."""
    if len(part) < 2:
        return False
    if part in roots or part in words:
        return True
    if peel_affixes(part, roots) in roots:
        return True
    bare = strip_ending(part)
    return bare in roots or bare in words or peel_affixes(bare, roots) in roots


def is_compound(word, roots, words):
    """True if the word splits into a known root plus a known remainder.

    Esperanto joins roots directly — fervojo is fer + vojo, samideano is
    sam + ide + an + o, tetablo is te + tablo — but it also joins them through
    a connecting vowel,
    vent-o-montrilo, and the second root carries the word's ending. Both had to
    be allowed: without the connecting vowel ventomontrilo stayed unknown even
    though vent and montr are both roots, and without stripping the tail's
    ending the tail of banlokoj was matched as 'lokoj'.
    """
    for cut in range(3, len(word) - 2):
        head, tail = word[:cut], word[cut:]
        # The first piece may be a preposition or a pronoun rather than a root
        # in the dictionary sense: laŭ-plana, ĝis-hejma, mem-turmento.
        #
        # The floor stays at three characters. Lowering it to two admits
        # te-tablo, du-flanke and ok-taga, which are real, but it also admits
        # et-apo, ul-ano and in-stanco, which dissolves three ordinary
        # international words into affixes and costs a reviewer the vocabulary
        # rather than saving them a verdict. Measured both ways; the shorter
        # floor loses more than it gains.
        if head not in roots and head not in GRAMMATICAL:
            continue
        if known_stem(tail, roots, words):
            return True
        if tail[:1] in 'oae' and known_stem(tail[1:], roots, words):
            return True
    return False


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


def participle_infinitive(token, roots, words):
    """The infinitive a participle belongs to, or None.

    A participle is a form of its verb, not a headword of its own. Filed as
    written, alnajlita, neĝkovrita, mokridante and duonfrenezigite each became
    a separate discovery; one reviewer measured 31 of 320 candidates in this
    class and two others reported it.

    Only the adjectival and adverbial participles are reduced. The nominal
    ones are not, for two separate reasons that point the same way: -anto and
    -into name a person and are words in their own right (komencanto is a
    beginner, and a reader looks it up), while -ato and -ito are the shape of
    a great many Latinate nouns whose root merely ends that way. Reducing
    those turned vizito into 'vizi', soldato into 'soldi', komitato into
    'komiti' and apetito into 'apeti' — and no vocabulary check catches it,
    because sold- and vizit- are roots and Esperanto really would build 'soldi'
    from one of them. Every case the reviewers reported is adjectival or
    adverbial: alnajlita, neĝkovrita, mokridante, duonfrenezigite, altirata.
    """
    low = token.lower().strip("'")
    if not PARTICIPLE_ENDING.search(low):
        return None
    for affix in PARTICIPLE:
        for ending in ('ajn', 'aj', 'an', 'a', 'e'):
            suffix = affix + ending
            if not low.endswith(suffix) or len(low) <= len(suffix) + 2:
                continue
            infinitive = low[:-len(suffix)] + 'i'
            if analyse(infinitive, roots, words)[1] == 'known':
                return infinitive
    return None


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
