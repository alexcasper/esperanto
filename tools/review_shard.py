#!/usr/bin/env python3
"""Review interface for one lemma shard: list candidates, apply verdicts.

Usage:
  python3 tools/review_shard.py --shard I/N --list [--top 100] [--kind unknown]
  python3 tools/review_shard.py --shard I/N --apply verdicts.json
  python3 tools/review_shard.py --shard I/N --status

A shard file is several megabytes of JSONL — too large to read or hand-edit.
This exposes the only two operations a reviewer needs, and touches exactly one
file, so reviewers working on different shards cannot collide.

--apply takes {"lemma": {"verdict": ..., "gloss": ..., "note": ...}, ...} and
rewrites only those fields on matching lemmas. Unknown lemma keys are reported
rather than silently ignored, since a typo would otherwise look like success.

Verdicts (closed set):
  lemma        real Esperanto word that belongs in the dictionary; give a gloss
  proper-noun  name of a person, place, organisation or publication
  foreign      word of another language quoted in the text
  ocr-artifact misprint or scanning corruption
  fragment     piece of a longer word, not a word itself
  inflection   regular form of a root already in DICT/entries.jsonl
  numeral      a compound number written solid — okdekkvin, dudeksepa. A
               regular formation from an infinite set, so it is real Esperanto
               and still not a headword
  nonce        a word coined by one author and used only in that text, whether
               or not the text glosses it. Attested, but not the language's
  uncertain    cannot be judged from the citations shown

Only 'lemma' reaches the dictionary. The other verdicts exist to record a
judgement once, so that no later round asks anyone the same question again.
"""
import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHARDS = os.path.join(ROOT, 'DICT', 'shards')
VERDICTS = {'lemma', 'proper-noun', 'foreign', 'ocr-artifact', 'fragment',
            'inflection', 'numeral', 'nonce', 'uncertain'}


def shard_path(spec):
    index, count = (int(part) for part in spec.split('/'))
    path = os.path.join(SHARDS, 'shard-%d-of-%d.jsonl' % (index, count))
    if not os.path.exists(path):
        sys.exit('%s does not exist — run: python3 tools/mine_lemmas.py '
                 '--shard %s' % (path, spec))
    return path


def read(path):
    with open(path, encoding='utf-8') as fh:
        return [json.loads(line) for line in fh if line.strip()]


def write(path, records):
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as fh:
        for record in records:
            fh.write(json.dumps(record, ensure_ascii=False) + '\n')
    os.replace(tmp, path)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--shard', required=True, help='I/N, e.g. 3/8')
    parser.add_argument('--list', action='store_true')
    parser.add_argument('--apply', metavar='FILE')
    parser.add_argument('--status', action='store_true')
    parser.add_argument('--top', type=int, default=100)
    parser.add_argument('--kind', default='unknown')
    args = parser.parse_args()

    path = shard_path(args.shard)
    records = read(path)

    if args.status:
        reviewed = sum(1 for r in records if r.get('verdict'))
        pending = [r for r in records
                   if r['kind'] == args.kind and not r.get('verdict')]
        print('shard %s: %d lemmas, %d reviewed, %d %s pending'
              % (args.shard, len(records), reviewed, len(pending), args.kind))
        return 0

    if args.list:
        pending = [r for r in records
                   if r['kind'] == args.kind and not r.get('verdict')]
        pending.sort(key=lambda r: -r['count'])
        for record in pending[:args.top]:
            print(json.dumps({
                'lemma': record['lemma'],
                'count': record['count'],
                'pos_guess': record['pos_guess'],
                'forms': dict(sorted(record['forms'].items(),
                                     key=lambda kv: -kv[1])[:4]),
                'citations': [{'source': c['source'], 'text': c['text']}
                              for c in record['citations'][:2]],
            }, ensure_ascii=False))
        return 0

    if args.apply:
        with open(args.apply, encoding='utf-8') as fh:
            decisions = json.load(fh)
        index = {r['lemma']: r for r in records}
        applied, missing, bad = 0, [], []
        for lemma, fields in decisions.items():
            record = index.get(lemma)
            if record is None:
                missing.append(lemma)
                continue
            verdict = fields.get('verdict')
            if verdict is not None and verdict not in VERDICTS:
                bad.append((lemma, verdict))
                continue
            for field in ('verdict', 'gloss', 'note'):
                if field in fields:
                    record[field] = fields[field]
            applied += 1
        write(path, records)
        print('applied %d verdicts to %s' % (applied, os.path.basename(path)))
        if missing:
            print('  %d lemmas not in this shard: %s'
                  % (len(missing), ', '.join(missing[:8])))
        if bad:
            print('  %d invalid verdicts (allowed: %s): %s'
                  % (len(bad), ', '.join(sorted(VERDICTS)),
                     ', '.join('%s=%s' % b for b in bad[:5])))
        return 1 if (missing or bad) else 0

    parser.error('one of --list, --apply or --status is required')


if __name__ == '__main__':
    sys.exit(main())
