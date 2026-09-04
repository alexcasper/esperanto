#!/usr/bin/env python3
"""Fill the gaps in the correlative grid.

Usage: python3 tools/complete_correlatives.py [--apply]

The tabelvortoj are a closed class of exactly forty-five words on a grid of
nine endings by five series, and the grid is complete by rule: the ending
carries the meaning, the initial carries the series, and every cell exists.
The dictionary held 39 of them. The six missing — nenial, neniom, ties, ĉial,
ĉies, ĉiom — are not rare or doubtful words; they are simply cells nobody
happened to source, and a reader who looks up *kial* and *tial* and then fails
to find *ĉial* is being told something false about the language.

They are generated from the grid rather than transcribed, so the glosses
cannot disagree with GRAMMAR/grammar.md, which carries the same table with
corpus citations.
"""
import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENTRIES = os.path.join(ROOT, 'DICT', 'entries.jsonl')

SERIES = [('i', 'some', 'indefinite'),
          ('ki', 'what', 'interrogative / relative'),
          ('ti', 'that', 'demonstrative'),
          ('ĉi', 'every', 'universal'),
          ('neni', 'no', 'negative')]

# ending, part of speech, and how the two halves combine into a gloss.
ENDINGS = [('o', 'pron', '%(series)sthing', 'thing'),
           ('u', 'pron', '%(series)sone', 'individual'),
           ('a', 'adj', 'of %(series)s kind', 'kind'),
           ('es', 'pron', "%(series)sone's", 'possession'),
           ('e', 'adv', '%(series)swhere', 'place'),
           ('am', 'adv', '%(series)stime', 'time'),
           ('al', 'adv', 'for %(series)s reason', 'reason'),
           ('el', 'adv', 'in %(series)s way', 'manner'),
           ('om', 'adv', '%(series)s quantity', 'quantity')]

GLOSS = {
    'io': 'something', 'kio': 'what', 'tio': 'that', 'ĉio': 'everything',
    'nenio': 'nothing',
    'iu': 'someone', 'kiu': 'who, which', 'tiu': 'that one',
    'ĉiu': 'everyone, each', 'neniu': 'no one',
    'ia': 'some kind of', 'kia': 'what kind of', 'tia': 'that kind of',
    'ĉia': 'every kind of', 'nenia': 'no kind of',
    'ies': "someone's", 'kies': 'whose', 'ties': "that one's",
    'ĉies': "everyone's", 'nenies': "no one's",
    'ie': 'somewhere', 'kie': 'where', 'tie': 'there', 'ĉie': 'everywhere',
    'nenie': 'nowhere',
    'iam': 'sometime, ever', 'kiam': 'when', 'tiam': 'then',
    'ĉiam': 'always', 'neniam': 'never',
    'ial': 'for some reason', 'kial': 'why', 'tial': 'therefore',
    'ĉial': 'for every reason', 'nenial': 'for no reason',
    'iel': 'somehow', 'kiel': 'how, as', 'tiel': 'thus, so',
    'ĉiel': 'in every way', 'neniel': 'in no way',
    'iom': 'some, a little', 'kiom': 'how much', 'tiom': 'that much',
    'ĉiom': 'all of it', 'neniom': 'none',
}


def grid():
    for initial, _short, series_name in SERIES:
        for ending, pos, _pattern, meaning in ENDINGS:
            word = initial + ending
            yield word, pos, meaning, series_name


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()

    with open(ENTRIES, encoding='utf-8') as fh:
        entries = [json.loads(line) for line in fh if line.strip()]
    have = {e['word'].lower() for e in entries}

    added = []
    for word, pos, meaning, series in grid():
        if word in have:
            continue
        if word not in GLOSS:
            sys.exit('no gloss for %r — the grid and the gloss table '
                     'disagree, so nothing was written.' % word)
        added.append({
            'word': word,
            'pos': pos,
            'gloss_en': GLOSS[word],
            'source': 'correlative-grid',
            'morphology': {'series': series, 'meaning': meaning},
        })

    print('%s%d correlatives missing of 45'
          % ('' if args.apply else '[dry run] ', len(added)))
    for entry in added:
        print('  %-8s %-5s %-22s (%s, %s)'
              % (entry['word'], entry['pos'], entry['gloss_en'],
                 entry['morphology']['series'], entry['morphology']['meaning']))

    if added and args.apply:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import repair_headwords          # noqa: E402  (for the sort order)
        entries.extend(added)
        entries.sort(key=lambda e: repair_headwords.sortkey(e['word']))
        with open(ENTRIES, 'w', encoding='utf-8') as fh:
            for entry in entries:
                fh.write(json.dumps(entry, ensure_ascii=False) + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
