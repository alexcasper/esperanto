#!/usr/bin/env python3
"""Score archive.org items for Esperanto text quality before fetching them.

Usage: python3 tools/triage_archive_items.py --series NAME [--sample N]
       python3 tools/triage_archive_items.py --items ID [ID ...]
       python3 tools/triage_archive_items.py --survey FILE.json [--per-series N]

bitarkivo.org has uploaded 9514 text items to archive.org across 128 series.
They are already OCR'd — every one of twelve sampled carries a text layer — but
OCR quality varies enormously by series, from 93% recognisable down to text
that has disintegrated into single letters, so a series has to be measured
before it is worth fetching.

The question this answers is "is this valid Esperanto text", not "is it from a
particular period". An earlier pass surveyed only the 1940-1990 window because
of a diachronic experiment; that was the wrong frame for a corpus whose goal is
breadth. --window still exists for asking a narrower question, but the default
is the whole run, and samples are spread across a series rather than taken from
its first issues, because OCR quality tracks the scanning batch and typography
of a period rather than being constant across a run.

TWO WAYS TO GET A WRONG ANSWER, both of which produced wrong numbers here
before this tool existed:

  guessing the filename. `https://archive.org/download/ID/ID_djvu.txt` is the
  usual name and is NOT universal. Where it is wrong archive.org serves an
  HTML error page with HTTP 200, which scores as ~10900 tokens at 34.4%
  recognisable — a plausible-looking bad score rather than an obvious failure.
  Two series were written off on exactly that before the identical scores gave
  it away. The file list in the item metadata is authoritative; use it.

  scoring an empty file. Some items have a text file of a few hundred bytes.
  That scores 44% on 18 tokens, which is noise, not a measurement. Anything
  under MIN_TOKENS is reported as empty rather than scored.

Scoring is tools/score_esperanto_text.py, so the bar is the one the rest of
the project uses: 80% or better recognisable with under 5% single-character
tokens is usable, and the band below that is where a reviewer has to look.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
METADATA = 'https://archive.org/metadata/%s'
DOWNLOAD = 'https://archive.org/download/%s/%s'
AGENT = ('esperanto-corpus/1.0 (corpus triage; '
         'github.com/alexcasper/esperanto)')
MIN_TOKENS = 500
TEXT_FORMATS = ('DjVuTXT', 'Text')
GOOD_KNOWN, MAX_SINGLES = 80.0, 5.0


def curl(url, binary=False):
    args = ['curl', '-sSL', '--max-time', '120', '-A', AGENT, url]
    out = subprocess.run(args, capture_output=True, text=not binary)
    return out.stdout if out.returncode == 0 else None


def text_file(identifier):
    """The item's text file NAME, from its metadata. Never guessed."""
    raw = curl(METADATA % identifier)
    if not raw:
        return None
    try:
        meta = json.loads(raw)
    except ValueError:
        return None
    for wanted in TEXT_FORMATS:
        for entry in meta.get('files', []):
            if entry.get('format') == wanted:
                return entry['name']
    return None


def score(path):
    """(tokens, known%, singles%) via the project's own scorer."""
    out = subprocess.run(
        [sys.executable, os.path.join(ROOT, 'tools',
                                      'score_esperanto_text.py'), path],
        capture_output=True, text=True)
    for line in out.stdout.splitlines()[1:]:
        numbers = re.findall(r'([\d.]+)%?', line)
        if len(numbers) >= 3:
            return int(numbers[-4]), float(numbers[-3]), float(numbers[-2])
    return None


def triage(identifier, keep=None):
    name = text_file(identifier)
    if not name:
        return identifier, 'no text file', None
    body = curl(DOWNLOAD % (identifier, name))
    if not body:
        return identifier, 'download failed', None
    # An HTML error page arrives with HTTP 200. Catch it by shape, not status.
    if body.lstrip()[:200].lower().startswith('<!doctype html'):
        return identifier, 'served an HTML page, not text', None
    target = keep or os.path.join(tempfile.gettempdir(),
                                  'triage-%s.txt' % identifier[:60])
    with open(target, 'w', encoding='utf-8') as fh:
        fh.write(body)
    figures = score(target)
    if not keep:
        os.unlink(target)
    if not figures:
        return identifier, 'unscorable', None
    tokens, known, singles = figures
    if tokens < MIN_TOKENS:
        return identifier, 'empty (%d tokens)' % tokens, figures
    verdict = ('usable' if known >= GOOD_KNOWN and singles < MAX_SINGLES
               else 'marginal' if known >= 65 else 'poor')
    return identifier, verdict, figures


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--items', nargs='*', default=[])
    parser.add_argument('--series')
    parser.add_argument('--survey', help='JSON list of archive.org items')
    parser.add_argument('--sample', type=int, default=3)
    parser.add_argument('--per-series', type=int, default=2)
    parser.add_argument('--window',
                        help='restrict to a year range like 1940-1990; the '
                             'default is every year')
    args = parser.parse_args()

    identifiers = list(args.items)
    if args.survey:
        first, last = (int(x) for x in args.window.split('-')) \
            if args.window else (0, 9999)
        items = json.load(open(args.survey, encoding='utf-8'))
        by_series = {}
        for item in items:
            found = re.search(r'(?<!\d)(18[89]\d|19\d\d|20[0-2]\d)(?!\d)',
                              item['identifier'])
            year = int(found.group(1)) if found else None
            if args.window and (year is None or not first <= year <= last):
                continue
            key = re.split(r'[_-](?=\d{4}(?!\d))', item['identifier'])[0]
            if args.series and key != args.series:
                continue
            by_series.setdefault(key, []).append(item['identifier'])
        for key in sorted(by_series, key=lambda k: -len(by_series[k])):
            run = sorted(by_series[key])
            # Spread the samples across the run. OCR quality follows the
            # scanning batch and the typography of a period, so the first three
            # issues of a forty-year run measure one year of it, not the run.
            if len(run) <= args.per_series:
                picks = run
            else:
                step = (len(run) - 1) / float(args.per_series - 1) \
                    if args.per_series > 1 else 0
                picks = [run[int(round(i * step))]
                         for i in range(args.per_series)]
            print('\n== %s (%d items%s)'
                  % (key, len(run),
                     ' in ' + args.window if args.window else ''))
            for identifier in picks:
                _i, verdict, figures = triage(identifier)
                print('   %-46s %-12s %s'
                      % (identifier[:46], verdict,
                         '' if not figures
                         else '%d tokens %.1f%% known %.1f%% singles' % figures))
        return 0

    for identifier in identifiers:
        _i, verdict, figures = triage(identifier)
        print('%-46s %-12s %s'
              % (identifier[:46], verdict,
                 '' if not figures
                 else '%d tokens %.1f%% known %.1f%% singles' % figures))
    return 0


if __name__ == '__main__':
    sys.exit(main())
