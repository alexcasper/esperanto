#!/usr/bin/env python3
"""Score every SYNTH item's Esperanto text with the repo scorer's vocabulary.

Uses the exact recognition logic of tools/score_esperanto_text.py applied to
the item 'text' field only (the raw JSONL also contains structural keys like
'seed'/'recipient', which would depress a naive whole-file score).
Writes SYNTH/scores.jsonl (one line per item) and prints a distribution.
"""
import collections
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import score_esperanto_text as s


def item_score(text, roots, words):
    tokens = [t for t in s.TOKEN.findall(text) if len(t) > 1]
    if not tokens:
        return 0.0, 0
    hits = sum(1 for t in tokens if s.recognised(t, roots, words))
    return 100.0 * hits / len(tokens), len(tokens)


def main():
    roots, words = s.load_vocabulary()
    src = os.path.join(HERE, 'agent_comms.jsonl')
    dst = os.path.join(HERE, 'scores.jsonl')
    rows = []
    with open(src, encoding='utf-8') as fh:
        for line in fh:
            item = json.loads(line)
            known, ntok = item_score(item['text'], roots, words)
            rows.append({'id': item['id'], 'type': item['type'],
                         'tokens': ntok, 'known_pct': round(known, 2)})
    with open(dst, 'w', encoding='utf-8') as fh:
        for row in rows:
            fh.write(json.dumps(row, sort_keys=True) + '\n')

    pcts = [r['known_pct'] for r in rows]
    by_type = collections.defaultdict(list)
    for r in rows:
        by_type[r['type']].append(r['known_pct'])
    print('items:', len(rows), 'total tokens:', sum(r['tokens'] for r in rows))
    print('corpus known%%: %.2f  min: %.2f  max: %.2f'
          % (sum(p * n for p, n in ((r['known_pct'], r['tokens']) for r in rows))
             / sum(r['tokens'] for r in rows),
             min(pcts), max(pcts)))
    buckets = collections.Counter()
    for p in pcts:
        buckets[int(p // 10) * 10] += 1
    for b in sorted(buckets):
        print('  %3d-%3d%%: %d items' % (b, b + 9, buckets[b]))
    print('per-type mean known%:')
    for t, vals in sorted(by_type.items()):
        print('  %-9s %6.2f (n=%d)' % (t, sum(vals) / len(vals), len(vals)))
    worst = sorted(rows, key=lambda r: r['known_pct'])[:5]
    print('worst 5:', [(w['id'], w['known_pct']) for w in worst])


if __name__ == '__main__':
    main()
