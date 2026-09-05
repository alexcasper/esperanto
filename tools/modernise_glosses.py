#!/usr/bin/env python3
"""Give the O'Connor entries a present-day gloss without losing the 1906 one.

Usage: python3 tools/modernise_glosses.py [--apply]

The O'Connor layer takes its English verbatim from a 1906 dictionary, which is
the right default — the `source: oconnor-1906` tag says whose wording it is,
and a lexicographic record should not be quietly rewritten. Eight entries make
that default untenable, because the period term is not a stylistic difference
but a slur or a clinical label no present-day artefact should repeat as its
own voice.

Each of those entries gets `gloss_en` replaced with a current gloss for the
same Esperanto word, and the original preserved verbatim in `dated_gloss`.
Nothing is deleted: a reader or a historian can still see exactly what the
source said, and the tag still says where it came from.

Only these eight are touched, and each replacement glosses the *Esperanto*
word as a modern dictionary would — nigrulo really does mean a Black person,
kriplulo really is the word a 1906 text uses for a disabled person, and
pretending otherwise would be its own kind of falsification.
"""
import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENTRIES = os.path.join(ROOT, 'DICT', 'entries.jsonl')

# word -> (the gloss to ship, the 1906 wording it replaces)
MODERNISED = {
    'nigrulo': 'Black person',
    'kriplulo': 'disabled person',
    'kripligi': 'to disable, to maim',
    'lunatikulo': 'person with a mental illness',
    'malspritulo': 'person with an intellectual disability',
    'idiotulo': 'fool; oaf',
    'pantomimo': 'mime; pantomime',
    'sovaĝa': 'wild; untamed; fierce',
}
SOURCE = 'oconnor-1906'


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()

    with open(ENTRIES, encoding='utf-8') as fh:
        entries = [json.loads(line) for line in fh if line.strip()]

    changed, missing = [], set(MODERNISED)
    for entry in entries:
        word = entry['word'].lower()
        if word not in MODERNISED:
            continue
        missing.discard(word)
        if entry.get('source') != SOURCE:
            # The word is now carried by a different layer, so O'Connor's
            # wording is not what ships and there is nothing to modernise.
            continue
        original = entry.get('gloss_en') or ''
        if entry.get('dated_gloss'):
            continue                       # already done, idempotent
        entry['dated_gloss'] = original
        entry['gloss_en'] = MODERNISED[word]
        changed.append((entry['word'], original, MODERNISED[word]))

    print('%s%d of %d entries modernised'
          % ('' if args.apply else '[dry run] ', len(changed), len(MODERNISED)))
    for word, was, now in changed:
        print('  %-12s %-34s -> %s' % (word, repr(was), repr(now)))
    if missing:
        print('  not found in the dictionary: %s' % ', '.join(sorted(missing)))

    if changed and args.apply:
        with open(ENTRIES, 'w', encoding='utf-8') as fh:
            for entry in entries:
                fh.write(json.dumps(entry, ensure_ascii=False) + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
