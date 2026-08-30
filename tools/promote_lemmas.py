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

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENTRIES = os.path.join(ROOT, 'DICT', 'entries.jsonl')
CANDIDATES = os.path.join(ROOT, 'DICT', 'candidates.jsonl')

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
    return 'unknown'


def morphology(word, pos):
    """Stem plus ending, the shape UV entries use when affixes do not resolve."""
    if pos in ENDING_POS.values() and word[-1:] in ENDING_POS:
        return {'stem': word[:-1], 'ending': word[-1:]}
    return None


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


def build_entry(record, roots, words):
    gloss = (record.get('gloss') or '').strip()
    word = citation_form(record['lemma'], gloss)
    pos = part_of_speech(word, gloss)
    entry = {'word': word, 'pos': pos, 'gloss_en': gloss}
    shape = morphology(word, pos)
    if shape:
        entry['root'] = shape['stem']
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
    roots, words = esperanto.load_vocabulary()

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
            entry = build_entry(record, roots, words)
            key = entry['word'].lower()
            if key in known:
                skipped.append((entry['word'], 'already in the dictionary'))
                continue
            if key in seen:
                skipped.append((entry['word'], 'duplicate citation form'))
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
