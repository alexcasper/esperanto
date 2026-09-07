#!/usr/bin/env python3
"""Harvest the bitarkivo.org periodical catalogue into RAW/PERIODICALS.tsv.

Usage: python3 tools/fetch_bitarkivo_catalogue.py [--write] [--cache FILE]

bitarkivo.org is the Esperanto digital archive behind most of the Esperanto
periodical scans on archive.org — the uploader on those items is
`kontakto@bitarkivo.org`. Its /gazetoj/ index lists 926 periodicals with the
country and the years each one ran, and each periodical's own page carries the
archive.org identifiers of its digitised issues plus an editorial history.

Two things this buys, neither of which archive.org's own search gives:

  identity   archive.org search returns loose items. It cannot tell you that
             416 of them are one periodical. That distinction is the same one
             that mattered for the 26 issues of `The Esperantist`, which were
             26 anonymous sources until they were recognised as one magazine —
             and treating them as 26 independent hands quietly defeated the
             author hold-out in the diachronic study. A source list without
             periodical identity will make that mistake again at scale.

  ceiling    The catalogue records what was PUBLISHED; archive.org records
             what has been SCANNED. The gap between them is the honest limit
             on what any corpus can hold, and it is large in exactly the
             period this project is short of. 391 periodicals ran at some
             point between 1940 and 1990, 6129 periodical-years in all, and
             the scans are nowhere near that: `Esperanto (UEA)` is catalogued
             1905-1995 with 616 identifiers, of which 16 fall in the window;
             `La Ondo de Esperanto` and `Katolika Sento` are catalogued across
             the whole period with no identifiers at all. Digitisation is
             concentrated before 1940 and after 2000, which is the copyright
             shadow seen from the archive's side rather than ours.

So the 1940-1990 gap is not only this project's gap. It is a gap in what has
been digitised, and no amount of searching will close the part of it that
nobody has scanned.
"""
import argparse
import html
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'RAW', 'PERIODICALS.tsv')
INDEX = 'https://bitarkivo.org/gazetoj/'
AGENT = ('esperanto-corpus/1.0 (building a research corpus; '
         'github.com/alexcasper/esperanto)')

# Two details that cost 200 of the 926 rows on the first attempt, both found
# by counting the links on the page against the rows parsed out of it:
# a row may carry a class (`<tr class="gazetoj-tabelo-vico--kompleta">` marks a
# periodical whose run is completely digitised, which is the most useful subset
# of all), so the split has to be on `<tr` and not `<tr>`; and either year cell
# may be EMPTY, so requiring four digits silently drops every periodical whose
# end year is unrecorded — `Afrika Esperantisto` among them.
#
# A third variant cost another 18, `Esperanto (UEA)` among them: the end year
# may read `Nuntempe`, meaning the periodical is still running. Accepting only
# digits-or-empty dropped exactly the periodicals that are alive today, which
# are the ones most likely to have a long digitised run. Each of these three
# was found by counting the slugs linked on the page against the rows parsed
# out of it, not by reading the markup — the count is the test worth keeping.
ROW = re.compile(
    r'<a href="/gazetoj/([a-z0-9_-]+)/">([^<]+)</a>'
    r'.*?data-label="Jaro komenco">([^<]*)</td>'
    r'.*?data-label="Jaro fino">([^<]*)</td>', re.S)
ONGOING = 'Nuntempe'
COUNTRY = re.compile(r'lando=([A-Z]{2})">([^<]+)</a>')
COMPLETE = 'gazetoj-tabelo-vico--kompleta'


def fetch(url, cache=None):
    """curl, because urllib stalls through this environment's proxy."""
    if cache and os.path.exists(cache):
        return open(cache, encoding='utf-8').read()
    out = subprocess.run(
        ['curl', '-sSL', '--max-time', '120', '-A', AGENT, url],
        capture_output=True, text=True)
    if out.returncode:
        sys.exit('fetch failed: %s' % out.stderr.strip()[:200])
    if cache:
        open(cache, 'w', encoding='utf-8').write(out.stdout)
    return out.stdout


def parse(page):
    """(slug, name, country, first, last, complete) per periodical.

    first/last are '' where the catalogue does not record them. complete is
    whether bitarkivo marks the run as fully digitised.
    """
    rows = []
    for block in page.split('<tr'):
        match = ROW.search(block)
        if not match:
            continue
        slug, name, first, last = match.groups()
        country = COUNTRY.search(block)
        rows.append((slug, html.unescape(name).strip(),
                     country.group(2).strip() if country else '',
                     first.strip(), last.strip(),
                     'yes' if COMPLETE in block else 'no'))
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--write', action='store_true')
    parser.add_argument('--cache', help='reuse a saved copy of the index page')
    args = parser.parse_args()

    rows = parse(fetch(INDEX, args.cache))
    if not rows:
        sys.exit('parsed nothing — the page markup has probably changed')
    rows.sort()

    def last_year(row, now=2026):
        return now if row[4] == ONGOING else (int(row[4]) if row[4] else None)

    dated = [r for r in rows if r[3].isdigit() and last_year(r)]
    window = [r for r in dated
              if int(r[3]) <= 1990 and last_year(r) >= 1940]
    years = sum(max(0, min(last_year(r), 1990) - max(int(r[3]), 1940) + 1)
                for r in window)
    print('%d periodicals catalogued, %d with usable years, from %s'
          % (len(rows), len(dated), min(int(r[3]) for r in dated)))
    print('%d still running (Nuntempe)'
          % sum(1 for r in rows if r[4] == ONGOING))
    print('%d marked completely digitised' % sum(1 for r in rows if r[5] == 'yes'))
    print('%d ran at some point in 1940-1990, %d periodical-years in the window'
          % (len(window), years))
    print('  — but see the docstring: catalogued is not scanned.')

    if not args.write:
        print('\n--dry-run by default. Re-run with --write.')
        return 0
    with open(OUT, 'w', encoding='utf-8') as fh:
        fh.write('slug\tname\tcountry\tfirst\tlast\tcomplete\n')
        for row in rows:
            fh.write('%s\t%s\t%s\t%s\t%s\t%s\n' % row)
    print('wrote %s' % OUT)
    return 0


if __name__ == '__main__':
    sys.exit(main())
