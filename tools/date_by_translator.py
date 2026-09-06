#!/usr/bin/env python3
"""Identify the translators named in RAW/ headers and find their lifespans.

Usage: python3 tools/date_by_translator.py [--write] [--refresh] [--name NAME]

Writes RAW/TRANSLATORS.tsv, which tools/date_sources.py reads as the
`translator` evidence kind. --dry-run is the default: without --write nothing
is written and the table is printed.

Why this exists. 68 of the 169 undated sources name a `Translator:` and are
undated for a reason that is correct and must stay correct: a translation's
in-text year dates the ORIGINAL work, not the Esperanto. Odd Tangerud's Ibsen
translations carry 1888-1896 on their title pages and were made in the 1990s,
and before date_sources.py refused in-text years under a named translator he
was 43% of the '1890s'. So the years are there; what is missing is a way to
tell which of them could be the Esperanto.

A lifespan is that way, and it is the only thing Wikidata reliably has. An
earlier probe of ten well-known Esperanto works matched one Wikidata item and
that match was wrong (a Polish film); the same query against the PEOPLE who
made them resolves most of them with a birth and a death year attached. So we
query people.

WHAT A LIFESPAN LICENCES, AND WHAT IT DOES NOT

A lifespan is a range and a publication date is a year, and the gap between
them is not something to paper over with a midpoint. Grobe lived 1927-2015;
recording 1971 for his ten translations would be wrong by twenty-seven years
in every case and would put nine texts into a decade this corpus otherwise has
nothing in, which is exactly the shape of a manufactured finding. This tool
therefore never emits a year on a lifespan alone. It emits a WINDOW:

    [max(1887, birth + MIN_AGE), min(death + POSTHUMOUS, this year)]

1887 because Esperanto did not exist before it. MIN_AGE is 16: the youngest
documented translator in this corpus is Eugen Wüster, whose preface to `La
Kantistino` is signed Vienna, 1 January 1917, when he was 18, and 16 leaves
room without admitting infancy. POSTHUMOUS is 3: translations do appear after
their translator dies, but a wide grace here would re-admit exactly the
original-work years the window exists to exclude.

date_sources.py then uses the window to filter, not to date: an in-text year
is re-admitted only if it falls inside it. That is a conjunction of two
independent facts — the year is printed in the book, and the translator was
alive and adult when it was printed — and neither alone would do. Tangerud's
1888 is outside his window and stays inadmissible; Zamenhof's 1908 on
`Ifigenio en Taurido` is inside his and dates the Hachette edition correctly.

VERIFICATION, because a namesake is worse than a blank

Every match is required to be a human (P31=Q5) whose life overlaps the
Esperanto era, AND to carry at least one positive Esperanto signal:

  eo-sitelink   the item has an eo.wikipedia article. Esperanto Wikipedia
                writes about Esperantists; a random American namesake does not
                get an article there.
  P1412=Q143    'languages spoken, written or signed' includes Esperanto.
  description   the English description says Esperantist/Esperanto.

Anything failing all three is recorded with verdict `unverified` and carries
no window, so it dates nothing. That is the intended outcome for a common
name: `A. Muller` and `Alexander Pride` are not identifiable and must not be
guessed at. The verdict column is in the output so the rejections stay
visible rather than silently vanishing.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, 'RAW')
OUT = os.path.join(RAW, 'TRANSLATORS.tsv')
CACHE = os.path.join(RAW, '.cache-wikidata')

API = 'https://www.wikidata.org/w/api.php'
UA = ('esperanto-corpus-pipeline/1.0 '
      '(https://github.com/; dating translators from Wikidata lifespans)')

HUMAN = 'Q5'
ESPERANTO = 'Q143'
FIRST_YEAR, THIS_YEAR = 1887, 2026
MIN_AGE = 16          # see docstring: Wüster was 18
POSTHUMOUS = 3

TRANSLATOR = re.compile(r'^Translator:\s*(.+)$', re.M)
DESC_ESP = re.compile(r'esperant', re.I)


def fetch(params, tag, refresh=False):
    """One cached GET against the Wikidata API.

    urllib dies about twelve seconds in through this environment's proxy, so
    this shells out to curl. Every response is cached by tag: a re-run costs
    nothing and the reviewer can read what the API actually said.
    """
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, re.sub(r'[^\w.-]', '_', tag) + '.json')
    if os.path.exists(path) and not refresh:
        with open(path, encoding='utf-8') as fh:
            return json.load(fh)
    query = '&'.join('%s=%s' % (k, quote(v)) for k, v in params.items())
    for attempt in range(6):
        proc = subprocess.run(
            ['curl', '-sS', '--max-time', '30', '-H', 'User-Agent: ' + UA,
             API + '?' + query],
            capture_output=True, text=True)
        try:
            data = json.loads(proc.stdout)
        except ValueError:
            time.sleep(10 * (attempt + 1))      # rate limit or proxy hiccup
            continue
        with open(path, 'w', encoding='utf-8') as fh:
            json.dump(data, fh, ensure_ascii=False)
        time.sleep(1.5)
        return data
    raise SystemExit('wikidata fetch failed for %s: %s'
                     % (tag, proc.stdout[:200]))


def quote(text):
    from urllib.parse import quote as q
    return q(str(text), safe='')


def search(name, refresh=False):
    data = fetch({'action': 'wbsearchentities', 'search': name,
                  'language': 'en', 'uselang': 'en', 'format': 'json',
                  'limit': '10', 'type': 'item'},
                 'search-' + name, refresh)
    return [hit['id'] for hit in data.get('search', [])]


def entities(qids, refresh=False):
    out = {}
    for i in range(0, len(qids), 20):
        batch = qids[i:i + 20]
        data = fetch({'action': 'wbgetentities', 'ids': '|'.join(batch),
                      'props': 'claims|labels|descriptions|sitelinks',
                      'languages': 'en', 'format': 'json'},
                     'ent-' + '_'.join(batch), refresh)
        out.update(data.get('entities', {}))
    return out


def claim_ids(entity, prop):
    out = []
    for claim in entity.get('claims', {}).get(prop, []):
        value = claim.get('mainsnak', {}).get('datavalue', {}).get('value')
        if isinstance(value, dict) and 'id' in value:
            out.append(value['id'])
    return out


def claim_year(entity, prop):
    for claim in entity.get('claims', {}).get(prop, []):
        value = claim.get('mainsnak', {}).get('datavalue', {}).get('value')
        if isinstance(value, dict) and 'time' in value:
            match = re.match(r'[+-](\d{4})', value['time'])
            if match:
                return int(match.group(1))
    return None


def assess(name, entity):
    """(verdict, reason) for one candidate item."""
    if HUMAN not in claim_ids(entity, 'P31'):
        return 'not-human', ''
    label = entity.get('labels', {}).get('en', {}).get('value', '')
    desc = entity.get('descriptions', {}).get('en', {}).get('value', '')
    signals = []
    if 'eowiki' in entity.get('sitelinks', {}):
        signals.append('eo-sitelink')
    if ESPERANTO in claim_ids(entity, 'P1412'):
        signals.append('P1412=Q143')
    if DESC_ESP.search(desc):
        signals.append('description')
    if not signals:
        return 'unverified', 'no Esperanto signal; desc=%r' % desc
    birth = claim_year(entity, 'P569')
    death = claim_year(entity, 'P570')
    if birth is None and death is None:
        return 'no-dates', '+'.join(signals)
    if death is not None and death < FIRST_YEAR:
        return 'pre-esperanto', 'died %d' % death
    return 'verified', '+'.join(signals)


def window(birth, death):
    lo = FIRST_YEAR if birth is None else max(FIRST_YEAR, birth + MIN_AGE)
    hi = THIS_YEAR if death is None else min(THIS_YEAR, death + POSTHUMOUS)
    return lo, hi


def head(path, lines=40):
    try:
        with open(path, encoding='utf-8') as fh:
            return ''.join(fh.readlines()[:lines])
    except OSError:
        return ''


def translators():
    """{name: [source, ...]} over every RAW/ file naming a Translator."""
    found = {}
    for name in sorted(os.listdir(RAW)):
        if not name.endswith('.txt'):
            continue
        match = TRANSLATOR.search(head(os.path.join(RAW, name)))
        if match:
            found.setdefault(match.group(1).strip(), []).append(name)
    return found


def resolve(name, refresh=False):
    """Best verified Wikidata person for this translator name, or None."""
    qids = search(name, refresh)
    if not qids:
        return None, 'no-match', 'wbsearchentities found nothing'
    items = entities(qids, refresh)
    rejected = []
    for qid in qids:                            # search order is relevance
        entity = items.get(qid)
        if not entity or 'missing' in entity:
            continue
        verdict, reason = assess(name, entity)
        if verdict == 'verified':
            return entity, verdict, reason
        rejected.append('%s:%s' % (qid, verdict))
    return None, 'unverified', ' '.join(rejected[:5])


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--write', action='store_true',
                        help='write RAW/TRANSLATORS.tsv (default: dry run)')
    parser.add_argument('--dry-run', action='store_true',
                        help='the default; accepted so it can be said aloud')
    parser.add_argument('--refresh', action='store_true',
                        help='ignore the response cache')
    parser.add_argument('--name', action='append',
                        help='restrict to these translator names')
    args = parser.parse_args()
    if args.dry_run:
        args.write = False

    people = translators()
    if args.name:
        people = {k: v for k, v in people.items() if k in args.name}

    rows = []
    for name in sorted(people, key=lambda n: (-len(people[n]), n)):
        entity, verdict, reason = resolve(name, args.refresh)
        qid = label = desc = ''
        birth = death = None
        if entity is not None:
            qid = entity['id']
            label = entity.get('labels', {}).get('en', {}).get('value', '')
            desc = entity.get('descriptions', {}).get('en', {}).get('value', '')
            birth = claim_year(entity, 'P569')
            death = claim_year(entity, 'P570')
        lo, hi = window(birth, death) if verdict == 'verified' else ('', '')
        rows.append((name, len(people[name]), qid, label, desc,
                     birth or '', death or '', lo, hi, verdict, reason))

    verified = [r for r in rows if r[9] == 'verified']
    print('%d translator names over %d sources'
          % (len(rows), sum(r[1] for r in rows)))
    print('  verified %d names over %d sources'
          % (len(verified), sum(r[1] for r in verified)))
    print()
    print('%-26s %4s %-11s %-9s %-11s %s'
          % ('translator', 'srcs', 'qid', 'life', 'window', 'verdict'))
    for row in rows:
        print('%-26s %4d %-11s %-9s %-11s %s'
              % (row[0][:26], row[1], row[2],
                 '%s-%s' % (row[5], row[6]),
                 '%s-%s' % (row[7], row[8]), row[9]))

    if args.write:
        with open(OUT, 'w', encoding='utf-8') as fh:
            fh.write('translator\tsources\tqid\tlabel\tdescription\tborn\t'
                     'died\twindow_from\twindow_to\tverdict\tevidence\n')
            for row in rows:
                fh.write('\t'.join(str(cell) for cell in row) + '\n')
        print('\nwrote %s' % OUT)
    else:
        print('\n(dry run: pass --write to update %s)' % OUT)
    return 0


if __name__ == '__main__':
    sys.exit(main())
