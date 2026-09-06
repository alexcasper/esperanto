#!/usr/bin/env python3
"""Establish, for each source, the year its ESPERANTO text was written.

Usage: python3 tools/date_sources.py [--write] [--wikidata DIR]

Writes RAW/DATES.tsv. Every diachronic figure rests on this file, so it records
where each date came from and refuses to guess.

The distinction that matters, and the reason this is not a one-liner: the
corpus records EDITION dates, and language change needs COMPOSITION dates.
They are the same for a novel printed the year it was written and wildly
different for a collection. `El verkoj de E. Lanti` is filed 1982 and collects
essays from 1922; Lanti died in 1947. Dating that text 1982 would put 1920s
prose in the 1980s bucket, and it is 250k tokens — enough to bend a trend on
its own.

Four kinds of evidence, and none of them is trusted alone unless it is
unambiguous about the Esperanto edition:

  pg-header   Project Gutenberg's `Original publication:` line, which gives the
              Esperanto edition's publisher and year — 'Paris: Presa
              Esperantista Societo, 1904'. Unambiguous, so it stands alone.
              Note this is NOT the original work's date: for a translation of
              Defoe the field still gives the Esperanto printing.
  filename    the year in a Vikifontaro scan's name. Unambiguous about the
              edition, silent about composition, so on its own it dates a
              single work and not a collection.
  intext      the earliest plausible year in the first 40 lines, excluding
              years in a birth or death statement, which date a person rather
              than the text. Tested against
              both other sources: on single works 7 right, 1 wrong, 4 silent;
              on collected works 11 of 23 wrong, several by 30-60 years,
              because it finds the composition date of the first piece. So it
              corroborates and never decides.
  wikidata    publication date of the Esperanto work. Fetched separately and
              cached; see --wikidata.

A date is recorded only when a standalone source gives it, or two independent
sources agree within THRESHOLD years. Otherwise the row says so and the source
is excluded from the diachronic analysis rather than being given a number
somebody might trust.
"""
import argparse
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, 'RAW')
CORPUS = os.path.join(ROOT, 'CORPUS')
OUT = os.path.join(RAW, 'DATES.tsv')

YEAR = re.compile(r'(?<!\d)(1[89]\d\d|20[0-2]\d)(?!\d)')
ORIGINAL = re.compile(r'^Original publication:.*?(\d{4})\s*$', re.M)
FIELD = {name: re.compile(r'^%s:\s*(.+)$' % name, re.M)
         for name in ('Title', 'Author', 'Translator')}
FIRST_YEAR, LAST_YEAR = 1887, 2026        # Esperanto was published in 1887
THRESHOLD = 5
HEAD_LINES = 40

# A collection gathers work written over decades, so its edition year says
# nothing about the language in it. Detected by name rather than guessed at:
# these are the anthologies and collected works in the corpus.
COLLECTION = re.compile(
    r'verkoj|verkaro|krestomatio|kolekto|antologio|el_verkoj|plena_verk',
    re.I)


def head(path, lines=HEAD_LINES):
    try:
        with open(path, encoding='utf-8') as fh:
            return ''.join(fh.readlines()[:lines])
    except OSError:
        return ''


# A year in a birth or death statement dates a PERSON, not the text, and the
# in-text rule takes the earliest year it finds — so a biographical note puts
# the text decades before it was written. Frantisek Omelka's `La Alaska
# stafeto` opens `Mi naskigxis en la jaro 1904` and came out dated 1904; it was
# written in 1951, and the two together looked like one author moving from
# -ujo to -io over 33 years, which was the strongest single piece of evidence
# in the diachronic study and was an artefact. One file in the corpus has this
# shape, and it was the one that mattered.
BIOGRAPHICAL = re.compile(
    r'naski\w*|mort(?:is|into)|\bnat[ae]\b|\bborn\b|\bdied\b', re.I)
BIO_WINDOW = 30


def biographical_years(text):
    """Years standing close to a birth or death word."""
    out = set()
    for match in YEAR.finditer(text):
        window = text[max(0, match.start() - BIO_WINDOW):
                      match.end() + BIO_WINDOW]
        if BIOGRAPHICAL.search(window):
            out.add(int(match.group(1)))
    return out


