#!/usr/bin/env python3
"""Measure how Esperanto changes across the dated corpus.

Usage: python3 tools/diachronic.py [--min-tokens N] [--confidence high|medium]

Reads RAW/DATES.tsv and reports a small set of features by period. The features
are fixed here rather than chosen after looking, because with 27000 dictionary
entries and 5 million tokens something always trends if you go fishing.

  hx-rate          tokens containing ĥ, per 10000. The letter's retreat is the
                   best-known change in written Esperanto — anarĥio to anarkio,
                   ĥemio to kemio — and the corpus recovered 651 ReVo variant
                   pairs of exactly this shape.
  ujo-share        of country names formed with -ujo or -io, the share using
                   -ujo. GRAMMAR 6.1 records that -ujo dominates the corpus
                   without asking when that stops being true.
  compound-tense   'estas/estis/estos' followed by a participle, per 10000
                   finite verbs. GRAMMAR 6.3 records these are rarer than their
                   prominence in grammars suggests.
  accusative       tokens ending in -n after a vowel that can carry one, per
                   10000. A CONTROL: the accusative is Fundamento-fixed and
                   should NOT trend. If it does, the periods differ by
                   something other than date — genre, register or scan quality
                   — and the other figures are suspect too.

Every figure is reported with the tokens behind it and the share contributed by
the period's largest single author or translator, because a decade carried by
one writer measures that writer. --hold-out recomputes with that contributor
removed.
"""
import argparse
import collections
import csv
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORPUS = os.path.join(ROOT, 'CORPUS')
DATES = os.path.join(ROOT, 'RAW', 'DATES.tsv')

WORD = re.compile(r'[a-zĉĝĥĵŝŭ]+', re.I)
HX = re.compile(r'ĥ', re.I)
# Country names: the -ujo/-io alternation applies to these stems, which are the
# ones the Fundamento and the corpus actually use. Matching bare -ujo would
# catch ovujo and abelujo, which are containers, not countries.
COUNTRY = ('angl', 'franc', 'german', 'rus', 'hispan', 'ital', 'pol', 'hungar',
           'ĉin', 'japan', 'turk', 'aŭstr', 'nederland', 'svis', 'sved',
           'norveg', 'dan', 'finn', 'grek', 'brit', 'amerik', 'belg', 'bulgar',
           'rumen', 'serb', 'kroat', 'ĉeĥ', 'slovak', 'litov', 'latv', 'eston',
           'pers', 'arab', 'hebre', 'egipt', 'hind', 'skot', 'irland')
UJO = re.compile(r'\b(%s)uj(o|on|oj|ojn)\b' % '|'.join(COUNTRY), re.I)
IO_FORM = re.compile(r'\b(%s)i(o|on|oj|ojn)\b' % '|'.join(COUNTRY), re.I)
BE = re.compile(r'\b(estas|estis|estos|estus)\s+(\w+?)(anta|inta|onta|ata|ita|ota)\b',
                re.I)
FINITE = re.compile(r'\b\w+(as|is|os|us)\b', re.I)
ACCUSATIVE = re.compile(r'\b\w*[oaeu]n\b', re.I)


def load_dates(min_confidence):
    allowed = {'high'} if min_confidence == 'high' else {'high', 'medium'}
    rows = {}
    with open(DATES, encoding='utf-8') as fh:
        for row in csv.DictReader(fh, delimiter='\t'):
            if row['written'] and row['confidence'] in allowed:
                rows[row['source']] = (int(row['written']),
                                       row['attributed'] or '(unattributed)')
    return rows


def measure(text):
    """Raw counts for one text."""
    tokens = WORD.findall(text)
    n = len(tokens)
    ujo, io_form = len(UJO.findall(text)), len(IO_FORM.findall(text))
    return {
        'tokens': n,
        'hx': sum(1 for t in tokens if HX.search(t)),
        'ujo': ujo,
        'io': io_form,
        'compound': len(BE.findall(text)),
        'finite': len(FINITE.findall(text)),
        'accusative': len(ACCUSATIVE.findall(text)),
    }


def rates(totals):
    n = max(totals['tokens'], 1)
    country = totals['ujo'] + totals['io']
    return {
        'hx-rate': 10000.0 * totals['hx'] / n,
        'ujo-share': (100.0 * totals['ujo'] / country) if country else None,
        'compound-tense': (10000.0 * totals['compound']
                           / max(totals['finite'], 1)),
        'accusative': 10000.0 * totals['accusative'] / n,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--confidence', default='medium',
                        choices=['high', 'medium'])
    parser.add_argument('--min-tokens', type=int, default=20000,
                        help='periods thinner than this are reported but '
                             'marked, since a rate over a few thousand tokens '
                             'is noise')
    parser.add_argument('--hold-out', action='store_true',
                        help='also recompute each period without its largest '
                             'single contributor')
    args = parser.parse_args()

    dated = load_dates(args.confidence)
    # Prose ABOUT Esperanto in another language is not evidence about
    # Esperanto. mine_lemmas already keeps this list, and the accusative
    # control is what caught the omission: the Downes textbook made the 1980s
    # read 565 accusatives per 10000 against 850-1040 everywhere else, because
    # most of its tokens are English.
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import mine_lemmas
    excluded = mine_lemmas.ENGLISH_HEAVY | mine_lemmas.MULTILINGUAL
    dropped = [s for s in dated if s in excluded]
    for source in dropped:
        del dated[source]
    periods = collections.defaultdict(collections.Counter)
    by_author = collections.defaultdict(lambda: collections.defaultdict(collections.Counter))

    for source, (year, who) in sorted(dated.items()):
        path = os.path.join(CORPUS, source)
        if not os.path.exists(path):
            continue
        counts = measure(open(path, encoding='utf-8').read())
        decade = year // 10 * 10
        periods[decade].update(counts)
        by_author[decade][who].update(counts)

    print('confidence: %s and above; %d sources, %d decades'
          % (args.confidence, len(dated), len(periods)))
    if dropped:
        print('excluded as foreign-language prose about Esperanto: %s'
              % ', '.join(sorted(d[:40] for d in dropped)))
    print()
    header = ('period', 'tokens', 'top share', 'ĥ/10k', '-ujo%',
              'cmp-tense', 'acc/10k')
    print('%-8s %9s %10s %8s %7s %10s %9s' % header)
    for decade in sorted(periods):
        totals = periods[decade]
        figures = rates(totals)
        who = by_author[decade]
        top, top_counts = max(who.items(), key=lambda kv: kv[1]['tokens'])
        share = 100.0 * top_counts['tokens'] / max(totals['tokens'], 1)
        thin = ' (thin)' if totals['tokens'] < args.min_tokens else ''
        print('%-8s %9d %9.0f%% %8.1f %6s %10.1f %9.0f%s'
              % (str(decade) + 's', totals['tokens'], share,
                 figures['hx-rate'],
                 '—' if figures['ujo-share'] is None
                 else '%.0f' % figures['ujo-share'],
                 figures['compound-tense'], figures['accusative'], thin))

        if args.hold_out and len(who) > 1:
            rest = collections.Counter()
            for name, counts in who.items():
                if name != top:
                    rest.update(counts)
            if rest['tokens']:
                other = rates(rest)
                print('%-8s %9d %10s %8.1f %6s %10.1f %9.0f'
                      % ('  minus ' + top[:12], rest['tokens'], '',
                         other['hx-rate'],
                         '—' if other['ujo-share'] is None
                         else '%.0f' % other['ujo-share'],
                         other['compound-tense'], other['accusative']))
    print()
    print('accusative is a control: it is fixed by the Fundamento and should '
          'not trend.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
