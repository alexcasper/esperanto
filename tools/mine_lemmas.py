#!/usr/bin/env python3
"""Map step of lemma mining: extract candidate lemmas from one shard of CORPUS/.

Usage:
  python3 tools/mine_lemmas.py --shard I/N [--min-count 2] [--max-citations 3]
  python3 tools/mine_lemmas.py --plan N          # show the shard assignment

Each shard writes exactly one file, DICT/shards/shard-<I>-of-<N>.jsonl, and
reads only the CORPUS/ files assigned to it. Nothing is shared between shards,
so shards can run concurrently — in separate agents, processes or machines —
without coordination. tools/reconcile_lemmas.py performs the reduce.

Shards are packed by file size, largest first into the lightest shard, because
the corpus is lopsided: Originala Verkaro is 1.4 MB and the smallest sources
are a few kilobytes, so round-robin would leave one shard doing most of the
work.

Output records are one JSON object per line:

  {"lemma": "...", "kind": "unknown", "count": 12, "pos_guess": "noun",
   "forms": {"vorto": 9, "vortoj": 3},
   "citations": [{"source": "pg-8224.txt", "line": 412, "text": "..."}],
   "verdict": null, "gloss": null, "note": null}

`verdict`, `gloss` and `note` are left null by this script. They are the
judgment a reviewer adds: whether a candidate is a real Esperanto lemma, an
OCR artefact, a proper noun or a foreign word — the part that needs a reader
rather than a regular expression.
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import esperanto  # noqa: E402  (path set above)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORPUS = os.path.join(ROOT, 'CORPUS')
SHARDS = os.path.join(ROOT, 'DICT', 'shards')
LEDGER = os.path.join(ROOT, 'DICT', 'verdicts.jsonl')

# 'grammar' sources are English prose about Esperanto; mining them for Esperanto
# lemmas yields English. PROVENANCE.md marks them; match them by id here.
ENGLISH_HEAVY = {'pg-7787.txt', 'pg-8177.txt', 'pg-16967.txt'}

# The Fundamento's multilingual tables put French, German, Russian and Polish
# gloss columns beside the Esperanto, so mining them yields those languages.
MULTILINGUAL = {'wsrc-Fundamento_de_Esperanto_Universala_vortaro.txt',
                'wsrc-Fundamento_de_Esperanto_Grammar.txt'}

# Not words: the elided article, Roman numerals, and the abbreviations that
# recur across sources (Kabe's subject labels, citation shorthand). Every
# reviewer hit these, and 'l' alone reached 2884 occurrences.
STOPWORDS = {'l', 'ktp', 'ekz', 'prof', 'kop', 'esp', 'fr', 'np', 'ex',
             'zool', 'ĥem', 'med', 'geom', 'fiz', 'bot', 'anat', 'mat',
             'haml', 'kos', 'no', 'nro', 'vol', 'pĝ', 'red'}
ROMAN = re.compile(r'^[ivxlcdm]+$')


def is_fragment(line, match):
    """True if the token is a piece of a longer word, not a word itself.

    The tokenizer only accepts Esperanto letters, so a foreign name breaks into
    pieces at the first letter outside the alphabet: Volapük yields 'volap',
    and the abbreviation d-ro yields 'ro'. Both then look like frequent unknown
    lemmas. Checking the characters either side of the match catches them.
    """
    before = line[match.start() - 1] if match.start() else ''
    after = line[match.end()] if match.end() < len(line) else ''
    for neighbour in (before, after):
        if neighbour and (neighbour.isalpha() or neighbour == '-'):
            if neighbour not in esperanto.ESPERANTO_LETTERS:
                return True
            if neighbour == '-':
                return True
    return False


def corpus_files():
    skip = ENGLISH_HEAVY | MULTILINGUAL
    return sorted(f for f in os.listdir(CORPUS)
                  if f.endswith('.txt') and f not in skip)


def plan_shards(count):
    """Greedy longest-first packing, so every shard gets similar total bytes."""
    files = [(os.path.getsize(os.path.join(CORPUS, f)), f)
             for f in corpus_files()]
    files.sort(reverse=True)
    shards = [[] for _ in range(count)]
    weights = [0] * count
    for size, name in files:
        lightest = weights.index(min(weights))
        shards[lightest].append(name)
        weights[lightest] += size
    return shards, weights


def mine(files, roots, words, min_count, max_citations):
    lemmas = {}
    for name in files:
        path = os.path.join(CORPUS, name)
        with open(path, encoding='utf-8') as fh:
            for lineno, line in enumerate(fh, 1):
                for match in esperanto.TOKEN.finditer(line):
                    token = match.group()
                    if len(token) < 2:
                        continue
                    lemma, kind = esperanto.analyse(token, roots, words)
                    if lemma is None or kind in ('grammatical', 'correlative'):
                        continue
                    low = token.lower()
                    if low in STOPWORDS or ROMAN.match(low):
                        continue
                    if kind == 'unknown':
                        # Capitalised tokens keep their surface form: stripping
                        # a final -n as if it were the accusative turned
                        # Hutton into 'hutto' and London into 'londo', which
                        # four reviewers reported independently.
                        if token[:1].isupper():
                            lemma = low
                        else:
                            # Otherwise unknown words split across their
                            # inflections, filing kongreso/kongresoj/kongreson
                            # as three separate discoveries.
                            lemma = esperanto.citation_form(token)
                        if is_fragment(line, match):
                            kind = 'fragment'
                    record = lemmas.setdefault(lemma, {
                        'lemma': lemma, 'kind': kind, 'count': 0,
                        'pos_guess': esperanto.guess_pos(token),
                        'forms': {}, 'citations': [],
                        'caps': 0, 'lower': 0,
                        'verdict': None, 'gloss': None, 'note': None,
                    })
                    record['count'] += 1
                    record['forms'][low] = record['forms'].get(low, 0) + 1
                    if token[:1].isupper():
                        record['caps'] += 1
                    else:
                        record['lower'] += 1
                    if len(record['citations']) < max_citations:
                        snippet = ' '.join(line.split())
                        if len(snippet) > 160:
                            cut = snippet.find(token)
                            start = max(0, cut - 70)
                            snippet = ('…' if start else '') + \
                                snippet[start:start + 150] + '…'
                        record['citations'].append({
                            'source': name, 'line': lineno, 'text': snippet})
    kept = {}
    for lemma, record in lemmas.items():
        if record['count'] < min_count:
            continue
        if record['kind'] == 'unknown' and record['lower'] == 0:
            record['kind'] = 'name'
        kept[lemma] = record
    return kept


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--shard', help='I/N, e.g. 3/8')
    parser.add_argument('--plan', type=int, help='print the shard assignment')
    parser.add_argument('--min-count', type=int, default=2)
    parser.add_argument('--max-citations', type=int, default=3)
    parser.add_argument('--ledger', nargs='?', const=LEDGER, default=None,
                        help='re-apply verdicts from a ledger after mining, so '
                             'the map can be re-run without discarding review '
                             'work held in the shard files')
    args = parser.parse_args()

    if args.plan:
        shards, weights = plan_shards(args.plan)
        for i, (files, weight) in enumerate(zip(shards, weights), 1):
            print('shard %d/%d: %2d files, %7.1f KB  (%s%s)'
                  % (i, args.plan, len(files), weight / 1024, files[0][:38],
                     ', …' if len(files) > 1 else ''))
        return 0

    if not args.shard or '/' not in args.shard:
        parser.error('--shard I/N is required (or use --plan N)')
    index, count = (int(part) for part in args.shard.split('/'))
    if not 1 <= index <= count:
        parser.error('shard index %d out of range 1..%d' % (index, count))

    shards, _ = plan_shards(count)
    files = shards[index - 1]
    roots, words = esperanto.load_vocabulary()
    lemmas = mine(files, roots, words, args.min_count, args.max_citations)

    restored = 0
    if args.ledger and os.path.exists(args.ledger):
        with open(args.ledger, encoding='utf-8') as fh:
            for line in fh:
                if not line.strip():
                    continue
                decided = json.loads(line)
                record = lemmas.get(decided['lemma'])
                if record:
                    record['verdict'] = decided.get('verdict')
                    record['gloss'] = decided.get('gloss')
                    record['note'] = decided.get('note')
                    restored += 1

    os.makedirs(SHARDS, exist_ok=True)
    out = os.path.join(SHARDS, 'shard-%d-of-%d.jsonl' % (index, count))
    ordered = sorted(lemmas.values(),
                     key=lambda r: ({'unknown': 0, 'name': 1, 'fragment': 2,
                                     'known': 3}.get(r['kind'], 4),
                                    -r['count']))
    with open(out, 'w', encoding='utf-8') as fh:
        for record in ordered:
            fh.write(json.dumps(record, ensure_ascii=False) + '\n')

    unknown = sum(1 for r in ordered if r['kind'] == 'unknown')
    print('shard %d/%d: %d files → %s' % (index, count, len(files), out))
    print('  %d lemmas (%d unknown, %d built on known roots)'
          % (len(ordered), unknown, len(ordered) - unknown))
    if args.ledger:
        print('  %d verdicts restored from %s'
              % (restored, os.path.basename(args.ledger)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
