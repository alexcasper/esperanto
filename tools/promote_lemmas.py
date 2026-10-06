#!/usr/bin/env python3
"""Promote reviewed candidates into DICT/entries.jsonl.

Usage: python3 tools/promote_lemmas.py [--dry-run] [--candidates FILE]

Takes the lemmas a reviewer accepted in DICT/candidates.jsonl (produced by
tools/reconcile_lemmas.py) and writes them into the dictionary in the schema
DICT/README.md documents, merged with the 1905 Universala Vortaro entries and
re-sorted in Esperanto alphabetical order.

Three things have to be right, and none of them are what the miner produced:

  citation form   The miner keys on the form it observed. Esperanto cites
                  verbs in the infinitive, so a lemma attested only as
                  'aspektis' is filed as 'aspekti'; reviewers flagged exactly
                  this and named the intended headword.
  part of speech  Endings decide POS in Esperanto, so -o/-a/-e/-i map
                  straight onto noun/adj/adv/verb. Interjections are the
                  exception — 'ho' and 'nu' end in -o and -u but are neither
                  noun nor verb — and the reviewers' glosses say so outright.
  provenance      A UV entry cites the Fundamento. These cite the corpus:
                  how often the word occurs, in how many independent sources,
                  and a couple of real citations. That is the difference
                  between a dictionary and a word list.

Only `verdict: lemma` entries are promoted. Proper nouns, foreign words,
fragments and OCR artefacts stay out by construction.
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import esperanto  # noqa: E402  (path set above)

# Morpheme glosses come from the UV build, so segmented corpus-mined entries
# gloss affixes exactly as the Fundamento layer does.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), 'DICT', 'tools'))
from build_dict import PREFIXES as AFFIX_PREFIX  # noqa: E402
from build_dict import SUFFIXES as AFFIX_SUFFIX  # noqa: E402

# esperanto.PREFIX also peels el-, for- and ne-, which the UV build glosses
# nowhere (they are words, not UV affix entries); gloss them here.
AFFIX_PREFIX = dict(AFFIX_PREFIX, el='out (of)', **{'for': 'away'},
                    ne='not, un-', retro='backwards')
# Prepositions/adverbs used as prefixes (esp-4qi): glossed by their meaning
# as a prefix, the way the UV glosses mal- or re-.
AFFIX_PREFIX.update({
    'al': 'to, towards', 'antaŭ': 'before, fore-', 'apud': 'beside',
    'ĉe': 'at', 'ĉirkaŭ': 'around', 'de': 'off, away from',
    'ekster': 'outside, extra-', 'en': 'in, into', 'inter': 'between, mutual',
    'kontraŭ': 'against, counter-', 'kun': 'with, together',
    'post': 'after, behind', 'preter': 'past, beyond', 'pri': 'about; '
    'transitivising', 'sen': 'without, -less', 'sub': 'under, sub-',
    'super': 'over, above', 'sur': 'on, upon', 'tra': 'through',
    'trans': 'across, trans-', 'pli': 'more', 'supren': 'upwards',
    'malsupren': 'downwards'})
AFFIX_SUFFIX = dict(AFFIX_SUFFIX, er='single unit, particle',
                    ism='doctrine, -ism')

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENTRIES = os.path.join(ROOT, 'DICT', 'entries.jsonl')
CANDIDATES = os.path.join(ROOT, 'DICT', 'candidates.jsonl')
LEDGER = os.path.join(ROOT, 'DICT', 'verdicts.jsonl')

ALPHA = 'abcĉdefgĝhĥijĵklmnoprsŝtuŭvz'
RANK = {c: i for i, c in enumerate(ALPHA)}

# Finite verb endings; a word attested only in these is cited as infinitive.
TENSE = ('as', 'is', 'os', 'us')
ENDING_POS = {'o': 'noun', 'a': 'adj', 'e': 'adv', 'i': 'verb'}
INTERJECTION = re.compile(r'\binterjection\b', re.IGNORECASE)
# Numerals and prepositions carry no POS-marking ending, so the ending rule
# leaves them unclassified. Both are closed classes, and Esperanto builds
# compounds of them transparently: dudek is du+dek, malantaŭ is mal+antaŭ.
NUMERAL_PARTS = ('unu', 'du', 'tri', 'kvar', 'kvin', 'ses', 'sep', 'ok',
                 'naŭ', 'dek', 'cent', 'mil')
PREPOSITIONS = {'al', 'anstataŭ', 'antaŭ', 'apud', 'ĉe', 'ĉirkaŭ', 'da', 'de',
                'dum', 'ekster', 'el', 'en', 'ĝis', 'inter', 'je', 'kontraŭ',
                'krom', 'kun', 'laŭ', 'malgraŭ', 'per', 'po', 'por', 'post',
                'preter', 'pri', 'pro', 'sen', 'sub', 'super', 'sur', 'tra',
                'trans'}


def is_numeral(word):
    remainder = word
    while remainder:
        for part in sorted(NUMERAL_PARTS, key=len, reverse=True):
            if remainder.startswith(part):
                remainder = remainder[len(part):]
                break
        else:
            return False
    return True


def is_preposition(word):
    if word in PREPOSITIONS:
        return True
    for prefix in ('mal', 'de', 'el', 'ĝis'):
        if word.startswith(prefix) and word[len(prefix):] in PREPOSITIONS:
            return True
    return False


SOURCE_TAG = 'corpus-mined'


def sortkey(word):
    return [RANK.get(c, 99) for c in word.lower()]


def citation_form(lemma, gloss):
    """The form the dictionary should file this under."""
    for tense in TENSE:
        if lemma.endswith(tense) and len(lemma) > len(tense) + 1:
            return lemma[:-len(tense)] + 'i'
    return lemma


def part_of_speech(word, gloss):
    if gloss and INTERJECTION.search(gloss):
        return 'interj'
    pos = ENDING_POS.get(word[-1:])
    if pos:
        return pos
    if is_numeral(word):
        return 'num'
    if is_preposition(word):
        return 'prep'
    # hodiaŭ, morgaŭ, postmorgaŭ: the -aŭ adverbs carry no POS ending.
    if word.endswith('aŭ'):
        return 'adv'
    if "'" in word and is_preposition(word.split("'")[-1]):
        return 'prep'          # dank'al
    return 'unknown'


# Reviewer corrections where the root stock lacks the true root and a
# plausible-looking wrong split wins: ekspiri is the root ekspir- ('exhale',
# 'expire'), not ek- + spiri ('start breathing').
NO_SPLIT = {'ekspiri', 'ŝovinismo'}
# Reviewer-fixed splits where the scoring picks a valid-looking wrong one:
# restarigi is re+star+ig ('re-establish'), not rest+ar+ig.
SPLIT_OVERRIDE = {
    'restarigi': (['re'], 'star', ['ig']),
    'restariĝi': (['re'], 'star', ['iĝ']),
}


def morphology(word, pos, stock=None):
    """UV-shaped morphology: affix segmentation where it self-validates.

    With a root stock (esperanto.root_stock) the stem is segmented into
    prefixes / root / suffixes, glossed like the Fundamento layer; when no
    split leaves an authoritative root (compounds such as batalkampo), the
    entry keeps plain stem + ending, the shape UV uses in the same case.
    """
    if pos not in ENDING_POS.values() or word[-1:] not in ENDING_POS:
        return None
    stem, ending = word[:-1], word[-1:]
    split = SPLIT_OVERRIDE.get(word) or (
        esperanto.segment(stem, stock)
        if stock and word not in NO_SPLIT else None)
    if not split:
        return {'stem': stem, 'ending': ending}
    prefixes, root, suffixes = split
    shape = {}
    if prefixes:
        shape['prefixes'] = [{'m': m, 'gloss': AFFIX_PREFIX.get(m, '')}
                             for m in prefixes]
    shape['stem'] = root
    if suffixes:
        shape['suffixes'] = [{'m': m, 'gloss': AFFIX_SUFFIX.get(m, '')}
                             for m in suffixes]
    shape['ending'] = ending
    return shape


def is_derived(word, roots, words):
    """True if the word is built by regular affixation on a root we hold.

    Settled policy: a productive derivation (reĝino, duono, treege) earns an
    entry, but is flagged, so a consumer wanting only roots and opaque
    compounds can filter on it. Reviewers disagreed 37 times about whether
    such words were headwords or inflections; both readings were defensible,
    so the dictionary records the fact rather than picking a side and
    discarding the other reading's view.
    """
    bare = word[:-1] if word[-1:] in ENDING_POS else word
    if bare in roots or bare in words:
        return False
    return esperanto.peel_affixes(bare, roots) in roots


def build_entry(record, roots, words, stock=None):
    gloss = (record.get('gloss') or '').strip()
    word = citation_form(record['lemma'], gloss)
    pos = part_of_speech(word, gloss)
    entry = {'word': word, 'pos': pos, 'gloss_en': gloss}
    shape = morphology(word, pos, stock)
    if shape:
        # `root` stays the whole word stem, as on every earlier corpus-mined
        # entry; the segmented base root is morphology.stem, as in the UV.
        entry['root'] = word[:-1]
        entry['morphology'] = shape
    entry['source'] = SOURCE_TAG
    entry['attestation'] = {
        'count': record.get('count', 0),
        'sources': len(record.get('sources') or []),
    }
    entry['citations'] = [{'source': c['source'], 'text': c['text']}
                          for c in (record.get('citations') or [])[:3]]
    if is_derived(word, roots, words):
        entry['derived'] = True
    return entry


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--candidates', default=CANDIDATES)
    parser.add_argument('--rebuild', action='store_true',
                        help='drop existing corpus-mined entries first, so the '
                             'promotion can be re-run after a review round')
    parser.add_argument('--resegment', metavar='BATCH_PREFIX', default=None,
                        help='recompute morphology of existing corpus-mined '
                             'entries reviewed in a ledger batch whose name '
                             'starts with BATCH_PREFIX (e.g. v2-), after the '
                             'segmenter improves; nothing else is touched')
    args = parser.parse_args()

    if not os.path.exists(args.candidates):
        sys.exit('%s not found — run tools/reconcile_lemmas.py first'
                 % args.candidates)

    with open(ENTRIES, encoding='utf-8') as fh:
        existing = [json.loads(line) for line in fh if line.strip()]
    dropped = 0
    if args.rebuild:
        before = len(existing)
        existing = [e for e in existing if e.get('source') != SOURCE_TAG]
        dropped = before - len(existing)
    known = {e['word'].lower() for e in existing}
    # Build the vocabulary from what will actually remain, not from the file on
    # disk: after --rebuild that file still holds the previous run's mined
    # entries, so every derivation would match a root promoted last time and
    # none would be flagged.
    roots, words = set(), set()
    for entry in existing:
        words.add(entry['word'].lower())
        if entry.get('root'):
            roots.add(entry['root'].lower())
        stem = (entry.get('morphology') or {}).get('stem')
        if stem:
            roots.add(stem.lower())

    stock = esperanto.root_stock(ENTRIES)
    resegmented = 0
    if args.resegment:
        batches = {}
        with open(LEDGER, encoding='utf-8') as fh:
            for line in fh:
                if line.strip():
                    rec = json.loads(line)
                    batches[rec['lemma']] = rec.get('reviewed_in') or []
        for entry in existing:
            if entry.get('source') != SOURCE_TAG or not any(
                    b.startswith(args.resegment)
                    for b in batches.get(entry['word'], [])):
                continue
            shape = morphology(entry['word'], entry['pos'], stock)
            if shape and shape != entry.get('morphology'):
                entry['morphology'] = shape
                resegmented += 1
    accepted, promoted, skipped, ungloss = 0, [], [], []
    seen = set()
    with open(args.candidates, encoding='utf-8') as fh:
        for line in fh:
            if not line.strip():
                continue
            record = json.loads(line)
            if record.get('verdict') != 'lemma':
                continue
            accepted += 1
            if not (record.get('gloss') or '').strip():
                ungloss.append(record['lemma'])
                continue
            entry = build_entry(record, roots, words, stock)
            key = entry['word'].lower()
            if key in known:
                skipped.append((entry['word'], 'already in the dictionary'))
                continue
            if key in seen:
                skipped.append((entry['word'], 'duplicate citation form'))
                continue
            if entry['pos'] == 'unknown':
                # The schema has a closed POS list; an entry we cannot classify
                # is reported rather than shipped with an invalid value.
                skipped.append((entry['word'], 'part of speech unresolved'))
                continue
            seen.add(key)
            promoted.append(entry)

    merged = sorted(existing + promoted, key=lambda e: sortkey(e['word']))
    if not args.dry_run:
        tmp = ENTRIES + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as fh:
            for entry in merged:
                fh.write(json.dumps(entry, ensure_ascii=False) + '\n')
        os.replace(tmp, ENTRIES)

    by_pos = {}
    for entry in promoted:
        by_pos[entry['pos']] = by_pos.get(entry['pos'], 0) + 1
    print('%s%d accepted, %d promoted, %d skipped, %d without a gloss'
          % ('[dry run] ' if args.dry_run else '', accepted, len(promoted),
             len(skipped), len(ungloss)))
    derived = sum(1 for e in promoted if e.get('derived'))
    if dropped:
        print('  rebuild: dropped %d existing corpus-mined entries' % dropped)
    if args.resegment:
        print('  resegment: %d entries got new morphology' % resegmented)
    print('  dictionary: %d → %d entries (%d flagged derived)'
          % (len(existing), len(merged), derived))
    print('  by pos: %s' % ', '.join('%s=%d' % kv for kv in
                                     sorted(by_pos.items(), key=lambda kv: -kv[1])))
    for word, why in skipped[:8]:
        print('  - %-18s %s' % (word, why))
    if ungloss:
        print('  no gloss (left out): %s' % ', '.join(ungloss[:8]))
    return 0


if __name__ == '__main__':
    sys.exit(main())
