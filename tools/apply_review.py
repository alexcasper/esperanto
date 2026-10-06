#!/usr/bin/env python3
"""Apply a review batch (TSV) to the verdict ledger, DICT/verdicts.jsonl.

Usage: python3 tools/apply_review.py DICT/review/<batch>.tsv [...] [--dry-run]

Each TSV line is `lemma<TAB>verdict<TAB>gloss[<TAB>note]` (gloss may be empty
for non-lemma verdicts). The batch name (file stem) is recorded in the
ledger's `reviewed_in`, so every promoted entry can be traced to the review
that accepted it. Lemmas are checked against DICT/candidates.jsonl: a key
the miner never produced would be silently orphaned by mine_lemmas --ledger,
so it is reported instead.

Also normalises existing ledger notes: before reconcile_lemmas deduplicated
them, each mine/reconcile cycle multiplied a note by the shard count.

The ledger is then replayed into shards by
  python3 tools/mine_lemmas.py --shard I/N --ledger
followed by tools/reconcile_lemmas.py and tools/promote_lemmas.py.
"""
import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEDGER = os.path.join(ROOT, 'DICT', 'verdicts.jsonl')
CANDIDATES = os.path.join(ROOT, 'DICT', 'candidates.jsonl')
VERDICTS = {'lemma', 'proper-noun', 'foreign', 'ocr-artifact', 'fragment',
            'inflection', 'uncertain'}


def dedupe_note(note):
    if not note:
        return note
    parts = []
    for part in note.split('; '):
        if part and part not in parts:
            parts.append(part)
    return '; '.join(parts) or None


def read_batch(path):
    rows, errors = [], []
    with open(path, encoding='utf-8') as fh:
        for n, line in enumerate(fh, 1):
            line = line.rstrip('\n')
            if not line.strip() or line.startswith('#'):
                continue
            cols = line.split('\t')
            cols += [''] * (4 - len(cols))
            lemma, verdict, gloss, note = (c.strip() for c in cols[:4])
            if verdict not in VERDICTS:
                errors.append('%s:%d bad verdict %r' % (path, n, verdict))
            elif verdict == 'lemma' and not gloss:
                errors.append('%s:%d lemma %r without gloss' % (path, n, lemma))
            else:
                rows.append((lemma, verdict, gloss or None, note or None))
    return rows, errors


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('batches', nargs='+')
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    with open(CANDIDATES, encoding='utf-8') as fh:
        mined = {json.loads(l)['lemma'] for l in fh if l.strip()}
    ledger, order = {}, []
    with open(LEDGER, encoding='utf-8') as fh:
        for line in fh:
            if line.strip():
                rec = json.loads(line)
                rec['note'] = dedupe_note(rec.get('note'))
                ledger[rec['lemma']] = rec
                order.append(rec['lemma'])

    added = updated = 0
    problems = []
    for path in args.batches:
        batch = os.path.splitext(os.path.basename(path))[0]
        rows, errors = read_batch(path)
        problems += errors
        for lemma, verdict, gloss, note in rows:
            if lemma not in mined:
                problems.append('%s: %r is not a mined candidate' % (batch, lemma))
                continue
            rec = ledger.get(lemma)
            if rec is None:
                rec = {'lemma': lemma, 'reviewed_in': [], 'disputed': None}
                ledger[lemma] = rec
                order.append(lemma)
                added += 1
            else:
                updated += 1
            rec.update(verdict=verdict, gloss=gloss, note=note)
            if batch not in rec['reviewed_in']:
                rec['reviewed_in'] = sorted(set(rec['reviewed_in']) | {batch})

    for p in problems:
        print('  !', p, file=sys.stderr)
    if problems:
        sys.exit('%d problem(s); ledger not written' % len(problems))
    if not args.dry_run:
        tmp = LEDGER + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as fh:
            for lemma in order:
                rec = ledger[lemma]
                fh.write(json.dumps({k: rec.get(k) for k in (
                    'lemma', 'verdict', 'gloss', 'note', 'reviewed_in',
                    'disputed')}, ensure_ascii=False) + '\n')
        os.replace(tmp, LEDGER)
    print('%sledger: %d added, %d updated, %d total'
          % ('[dry run] ' if args.dry_run else '', added, updated, len(order)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
