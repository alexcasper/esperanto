#!/usr/bin/env python3
"""Fetch archive.org periodical issues into RAW/, deciding issue by issue.

Usage: python3 tools/fetch_archive_periodical.py --series NAME [--apply]
                                                 [--items FILE] [--limit N]
                                                 [--include-marginal]

bitarkivo.org has 9514 Esperanto text items on archive.org across 128 series.
`tools/triage_archive_items.py` measures a series; this fetches one.

THE DECISION IS PER ISSUE, NOT PER SERIES, and that is the whole design. OCR
quality tracks the era of the scan rather than the periodical: britaesperantisto
reads 53.9% recognisable in 1905, 44.9% in 1925 and 91.4% in 2017. Accepting or
rejecting a run wholesale would throw away the clean half of most of them. So
every issue is downloaded, scored, and kept or refused on its own numbers,
which is also why a series bead's survey figures say where to look first and
nothing more.

The bar is the project's: 80% or better recognisable with under 5%
single-character tokens. `--include-marginal` lowers it to 70% and marks those
rows, for a run where the marginal issues are the only ones there are.

Three things that are not obvious and each of which produced a wrong result
before it was handled:

  the text filename is not derivable. `ID_djvu.txt` is usual and not
  universal, and where it is wrong archive.org serves an HTML error page with
  HTTP 200 that scores about 34% recognisable over 10900 tokens — a plausible
  bad score rather than a visible failure. Read the file list from the item
  metadata.

  a near-empty text file scores like bad OCR. One scored 44% on 18 tokens.
  Under MIN_TOKENS an issue is refused as empty rather than scored.

  an issue is not a source. A periodical run is one editorial line; Sennaciulo
  is 462 identifiers and Esperanto-UEA 517. Counting issues as independent
  authors is the mistake that made 26 issues of `The Esperantist` look like 26
  hands and defeated the author hold-out in ANALYSIS/diachronic.md. Every
  accepted issue is written to RAW/PERIODICAL_ISSUES.tsv against its
  periodical, so anything downstream can pool them.

Licence follows the policy in CLAUDE.md: an item is usable unless it states a
restriction, and PROVENANCE.md records what was observed rather than a licence
we inferred. Items carrying `access-restricted-item`, or a `rights` or
`possible-copyright-status` field, are skipped and reported.
"""
import argparse
import csv
import datetime
import hashlib
import json
import os
import re
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, 'RAW')
PROVENANCE = os.path.join(RAW, 'PROVENANCE.md')
QUALITY = os.path.join(RAW, 'QUALITY.tsv')
ISSUES = os.path.join(RAW, 'PERIODICAL_ISSUES.tsv')
PERIODICALS = os.path.join(RAW, 'PERIODICALS.tsv')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import triage_archive_items as triage                     # noqa: E402

AGENT = ('esperanto-corpus/1.0 (building a research corpus; '
         'github.com/alexcasper/esperanto)')
DELAY = 0.5                # archive.org is free infrastructure; do not hammer
MIN_TOKENS = triage.MIN_TOKENS
GOOD, MARGINAL, MAX_SINGLES = 80.0, 70.0, 5.0
RESTRICTION_FIELDS = ('access-restricted-item', 'rights',
                      'possible-copyright-status')


def curl(url):
    out = subprocess.run(['curl', '-sSL', '--max-time', '180', '-A', AGENT,
                          url], capture_output=True, text=True)
    return out.stdout if out.returncode == 0 else None


def metadata(identifier):
    raw = curl('https://archive.org/metadata/%s' % identifier)
    if not raw:
        return None
    try:
        return json.loads(raw)
    except ValueError:
        return None


def restriction(meta):
    """A stated restriction, or None. Absence is not permission, but the
    project's policy is to proceed absent a statement and record what we saw."""
    fields = meta.get('metadata', {})
    for key in RESTRICTION_FIELDS:
        if fields.get(key):
            return '%s=%s' % (key, str(fields[key])[:60])
    return None


def periodical_index():
    """slug -> display name, for attributing an issue to its run."""
    out = {}
    if os.path.exists(PERIODICALS):
        with open(PERIODICALS, encoding='utf-8') as fh:
            for row in csv.DictReader(fh, delimiter='\t'):
                out[row['slug'].lower()] = row['name']
    return out


def series_of(identifier):
    return re.split(r'[_-](?=\d{4}(?!\d))', identifier)[0]


def year_of(identifier):
    found = re.search(r'(?<!\d)(18[89]\d|19\d\d|20[0-2]\d)(?!\d)', identifier)
    return found.group(1) if found else ''


def already_have():
    return {name[3:-4] for name in os.listdir(RAW)
            if name.startswith('ia-') and name.endswith('.txt')}


