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

Decades are not the only unit available, and they are the worse one: bucketing
by decade lets a single 250k-token book be a period. Three other units are
available here, and they disagree with each other, which is the point:

  --by-text     one observation per text, Spearman's rho against the year.
                No single book can be a period. But an author with six texts
                is still six observations, so this does not remove the author.
  --by-author   one observation per author: their texts pooled, their mean
                year. This is the test that matters, because author and period
                are confounded by construction in this corpus. Two of the three
                candidate trends survive --by-text and die here.
  --stem        one country stem, text by text. A rank correlation cannot show
                you a first attestation, and for -ujo/-io the first attestation
                is the whole finding.

Every rho is reported with a permutation p: the years are shuffled against the
values 20000 times and the p is the share of shuffles reaching |rho|. With
n=23 authors a rank correlation can be carried by two points, so read the
printed table and not the coefficient.
"""
import argparse
import collections
import csv
import os
import random
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


def spearman(pairs):
    """Rank correlation with ties averaged. This project has no third-party
    dependencies, and rho is the right statistic here anyway: the features are
    bounded rates and shares, so a linear fit would assume more than we know."""
    if len(pairs) < 4:
        return None

    def ranks(values):
        order = sorted(range(len(values)), key=lambda i: values[i])
        out = [0.0] * len(values)
        i = 0
        while i < len(order):
            j = i
            while (j + 1 < len(order)
                   and values[order[j + 1]] == values[order[i]]):
                j += 1
            mean = (i + j) / 2.0 + 1
            for k in range(i, j + 1):
                out[order[k]] = mean
            i = j + 1
        return out

    xs, ys = ranks([p[0] for p in pairs]), ranks([p[1] for p in pairs])
    n = len(pairs)
    mx, my = sum(xs) / n, sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    den = (sum((x - mx) ** 2 for x in xs)
           * sum((y - my) ** 2 for y in ys)) ** 0.5
    return num / den if den else None


PERMUTATIONS = 20000


def permutation_p(pairs, observed, seed=20260906):
    """Share of year-shuffles reaching |observed|. Two-sided, and exact enough:
    no scipy, and the sample is small enough that an asymptotic p would be the
    less honest of the two."""
    rng = random.Random(seed)
    years = [p[0] for p in pairs]
    values = [p[1] for p in pairs]
    hits = 0
    for _ in range(PERMUTATIONS):
        rng.shuffle(years)
        shuffled = spearman(list(zip(years, values)))
        if shuffled is not None and abs(shuffled) >= abs(observed):
            hits += 1
    return (hits + 1.0) / (PERMUTATIONS + 1)


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


def corpus_texts(dated, min_tokens):
    """(year, source, who, counts, rates) for every dated text we can read."""
    out = []
    for source, (year, who) in sorted(dated.items()):
        path = os.path.join(CORPUS, source)
        if not os.path.exists(path):
            continue
        counts = measure(open(path, encoding='utf-8').read())
        if counts['tokens'] < min_tokens:
            continue
        out.append((year, source, who, counts, rates(counts)))
    out.sort()
    return out


def by_text(rows, min_country):
    """Each text one observation. A decade cannot be carried by one book here."""
    print('%d texts of 5000+ tokens, %d-%d\n'
          % (len(rows), rows[0][0], rows[-1][0]))
    print('%-16s %8s %8s %5s' % ('feature', 'rho', 'p', 'n'))
    for feature in ('hx-rate', 'compound-tense', 'accusative'):
        pairs = [(year, fig[feature]) for year, _s, _w, _c, fig in rows]
        rho = spearman(pairs)
        print('%-16s %+8.2f %8.4f %5d'
              % (feature, rho, permutation_p(pairs, rho), len(pairs)))
    country = [(year, fig['ujo-share']) for year, _s, _w, c, fig in rows
               if fig['ujo-share'] is not None
               and (c['ujo'] + c['io']) >= min_country]
    if len(country) >= 4:
        rho = spearman(country)
        print('%-16s %+8.2f %8.4f %5d   (texts with %d+ country names)'
              % ('ujo-share', rho, permutation_p(country, rho), len(country),
                 min_country))
    print('\naccusative is the control and should read near zero.')
    first_attestation(rows)

    users = [r for r in rows if r[3]['io'] > 0]
    print('\ntexts using -io for a country at all: %d of %d'
          % (len(users), len(rows)))
    for year, source, who, counts, _fig in users:
        print('   %4d  %-42s %-18s -io=%-4d -ujo=%d'
              % (year, source[:42], who[:18], counts['io'], counts['ujo']))


def first_attestation(rows, boundary=1911):
    """Whether -io occurs at all, before and after the boundary.

    A rate is carried by whoever writes most; a first attestation is not. If no
    text before 1911 uses -io across seventeen hands, that is a fact about the
    period rather than about any writer in it, and it is the only claim in this
    study that survives holding out authors.
    """
    early = [r for r in rows if r[0] < boundary and r[3]['ujo'] + r[3]['io']]
    late = [r for r in rows if r[0] >= boundary and r[3]['ujo'] + r[3]['io']]
    if not (early and late):
        return
    a = sum(1 for r in early if r[3]['io'])
    b = sum(1 for r in late if r[3]['io'])
    rng = random.Random(20260906)
    labels = [1] * (a + b) + [0] * (len(early) + len(late) - a - b)
    hits = sum(1 for _ in range(PERMUTATIONS)
               if (rng.shuffle(labels), sum(labels[:len(early)]))[1] <= a)
    print('\nfirst attestation of -io, split at %d:' % boundary)
    print('   before  %2d texts, %2d hands, %4d country names, %2d use -io'
          % (len(early), len({r[2] for r in early}),
             sum(r[3]['ujo'] + r[3]['io'] for r in early), a))
    print('   after   %2d texts, %2d hands, %4d country names, %2d use -io'
          % (len(late), len({r[2] for r in late}),
             sum(r[3]['ujo'] + r[3]['io'] for r in late), b))
    print('   permutation p (one-sided, text-level) = %.4f'
          % ((hits + 1.0) / (PERMUTATIONS + 1)))


def jackknife(pairs, drop=2):
    """How much of a rho is carried by its most influential few observations.

    With 27 authors and 21 of them at 91-100% -ujo, a rank correlation can be
    produced almost entirely by two points, and the coefficient looks the same
    either way. Refitting without the k observations whose removal moves rho
    most says so. This is reported for every feature, not just the ones that
    look real, because the ones that look real are exactly where the
    temptation is."""
    if len(pairs) - drop < 4:
        return ''
    # Greedily remove the observation whose removal WEAKENS rho most. Removing
    # whichever moves rho furthest in either direction picks the points that
    # oppose the trend and reports a stronger result than the full sample,
    # which is the flattering answer rather than the informative one.
    remaining = list(pairs)
    for _ in range(drop):
        best, best_index = None, None
        for i in range(len(remaining)):
            weakened = abs(spearman(remaining[:i] + remaining[i + 1:]))
            if best is None or weakened < best:
                best, best_index = weakened, i
        remaining.pop(best_index)
    rho = spearman(remaining)
    return ('   without the %d it leans on most: %+.2f p=%.4f'
            % (drop, rho, permutation_p(remaining, rho)))


def by_author(rows, min_country):
    """Authors pooled: the test that removes the confound rather than one name.

    --hold-out drops a period's largest contributor, which answers 'does this
    survive without Lanti'. It cannot answer 'does this survive without
    whichever author happens to carry it', and in this corpus that is the
    question. Pooling each author into one observation does.
    """
    pooled = collections.defaultdict(
        lambda: [[], collections.Counter()])
    for year, _source, who, counts, _fig in rows:
        pooled[who][0].append(year)
        pooled[who][1].update(counts)

    print('%d authors, %d texts\n' % (len(pooled), len(rows)))
    print('%-16s %8s %8s %5s' % ('feature', 'rho', 'p', 'authors'))
    for feature, gate in (('hx-rate', None), ('compound-tense', None),
                          ('accusative', None), ('ujo-share', min_country)):
        pairs = []
        for _who, (years, counts) in pooled.items():
            if gate and counts['ujo'] + counts['io'] < gate:
                continue
            value = rates(counts)[feature]
            if value is not None:
                pairs.append((sum(years) / float(len(years)), value))
        if len(pairs) < 4:
            continue
        rho = spearman(pairs)
        print('%-16s %+8.2f %8.4f %5d%s'
              % (feature, rho, permutation_p(pairs, rho), len(pairs),
                 jackknife(pairs)))

    print('\n-ujo share by author, earliest mean year first:')
    print('%-6s %-26s %7s %7s' % ('year', 'author', '-ujo%', 'texts'))
    listing = []
    for who, (years, counts) in pooled.items():
        if counts['ujo'] + counts['io'] < min_country:
            continue
        listing.append((sum(years) / float(len(years)), who,
                        rates(counts)['ujo-share'], len(years)))
    for year, who, share, texts in sorted(listing):
        print('%-6.0f %-26s %6.0f%% %7d' % (year, who[:26], share, texts))


def by_stem(rows, stem):
    """One stem, text by text. A rank correlation hides first attestation."""
    ujo = re.compile(r'\b%suj(o|on|oj|ojn)\b' % stem, re.I)
    io_form = re.compile(r'\b%si(o|on|oj|ojn)\b' % stem, re.I)
    print('stem %r, every dated text that uses it\n' % stem)
    print('%-6s %-42s %-18s %6s %6s' % ('year', 'source', 'attributed',
                                        '-ujo', '-io'))
    totals = collections.Counter()
    for year, source, who, _counts, _fig in rows:
        text = open(os.path.join(CORPUS, source), encoding='utf-8').read()
        a, b = len(ujo.findall(text)), len(io_form.findall(text))
        if not (a or b):
            continue
        totals['ujo'] += a
        totals['io'] += b
        print('%-6d %-42s %-18s %6d %6d'
              % (year, source[:42], who[:18], a, b))
    print('\ntotal -ujo=%d -io=%d' % (totals['ujo'], totals['io']))


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--confidence', default='medium',
                        choices=['high', 'medium'])
    parser.add_argument('--min-tokens', type=int, default=20000,
                        help='periods thinner than this are reported but '
                             'marked, since a rate over a few thousand tokens '
                             'is noise')
    parser.add_argument('--by-text', action='store_true',
                        help='one observation per text rather than per decade, '
                             'reported as Spearman rho against the year')
    parser.add_argument('--by-author', action='store_true',
                        help='pool each author into one observation: the test '
                             'that actually removes the author confound')
    parser.add_argument('--stem',
                        help='trace one country stem text by text, e.g. austr')
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
    if args.by_text or args.by_author or args.stem:
        rows = corpus_texts(dated, 5000)
        if args.stem:
            by_stem(rows, args.stem)
        elif args.by_author:
            by_author(rows, min_country=5)
        else:
            by_text(rows, min_country=5)
        return 0

    periods = collections.defaultdict(collections.Counter)
    per_decade_author = collections.defaultdict(
        lambda: collections.defaultdict(collections.Counter))

    for source, (year, who) in sorted(dated.items()):
        path = os.path.join(CORPUS, source)
        if not os.path.exists(path):
            continue
        counts = measure(open(path, encoding='utf-8').read())
        decade = year // 10 * 10
        periods[decade].update(counts)
        per_decade_author[decade][who].update(counts)

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
        who = per_decade_author[decade]
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
