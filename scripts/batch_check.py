#!/usr/bin/env python3
"""Post-promotion check for one DICT review batch.

Usage (repo root):
  python3 scripts/batch_check.py $TMPDIR/entries.bN.before.jsonl v2-batchN

Prints: key-diff vs the pre-batch snapshot (new / changed / lost, exact
words), sort + case-insensitive dupes, the batch's verdict counts,
accepted-but-not-promoted words, POS of new entries, gloss/citation gaps,
literary-citation counts, corpus-mined derived == segmented, and every new
segmentation as word=pre+ROOT+suf for reading.
"""
import collections
import json
import sys

ALPHA = 'abcĉdefgĝhĥijĵklmnoprsŝtuŭvz'
RANK = {c: i for i, c in enumerate(ALPHA)}


def load(path):
    with open(path, encoding='utf-8') as fh:
        return [json.loads(line) for line in fh if line.strip()]


def seg(m):
    return bool(m and (m.get('prefixes') or m.get('suffixes')))


def fmt(m):
    return '+'.join([a['m'] for a in m.get('prefixes', [])] +
                    [m['stem'].upper()] +
                    [a['m'] for a in m.get('suffixes', [])])


def main(snapshot, batch):
    before = {e['word']: e for e in load(snapshot)}
    entries = load('DICT/entries.jsonl')
    after = {e['word']: e for e in entries}
    ledger = {r['lemma']: r for r in load('DICT/verdicts.jsonl')}

    keys = [e['word'].lower() for e in entries]
    sk = [[RANK.get(c, 99) for c in k] for k in keys]
    new = sorted(set(after) - set(before))
    changed = [w for w in before if w in after and after[w] != before[w]]
    print('entries %d -> %d | new %d | changed %d %s | lost %d' % (
        len(before), len(entries), len(new), len(changed), changed[:10],
        len(set(before) - set(after))))
    print('dupes %d | sorted %s' % (len(keys) - len(set(keys)),
          all(sk[i] <= sk[i + 1] for i in range(len(sk) - 1))))

    batch_words = {w for w, r in ledger.items()
                   if any(b.startswith(batch) for b in r.get('reviewed_in') or [])}
    accepted = {w for w in batch_words if ledger[w].get('verdict') == 'lemma'}
    print('verdicts', dict(collections.Counter(
        ledger[w].get('verdict') for w in batch_words)))
    print('accepted - promoted', sorted(accepted - set(new)))
    print('promoted - accepted', sorted(set(new) - accepted))

    fresh = [after[w] for w in new]
    lit = lambda e: sum(not c['source'].startswith('wp-')
                        for c in e.get('citations') or [])
    print('pos', dict(collections.Counter(e['pos'] for e in fresh)),
          '| no gloss', sum(not e.get('gloss_en') for e in fresh),
          '| uncited', sum(not e.get('citations') for e in fresh))
    print('all-literary', sum(lit(e) == len(e.get('citations') or [])
                              for e in fresh),
          '| wp-only', [e['word'] for e in fresh if lit(e) == 0])
    cm = [e for e in entries if e.get('source') == 'corpus-mined']
    print('corpus-mined %d | derived %d | segmented %d | grammar_refs %d' % (
        len(cm), sum(bool(e.get('derived')) for e in cm),
        sum(seg(e.get('morphology')) for e in cm),
        sum('grammar_refs' in e for e in entries)))
    splits = ['%s=%s' % (e['word'], fmt(e['morphology']))
              for e in fresh if seg(e.get('morphology'))]
    print('%d new splits:' % len(splits))
    print('  '.join(splits))


if __name__ == '__main__':
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