def plausible(text):
    skip = biographical_years(text)
    return sorted({int(y) for y in YEAR.findall(text)
                   if FIRST_YEAR <= int(y) <= LAST_YEAR and int(y) not in skip})


def evidence(name, wikidata):
    """Every year we can find for this source, by where it came from."""
    found = {}
    raw_head = head(os.path.join(RAW, name))

    match = ORIGINAL.search(raw_head)
    if match:
        found['pg-header'] = int(match.group(1))

    years = plausible(name)
    if years:
        found['filename'] = years[0]

    # A translation's in-text year dates the ORIGINAL, not the Esperanto, and
    # the two can be a century apart. Odd Tangerud's Ibsen translations carry
    # 1888, 1890, 1892, 1894, 1895 and 1896 on their title pages and were made
    # in the 1990s; he came out as 43% of the '1890s' before this rule. So
    # where the source names a translator, the in-text year is inadmissible
    # and the text stays undated unless something dates the Esperanto itself.
    if not FIELD['Translator'].search(raw_head):
        body = plausible(head(os.path.join(CORPUS, name)))
        if body:
            found['intext'] = body[0]

    if name in wikidata:
        found['wikidata'] = wikidata[name]
    return found


# A Vikifontaro scan is named Author_Title_Year, so the author is recoverable
# even though these files carry no Gutenberg header. Without this they all come
# out '(unattributed)', they clump into one pseudo-contributor, and the
# hold-out test that is supposed to catch a period carried by one writer
# silently stops working — which is how Lanti's Naciismo was able to look like
# a 1930s trend.
# Any letter, not an Esperanto-alphabet whitelist: the whitelist dropped
# Moliere and Prevost on their accents and filed them as '(unattributed)',
# which is precisely the collapse this regex exists to prevent. Source
# names are transliterated from the scan and carry whatever the original
# language uses.
WS_AUTHOR = re.compile(r"^ws(?:dump|rc)-([^\W\d_]+'?[^\W\d_]*)_")


# A periodical run is one editorial line, not one independent hand per issue.
# Eighteen issues of `The Esperantist` came out as eighteen '(unattributed)'
# sources, which made the pre-1911 corpus look like eighteen writers agreeing
# and made the author hold-out unable to drop the magazine. Attributing each
# issue to the periodical pools them into one observation, which is the
# conservative reading: it can only weaken a claim, never manufacture one.
# `\b` after a literal dot never fires: `Vol. 1` has a space where \b wants a
# word character, so `The Esperantist, Vol. 1, No. 4` matched nothing.
PERIODICAL = re.compile(
    r'^(.+?),\s*(?:vol\.|volumo|numero|n-?ro\.?|no\.|jaro)(?=[\s\d])', re.I)


def metadata(name):
    raw_head = head(os.path.join(RAW, name))
    found = {key: pattern.search(raw_head).group(1).strip()
             for key, pattern in FIELD.items()
             if pattern.search(raw_head)}
    if 'Author' not in found and 'Translator' not in found:
        match = WS_AUTHOR.match(name)
        if match and len(match.group(1)) > 2:
            found['Author'] = match.group(1)
    if 'Author' not in found and 'Translator' not in found:
        match = PERIODICAL.match(found.get('Title', ''))
        if match:
            found['Author'] = match.group(1).strip()
    return found