def consider(identifier, include_marginal):
    """(verdict, reason, text, figures) for one issue."""
    meta = metadata(identifier)
    if not meta:
        return 'error', 'metadata unavailable', None, None
    stated = restriction(meta)
    if stated:
        return 'restricted', stated, None, None
    name = None
    for wanted in triage.TEXT_FORMATS:
        for entry in meta.get('files', []):
            if entry.get('format') == wanted:
                name = entry['name']
                break
        if name:
            break
    if not name:
        return 'no-text', 'no text file in the item', None, None
    body = curl('https://archive.org/download/%s/%s' % (identifier, name))
    if not body:
        return 'error', 'download failed', None, None
    if body.lstrip()[:200].lower().startswith('<!doctype html'):
        return 'error', 'served an HTML page instead of text', None, None
    scratch = os.path.join(RAW, '.probe-%s.txt' % identifier[:60])
    with open(scratch, 'w', encoding='utf-8') as fh:
        fh.write(body)
    figures = triage.score(scratch)
    os.unlink(scratch)
    if not figures:
        return 'error', 'unscorable', None, None
    tokens, known, singles = figures
    if tokens < MIN_TOKENS:
        return 'empty', '%d tokens' % tokens, None, figures
    if known >= GOOD and singles < MAX_SINGLES:
        return 'accept', 'good', body, figures
    if include_marginal and known >= MARGINAL:
        return 'accept-marginal', 'marginal', body, figures
    return 'reject', '%.1f%% known, %.1f%% singles' % (known, singles), \
        None, figures


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--series', required=True)
    parser.add_argument('--items', help='JSON list of archive.org items')
    parser.add_argument('--limit', type=int)
    parser.add_argument('--include-marginal', action='store_true')
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()

    default = os.path.join(ROOT, 'RAW', '.bitarkivo-items.json')
    source = args.items or default
    if not os.path.exists(source):
        sys.exit('need an item list: pass --items FILE (a JSON list of '
                 '{"identifier": ...} from the archive.org scrape API)')
    items = json.load(open(source, encoding='utf-8'))
    run = sorted(x['identifier'] for x in items
                 if series_of(x['identifier']) == args.series)
    if not run:
        sys.exit('no items for series %r' % args.series)
    have = already_have()
    fresh = [i for i in run if i not in have]
    todo = fresh[:args.limit] if args.limit else fresh
    names = periodical_index()
    display = names.get(args.series.lower(), args.series)
    print('%s (%s): %d issues in the run, %d already in RAW/, %d to consider%s\n'
          % (args.series, display, len(run), len(run) - len(fresh), len(todo),
             ' (--limit %d of %d new)' % (args.limit, len(fresh))
             if args.limit and len(fresh) > args.limit else ''))

    accepted, tally, rows = [], {}, []
    for index, identifier in enumerate(todo, 1):
        verdict, reason, body, figures = consider(identifier,
                                                  args.include_marginal)
        tally[verdict] = tally.get(verdict, 0) + 1
        note = '' if not figures else '%d tok %.1f%% known %.1f%% singles' % figures
        print('  %3d/%-3d %-46s %-16s %s %s'
              % (index, len(todo), identifier[:46], verdict, note, reason
                 if verdict not in ('accept', 'accept-marginal') else ''))
        if body:
            accepted.append((identifier, body, figures, verdict))
        time.sleep(DELAY)

    print('\n%s' % '  '.join('%s=%d' % kv for kv in sorted(tally.items())))
    print('%d of %d issues accepted' % (len(accepted), len(todo)))
    if not args.apply:
        print('\n--dry-run by default. Re-run with --apply to write.')
        return 0
    if not accepted:
        return 0

    today = datetime.date.today().isoformat()
    lines, quality = [], []
    for identifier, body, figures, verdict in accepted:
        target = os.path.join(RAW, 'ia-%s.txt' % identifier)
        with open(target, 'w', encoding='utf-8') as fh:
            fh.write(body)
        digest = hashlib.sha256(body.encode('utf-8')).hexdigest()[:12]
        lines.append(
            '- `ia-%s.txt` — %s%s — sha256:%s — Internet Archive, uploaded by '
            'kontakto@bitarkivo.org (no restriction stated; retrieved %s)%s — '
            'https://archive.org/details/%s'
            % (identifier, display,
               ', ' + year_of(identifier) if year_of(identifier) else '',
               digest, today,
               ' — accepted as marginal' if verdict == 'accept-marginal' else '',
               identifier))
        quality.append('ia-%s.txt\t%d\t%.1f\t%.1f'
                       % (identifier, figures[0], figures[1], figures[2]))
        rows.append('ia-%s.txt\t%s\t%s\t%s\t%s'
                    % (identifier, identifier, args.series, display,
                       year_of(identifier)))

    with open(PROVENANCE, 'a', encoding='utf-8') as fh:
        fh.write('\n### %s — %s, %d issues, retrieved %s\n\n'
                 % (display, args.series, len(accepted), today))
        fh.write('Fetched by `tools/fetch_archive_periodical.py`, one file per '
                 'issue, each scored and kept on its own numbers. No item '
                 'stated a restriction; see CLAUDE.md for the sourcing policy.'
                 '\n\n')
        fh.write('\n'.join(lines) + '\n')
    with open(QUALITY, 'a', encoding='utf-8') as fh:
        fh.write('\n'.join(quality) + '\n')
    new = not os.path.exists(ISSUES)
    with open(ISSUES, 'a', encoding='utf-8') as fh:
        if new:
            fh.write('source\tarchive_id\tseries\tperiodical\tyear\n')
        fh.write('\n'.join(rows) + '\n')
    print('\nwrote %d files to RAW/, and appended to PROVENANCE.md, '
          'QUALITY.tsv and PERIODICAL_ISSUES.tsv' % len(accepted))
    print('run tools/normalize_corpus.py next to bring them into CORPUS/')
    return 0


if __name__ == '__main__':
    sys.exit(main())
