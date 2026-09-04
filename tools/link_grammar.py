#!/usr/bin/env python3
"""Point the entries a reader cannot understand alone at the section that
explains them.

Usage: python3 tools/link_grammar.py [--apply]

Most dictionary entries need no help: 'abelo — bee' is complete. A closed
class of them is not. An affix entry says '-in- — feminine' and leaves the
reader to discover that Esperanto builds *reĝino* from *reĝo* by rule; a
correlative says 'kial — why' without the grid that makes all forty-five
predictable; an ending is not a word at all. Those are exactly the entries
GRAMMAR/grammar.md exists for, so each one gets a `grammar` field naming the
section and its anchor.

The mapping is by part of speech and by the correlative pattern, never by a
hand-written list of words, so it stays correct as the dictionary grows.
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import esperanto  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENTRIES = os.path.join(ROOT, 'DICT', 'entries.jsonl')
GRAMMAR = os.path.join(ROOT, 'GRAMMAR', 'grammar.md')

# Section title -> the anchor GitHub generates for it. Verified against the
# file rather than assumed: a heading that moves or is renamed must break this
# script loudly, not link to nothing.
SECTIONS = {
    'morphology': '## 2. Morfologio — Morphology',
    'correlatives': '### La tabelvortoj — the correlatives',
    'fundamentals': '## 1. Fundamentoj — Fundamentals',
    'orthography': '## 4. Fonologio kaj Ortografio',
}

# Which entries cannot be understood from their own gloss.
BY_POS = {
    'prefix': 'morphology',
    'suffix': 'morphology',
    'ending': 'morphology',
    'art': 'fundamentals',
    'pron': 'fundamentals',
    'prep': 'fundamentals',
    'conj': 'fundamentals',
    'particle': 'fundamentals',
    'num': 'fundamentals',
}


def anchor(heading):
    """The fragment GitHub derives from a Markdown heading.

    Lowercase, drop everything that is not a letter, digit, space or hyphen,
    then turn each remaining space into a hyphen — each one, not each run.
    That distinction is the whole of the correctness here: every heading in
    this file separates its Esperanto and English halves with an em dash
    surrounded by spaces, the dash is dropped as punctuation, and the two
    spaces it leaves behind become two hyphens. Collapsing them produces
    '#2-morfologio-morphology', which is a dead link.
    """
    text = heading.lstrip('#').strip().lower()
    text = re.sub(r'[^\w\s-]', '', text, flags=re.UNICODE)
    return '#' + ''.join('-' if character.isspace() else character
                         for character in text)


def load_sections():
    with open(GRAMMAR, encoding='utf-8') as fh:
        headings = [line.rstrip('\n') for line in fh if line.startswith('#')]
    resolved = {}
    for key, heading in SECTIONS.items():
        if heading not in headings:
            sys.exit('GRAMMAR/grammar.md has no heading %r — the cross-links '
                     'would point at nothing, so nothing was written.'
                     % heading)
        resolved[key] = {'section': heading.lstrip('#').strip(),
                         'anchor': 'GRAMMAR/grammar.md' + anchor(heading)}
    return resolved


def section_for(entry):
    word = entry['word'].lower().lstrip('-').rstrip('-')
    if esperanto.CORRELATIVE.match(word):
        return 'correlatives'
    return BY_POS.get(entry.get('pos'))


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()

    sections = load_sections()
    with open(ENTRIES, encoding='utf-8') as fh:
        entries = [json.loads(line) for line in fh if line.strip()]

    counts = {}
    for entry in entries:
        key = section_for(entry)
        if key:
            entry['grammar'] = sections[key]
            counts[key] = counts.get(key, 0) + 1
        else:
            entry.pop('grammar', None)

    print('%s%d of %d entries linked'
          % ('' if args.apply else '[dry run] ', sum(counts.values()),
             len(entries)))
    for key in sorted(counts):
        print('  %-14s %4d  ->  %s'
              % (key, counts[key], sections[key]['anchor']))

    if args.apply:
        with open(ENTRIES, 'w', encoding='utf-8') as fh:
            for entry in entries:
                fh.write(json.dumps(entry, ensure_ascii=False) + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
