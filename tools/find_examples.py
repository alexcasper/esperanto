#!/usr/bin/env python3
"""Find attested examples of a grammatical pattern in CORPUS/.

Usage:
  python3 tools/find_examples.py PATTERN [--limit 5] [--count] [--source GLOB]
  python3 tools/find_examples.py --compare PATTERN_A PATTERN_B

Written for the grammar guide, where every claim is supposed to rest on a
citation from the corpus rather than on recollection. Two modes matter:

  default    a handful of real sentences illustrating the pattern, each with
             its source, spread across different books rather than taken from
             whichever one happens to be longest
  --compare  frequencies of two competing forms, for the cases where the
             stated rule and actual usage may differ — -ujo against -io for
             country names, for instance. A grammar that says which form the
             corpus prefers is more useful than one that only states a rule.

Patterns are Python regexes matched case-insensitively against whole lines.
"""
import argparse
import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORPUS = os.path.join(ROOT, 'CORPUS')
# English-language and multilingual sources: their sentences are not Esperanto.
EXCLUDE = {'pg-7787.txt', 'pg-8177.txt', 'pg-16967.txt',
           'wsrc-Fundamento_de_Esperanto_Universala_vortaro.txt',
           'wsrc-Fundamento_de_Esperanto_Grammar.txt'}


def sources(pattern='*.txt'):
    return [p for p in sorted(glob.glob(os.path.join(CORPUS, pattern)))
            if os.path.basename(p) not in EXCLUDE]


def search(regex, paths, limit=None, want_count=False):
    compiled = re.compile(regex, re.IGNORECASE)
    hits, total = [], 0
    for path in paths:
        name = os.path.basename(path)
        with open(path, encoding='utf-8') as fh:
            for lineno, line in enumerate(fh, 1):
                if not compiled.search(line):
                    continue
                total += 1
                if want_count:
                    continue
                text = ' '.join(line.split())
                if 30 <= len(text) <= 200:
                    hits.append((name, lineno, text))
    return hits, total


def spread(hits, limit):
    """One example per source before a second from any, so the citations do
    not all come from whichever book is longest."""
    by_source = {}
    for hit in hits:
        by_source.setdefault(hit[0], []).append(hit)
    picked = []
    while len(picked) < limit and any(by_source.values()):
        for name in list(by_source):
            if by_source[name] and len(picked) < limit:
                picked.append(by_source[name].pop(0))
    return picked


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('pattern', nargs='?')
    parser.add_argument('--limit', type=int, default=5)
    parser.add_argument('--count', action='store_true')
    parser.add_argument('--source', default='*.txt')
    parser.add_argument('--compare', nargs=2, metavar=('A', 'B'))
    args = parser.parse_args()

    paths = sources(args.source)
    if args.compare:
        for pattern in args.compare:
            _, total = search(pattern, paths, want_count=True)
            print('%8d  %s' % (total, pattern))
        return 0

    if not args.pattern:
        parser.error('a PATTERN is required unless --compare is used')

    hits, total = search(args.pattern, paths, want_count=args.count)
    if args.count:
        print('%d lines match %s across %d sources' % (total, args.pattern,
                                                       len(paths)))
        return 0
    for name, lineno, text in spread(hits, args.limit):
        print('%s:%d\n  %s\n' % (name, lineno, text))
    print('(%d matching lines in %d sources)' % (total, len(paths)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
