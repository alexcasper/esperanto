#!/usr/bin/env python3
"""Reduce step of lemma mining: merge the shard files into one candidate list.

Usage: python3 tools/reconcile_lemmas.py [--shards N] [--out DICT/candidates.jsonl]

Shards are mined and reviewed independently, so the same lemma turns up in
several of them with independently assigned verdicts. This merges them:

  counts and forms   summed across shards
  citations          kept, preferring one per distinct source over three from
                     the same book, since a lemma attested in four authors is
                     better evidence than one attested four times in one
  kind               the strictest a shard assigned — if any shard saw the
                     token only as a word fragment, that is worth knowing
  verdict/gloss      agreed values are kept; disagreements are NOT silently
                     resolved but recorded in `conflicts` for a human to settle

A conflict is a finding, not a failure: two reviewers disagreeing about whether
'volapuko' is a loanword or a proper noun is exactly the case worth surfacing.
"""
import argparse
import collections
import glob
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHARDS = os.path.join(ROOT, 'DICT', 'shards')
DEFAULT_OUT = os.path.join(ROOT, 'DICT', 'candidates.jsonl')

# Strictest first: a lemma seen as a fragment anywhere keeps that warning.
KIND_RANK = {'fragment': 0, 'unknown': 1, 'known': 2}


def load_shards(pattern):
    files = sorted(glob.glob(os.path.join(SHARDS, pattern)))
    if not files:
        sys.exit('no shard files matching %s in %s' % (pattern, SHARDS))
    for path in files:
        with open(path, encoding='utf-8') as fh:
            for line in fh:
                if line.strip():
                    yield os.path.basename(path), json.loads(line)
    return


def pick_citations(citations, limit=5):
    """Prefer breadth of sources over repetition within one source."""
    by_source = collections.OrderedDict()
    for citation in citations:
        by_source.setdefault(citation['source'], []).append(citation)
    picked = []
    while len(picked) < limit and any(by_source.values()):
        for source in list(by_source):
            if by_source[source] and len(picked) < limit:
                picked.append(by_source[source].pop(0))
    return picked


def merge(records):
    merged = {}
    for shard, record in records:
        lemma = record['lemma']
        entry = merged.setdefault(lemma, {
            'lemma': lemma, 'kind': record['kind'], 'count': 0,
            'pos_guess': record.get('pos_guess'), 'forms': {},
            'citations': [], 'shards': [], 'verdict': None, 'gloss': None,
            'notes': [], 'conflicts': [],
        })
        entry['count'] += record.get('count', 0)
        if KIND_RANK.get(record['kind'], 9) < KIND_RANK.get(entry['kind'], 9):
            entry['kind'] = record['kind']
        for form, n in (record.get('forms') or {}).items():
            entry['forms'][form] = entry['forms'].get(form, 0) + n
        entry['citations'].extend(record.get('citations') or [])
        entry['shards'].append(shard)

        for field in ('verdict', 'gloss'):
            value = record.get(field)
            if value in (None, ''):
                continue
            if entry[field] in (None, ''):
                entry[field] = value
            elif entry[field] != value:
                entry['conflicts'].append(
                    {'field': field, 'shard': shard, 'value': value,
                     'kept': entry[field]})
        note = record.get('note')
        if note:
            entry['notes'].append(note)

    for entry in merged.values():
        entry['citations'] = pick_citations(entry['citations'])
        entry['sources'] = sorted({c['source'] for c in entry['citations']})
    return merged


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--shards', type=int, default=None,
                        help='expected shard count, for the completeness check')
    parser.add_argument('--out', default=DEFAULT_OUT)
    args = parser.parse_args()

    pattern = 'shard-*-of-%d.jsonl' % args.shards if args.shards else 'shard-*.jsonl'
    merged = merge(load_shards(pattern))

    seen_shards = {s for e in merged.values() for s in e['shards']}
    if args.shards and len(seen_shards) != args.shards:
        print('WARNING: merged %d shard files, expected %d — %s'
              % (len(seen_shards), args.shards,
                 'reduce is running on an incomplete map'), file=sys.stderr)

    ordered = sorted(merged.values(),
                     key=lambda e: (KIND_RANK.get(e['kind'], 9), -e['count']))
    with open(args.out, 'w', encoding='utf-8') as fh:
        for entry in ordered:
            fh.write(json.dumps(entry, ensure_ascii=False) + '\n')

    verdicts = collections.Counter(e['verdict'] or '(unreviewed)'
                                   for e in ordered)
    kinds = collections.Counter(e['kind'] for e in ordered)
    conflicted = [e for e in ordered if e['conflicts']]
    multi = sum(1 for e in ordered if len(set(e['shards'])) > 1)

    print('merged %d shard files → %s' % (len(seen_shards), args.out))
    print('  %d distinct lemmas, %d seen in more than one shard'
          % (len(ordered), multi))
    print('  kinds: %s' % ', '.join('%s=%d' % kv for kv in kinds.most_common()))
    print('  verdicts: %s'
          % ', '.join('%s=%d' % kv for kv in verdicts.most_common()))
    if conflicted:
        print('  %d lemmas with disagreeing verdicts:' % len(conflicted))
        for entry in conflicted[:10]:
            clash = entry['conflicts'][0]
            print('    %-20s %s: kept %r, %s said %r'
                  % (entry['lemma'][:20], clash['field'], clash['kept'],
                     clash['shard'], clash['value']))
    else:
        print('  no verdict conflicts')
    return 0


if __name__ == '__main__':
    sys.exit(main())