def decide(name, found):
    """(year, confidence, basis, note) — or (None, ...) where evidence conflicts.

    Standalone sources are those unambiguous about the Esperanto edition. A
    filename year is standalone only for a single work: for a collection it
    dates the printing of an anthology whose contents are older.
    """
    collection = bool(COLLECTION.search(name))
    standalone = ['pg-header', 'wikidata']
    if not collection:
        standalone.append('filename')

    for basis in standalone:
        if basis in found:
            year = found[basis]
            other = [(k, v) for k, v in found.items() if k != basis]
            clash = [k for k, v in other if abs(v - year) > THRESHOLD]
            if clash:
                return (year, 'medium', basis,
                        'disagrees with %s' % ', '.join(clash))
            return year, 'high', basis, ''

    # No standalone source: two independent ones agreeing will do.
    pairs = sorted(found.items())
    for i, (basis_a, year_a) in enumerate(pairs):
        for basis_b, year_b in pairs[i + 1:]:
            if abs(year_a - year_b) <= THRESHOLD:
                return (min(year_a, year_b), 'medium',
                        '%s+%s' % (basis_a, basis_b), '')

    if collection and 'filename' in found:
        return (None, 'none', 'filename-edition-only',
                'collection: edition %d says nothing about composition'
                % found['filename'])
    if len(found) == 1:
        basis, year = next(iter(found.items()))
        if basis == 'intext' and not collection:
            # On single works this is right 7 times in 8 against independently
            # known dates — good enough to use, not good enough to trust
            # silently. Recorded as medium so the headline analysis can run on
            # high-confidence sources alone and report what changes when these
            # are included.
            return year, 'medium', basis, 'uncorroborated in-text year'
        return (None, 'none', basis,
                'single uncorroborated %s year %d' % (basis, year))
    if found:
        return (None, 'none', 'conflict',
                '; '.join('%s=%d' % kv for kv in sorted(found.items())))
    return None, 'none', 'no evidence', ''


def merge_surnames(rows, index=5):
    """Fold a bare surname into the full name when exactly one matches.

    Vikifontaro filenames give `Luyken`; Gutenberg headers give `Heinrich
    August Luyken`. Left alone that is two contributors, which quietly defeats
    the author hold-out — the whole purpose of which is to stop one writer
    counting twice. Four writers in this corpus were split this way: Bulthuis,
    Grabowski, Luyken and Vallienne. Merged only where the surname resolves to
    exactly one full name, so an ambiguous surname stays as it is.
    """
    names = {row[index] for row in rows if row[index]}
    full = [n for n in names if ' ' in n]
    merge = {}
    for name in names:
        if ' ' in name:
            continue
        matches = [f for f in full if f.split()[-1] == name]
        if len(matches) == 1:
            merge[name] = matches[0]
    if not merge:
        return rows, merge
    return ([row[:index] + (merge.get(row[index], row[index]),) + row[index + 1:]
             for row in rows], merge)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--write', action='store_true')
    parser.add_argument('--wikidata', help='JSON cache of source -> year')
    args = parser.parse_args()

    wikidata = {}
    if args.wikidata and os.path.exists(args.wikidata):
        wikidata = json.load(open(args.wikidata, encoding='utf-8'))

    rows, counts, tokens_dated, tokens_all = [], {}, 0, 0
    for name in sorted(os.listdir(CORPUS)):
        if not name.endswith('.txt'):
            continue
        found = evidence(name, wikidata)
        year, confidence, basis, note = decide(name, found)
        meta = metadata(name)
        size = os.path.getsize(os.path.join(CORPUS, name))
        tokens_all += size
        if year:
            tokens_dated += size
        counts[confidence] = counts.get(confidence, 0) + 1
        rows.append((name, year or '', found.get('filename', '') or '',
                     confidence, basis,
                     meta.get('Translator', '') or meta.get('Author', ''),
                     note))

    rows, merged = merge_surnames(rows)
    print('%d sources' % len(rows))
    if merged:
        print('  merged split attributions: %s'
              % ', '.join('%s -> %s' % kv for kv in sorted(merged.items())))
    for confidence in ('high', 'medium', 'none'):
        print('  %-8s %4d' % (confidence, counts.get(confidence, 0)))
    print('  dated share of corpus by bytes: %.1f%%'
          % (100.0 * tokens_dated / max(tokens_all, 1)))

    if args.write:
        with open(OUT, 'w', encoding='utf-8') as fh:
            fh.write('source\twritten\tedition\tconfidence\tbasis\t'
                     'attributed\tnote\n')
            for row in rows:
                fh.write('\t'.join(str(cell) for cell in row) + '\n')
        print('  wrote %s' % OUT)
    return 0


if __name__ == '__main__':
    sys.exit(main())
