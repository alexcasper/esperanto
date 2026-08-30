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
LEDGER = os.path.join(ROOT, 'DICT', 'verdicts.jsonl')

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


NOTE_LIMIT = 600


def join_notes(notes):
    """One note per distinct observation, bounded.

    Reviewers write a sentence or two per lemma; several shards seeing the
    same word should not multiply that. The cap is a backstop against any
    future path that reintroduces duplication.
    """
    seen, unique = set(), []
    for note in notes:
        text = note.strip()
        if text and text not in seen:
            seen.add(text)
            unique.append(text)
    joined = '; '.join(unique)
    if len(joined) > NOTE_LIMIT:
        joined = joined[:NOTE_LIMIT].rsplit(' ', 1)[0] + ' …'
    return joined or None


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
        if note and note not in entry['notes']:
            # Deduplicate. Without this the ledger grows 8x per round: the
            # reduce joins the note from all eight shards, the next map
            # restores that joined string into every shard, and the round
            # after joins eight copies of it. Three rounds took one note to
            # 1.2 million characters and the ledger to 431 MB, which GitHub
            # refused outright.
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
    parser.add_argument('--write-ledger', metavar='FILE', nargs='?',
                        const=LEDGER, default=None,
                        help='also write the verdicts to a ledger keyed by '
                             'lemma, so re-mining does not lose review work')
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

    if args.write_ledger:
        reviewed = [e for e in ordered if e.get('verdict')]
        with open(args.write_ledger, 'w', encoding='utf-8') as fh:
            for entry in reviewed:
                fh.write(json.dumps({
                    'lemma': entry['lemma'], 'verdict': entry['verdict'],
                    'gloss': entry['gloss'],
                    'note': join_notes(entry['notes']),
                    'reviewed_in': sorted(set(entry['shards'])),
                    # Carry disagreements into the ledger. Without this the
                    # ledger flattens each lemma to one verdict, re-mining
                    # writes that verdict back to every shard, and the fact
                    # that reviewers disagreed is silently erased.
                    'disputed': [c for c in entry['conflicts']
                                 if c['field'] == 'verdict'] or None,
                }, ensure_ascii=False) + '\n')
        print('  ledger: %d verdicts → %s'
              % (len(reviewed), args.write_ledger))

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
    # A gloss worded two ways is a style difference; two reviewers calling the
    # same word a lemma and a proper noun is a real disagreement. Only the
    # second needs anyone's attention, so do not report them as one number.
    verdict_clash = [e for e in conflicted
                     if any(c['field'] == 'verdict' for c in e['conflicts'])]
    gloss_clash = [e for e in conflicted if e not in verdict_clash]
    print('  %d gloss wordings differ between shards (benign)'
          % len(gloss_clash))
    if verdict_clash:
        print('  %d SUBSTANTIVE verdict disagreements:' % len(verdict_clash))
        for entry in verdict_clash[:15]:
            clash = next(c for c in entry['conflicts']
                         if c['field'] == 'verdict')
            print('    %-22s count=%-5d kept %-12s %s said %s'
                  % (entry['lemma'][:22], entry['count'], clash['kept'],
                     clash['shard'].replace('shard-', '').replace('.jsonl', ''),
                     clash['value']))
    else:
        print('  no substantive verdict disagreements')
    return 0


if __name__ == '__main__':
    sys.exit(main())
