#!/usr/bin/env python3
"""Make every headword in DICT/entries.jsonl a single Esperanto word.

Usage: python3 tools/repair_headwords.py [--apply]

The ReVo merge wrote a variant pair into one headword field, separated by a
comma, and 1466 entries — 5.4% of the dictionary — carry a headword that is
therefore not a word and cannot be looked up:

    aboli,i            adultulo,ulino      abrikotujo,arbo
    anarĥio,anarkio    aĥ,                 acetilĥolino,o

The second half is NOT reconstructed here, and that is the point of this
script rather than an omission. The encoding is inconsistent — 'anarĥio,anarkio'
holds two complete words, 'adultulo,ulino' holds a word and a differing tail
whose shared prefix ('adultul') is nowhere in the string, and 241 are mangled
beyond reading ('antigvo-barbudo,10okajbarbudooficialainformodeade,numero11').
Inferring the shared prefix by asking which candidate the morphology accepts
was tried and produced 'adultuloulino', 'aerarflugo' and 'abrikotujarbo': with
27000 entries the morphology accepts the wrong answer as readily as the right
one. So the headword is truncated at the first comma, which is correct in
every case sampled, and the original string is kept in `revo_raw` so that a
proper re-merge from the ReVo XML can find and replace exactly these entries.

That re-merge now exists: `tools/repair_revo_headwords.py` fetches the source
articles and recovers the second form properly — 'abrikotujo,arbo' is
abrikotujo and abrikotarbo, not the 'abrikotujarbo' guessed here. Run it after
this one. What remains below is still the right first step, because it makes
every headword a word even for the articles that cannot be fetched.

Two further repairs, both small and both certain:

  * Eight headwords differ from an existing entry only in case, because the
    Fundamento capitalises a proper noun and ReVo does not: Dio/dio,
    Pasko/pasko, Marto/marto. The Fundamento spelling wins as the
    authoritative layer, and a gloss the other entry had that this one lacks
    is carried across, so 'god' and 'Passover' are not lost.
  * Five glosses begin with the ReVo officialness marker '*', which is markup
    that leaked into the text: '*need', '*say', '*Messiah'.
"""
import argparse
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENTRIES = os.path.join(ROOT, 'DICT', 'entries.jsonl')

# Esperanto alphabetical order, matching the order entries.jsonl is written in.
ALPHABET = 'abcĉdefgĝhĥijĵklmnoprsŝtuŭvz'
RANK = {letter: index for index, letter in enumerate(ALPHABET)}

# Which layer wins when two entries collide. The Fundamento is authoritative;
# a corpus-mined entry rests on citations, so it outranks a compiled word list.
SOURCE_RANK = ['Fundamento/UV-1905', 'corpus-mined', 'ReVo/UV-*', 'ReVo/OA-',
               'ReVo', 'oconnor-1906']


# A headword carrying a digit or a colon has a bibliographic reference glued
# to it by the same merge defect: 'akenoopiv1' is Aachen with a PIV citation
# attached, 'vundlokoolokoboriskondratjev:rusa-esperantavortaro' is a sore
# spot with a whole dictionary's title. Thirteen of them, none recoverable by
# rule — the first form ends somewhere inside the run and nothing marks where —
# so they are dropped and listed for the re-merge that can do it properly.
REFERENCE_LEAK = re.compile(r'[\d:]')


def sortkey(word):
    return [RANK.get(character, 99) for character in word.lower()]


def source_rank(entry):
    source = entry.get('source') or ''
    for index, prefix in enumerate(SOURCE_RANK):
        if source.startswith(prefix):
            return index
    return len(SOURCE_RANK)


def merge_gloss(winner, loser):
    """Keep a sense the losing entry had and the winner does not.

    Dio is glossed 'God' and dio 'god'; Pasko is 'Easter' and pasko
    'Passover'. Dropping the duplicate silently would drop the second sense,
    which is the one thing this repair must not do.
    """
    kept = (winner.get('gloss_en') or '').strip()
    other = (loser.get('gloss_en') or '').strip()
    if not other or other.lower() == kept.lower():
        return kept or other
    if other.lower() in kept.lower():
        return kept
    return '%s; %s' % (kept, other) if kept else other


def repair(entries):
    changes = {'truncated': [], 'case-merged': [], 'gloss-marker': [],
               'dropped as duplicate': [], 'dropped, reference glued on': [],
               'left alone': []}

    for entry in entries:
        gloss = entry.get('gloss_en')
        if gloss and gloss.startswith('*'):
            entry['gloss_en'] = gloss.lstrip('*').strip()
            changes['gloss-marker'].append(entry['word'])

        word = entry['word']
        if REFERENCE_LEAK.search(word.split(',')[0]):
            changes['dropped, reference glued on'].append(
                '%s = %r' % (word[:46], (entry.get('gloss_en') or '')[:30]))
            entry['word'] = None
            continue
        if ',' in word:
            head = word.split(',')[0].strip()
            if not head:
                changes['left alone'].append(word)
                continue
            entry['revo_raw'] = word
            entry['word'] = head
            changes['truncated'].append('%s -> %s' % (word, head))
        elif ' ' in word or len(word) > 28:
            # A multi-word name run together, or a reference glued on. Neither
            # can be split by rule, so they are reported rather than guessed at.
            changes['left alone'].append(word)

    # Now collapse collisions, including the ones truncation just created.
    best = {}
    for entry in entries:
        if entry['word'] is None:
            continue
        key = entry['word'].lower()
        if key not in best:
            best[key] = entry
            continue
        winner, loser = best[key], entry
        if source_rank(loser) < source_rank(winner):
            winner, loser = loser, winner
        winner['gloss_en'] = merge_gloss(winner, loser)
        best[key] = winner
        label = ('case-merged' if winner['word'] != loser['word']
                 and winner['word'].lower() == loser['word'].lower()
                 else 'dropped as duplicate')
        changes[label].append('%s <- %s (%s)'
                              % (winner['word'], loser.get('revo_raw')
                                 or loser['word'], loser.get('source')))

    kept = sorted(best.values(), key=lambda e: sortkey(e['word']))
    return kept, changes


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--limit', type=int, default=8)
    args = parser.parse_args()

    with open(ENTRIES, encoding='utf-8') as fh:
        entries = [json.loads(line) for line in fh if line.strip()]
    before = len(entries)
    kept, changes = repair(entries)

    print('%s%d entries -> %d' % ('' if args.apply else '[dry run] ',
                                  before, len(kept)))
    for label in ('truncated', 'gloss-marker', 'case-merged',
                  'dropped as duplicate', 'dropped, reference glued on',
                  'left alone'):
        rows = changes[label]
        print('  %-22s %5d' % (label, len(rows)))
        for row in rows[:args.limit]:
            print('        %s' % row)

    broken = [e['word'] for e in kept if ',' in e['word']]
    # A space is not a defect. Once repair_revo_headwords has recovered the
    # multi-word terms from the source, 'Aleksandro la Granda' and 'amina
    # acido' are headwords with spaces in them, and reporting those as
    # unrepaired damage would be crying wolf.
    multiword = [e['word'] for e in kept if ' ' in e['word']]
    print('  headwords still carrying a comma: %d %s'
          % (len(broken), broken[:4]))
    print('  multi-word headwords (not a defect): %d %s'
          % (len(multiword), multiword[:3]))

    if args.apply:
        with open(ENTRIES, 'w', encoding='utf-8') as fh:
            for entry in kept:
                fh.write(json.dumps(entry, ensure_ascii=False) + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
