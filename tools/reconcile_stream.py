#!/usr/bin/env python3
"""Streaming variant of reconcile_lemmas for corpus-scale merges (esp-4d9).

The in-memory merge (reconcile_lemmas.py) holds every merged record at once:
5.1 GB peak RSS / 34 s at 42,899 sources. This module keeps its per-lemma
merge logic byte-for-byte identical but never holds more than one lemma's
records plus fixed-size heaps:

  1. External per-shard sort: each shard file is split into sorted runs
     (sort by lemma, chunk_size records at a time), written to temp files.
  2. heapq k-way merge across all runs of all shards — records arrive in
     lemma order, so a lemma's records are contiguous and merged by the
     same per-logic as the in-memory version.
  3. Output pass identical to reconcile_lemmas.main's ordering and
     filtering.

Usage: python3 tools/reconcile_stream.py [--shards N] [--out FILE]
       [--min-count 2] [--write-ledger] [--chunk-size 200000]

Verification contract (esp-4d9): output must be byte-identical to
reconcile_lemmas.py on the same shard set.
"""
import argparse
import collections
import glob
import heapq
import json
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHARDS = os.path.join(ROOT, 'DICT', 'shards')
DEFAULT_OUT = os.path.join(ROOT, 'DICT', 'candidates.jsonl')
LEDGER = os.path.join(ROOT, 'DICT', 'verdicts.jsonl')

KIND_RANK = {'fragment': 0, 'unknown': 1, 'known': 2}


# --------------------------------------------------------------- run sort
def sorted_runs(path, chunk_size, tmpdir):
    """Split one shard into lemma-sorted run files; return their paths.
    Each run line embeds the record's original line position (_pos) so the
    final ordering can reproduce the in-memory merge's first-encounter
    tie-break exactly."""
    runs = []
    chunk = []
    with open(path, encoding='utf-8') as fh:
        for pos, line in enumerate(fh):
            if not line.strip():
                continue
            record = json.loads(line)
            chunk.append((record['lemma'], pos, record))
            if len(chunk) >= chunk_size:
                runs.append(_flush(chunk, tmpdir))
                chunk = []
    if chunk:
        runs.append(_flush(chunk, tmpdir))
    return runs


def _flush(chunk, tmpdir):
    chunk.sort(key=lambda triple: triple[0])
    fd, path = tempfile.mkstemp(dir=tmpdir, suffix='.run')
    with os.fdopen(fd, 'w', encoding='utf-8') as out:
        for _, pos, record in chunk:
            out.write(json.dumps({'_pos': pos, **record},
                                 ensure_ascii=False) + '\n')
    return path


def run_reader(path):
    """Yield (lemma, pos, record) from a sorted run file."""
    with open(path, encoding='utf-8') as fh:
        for line in fh:
            if line.strip():
                record = json.loads(line)
                pos = record.pop('_pos')
                yield record['lemma'], pos, record


def iter_by_lemma(all_runs):
    """k-way merge all sorted runs; yield (lemma, records) groups.
    (Kept for reference; stream_groups is the variant that also carries
    shard identity and first-encounter order.)"""
    raise NotImplementedError


# ------------------------------------------------------- per-lemma merge
def merge_group(shard_names, records):
    """Identical logic to reconcile_lemmas.merge for one lemma's records.

    shard_names is a per-record list of shard basenames parallel to records;
    the caller tracks them because the original merge() reads them from the
    load generator. (Streaming: records arrive already grouped.)
    """
    first = records[0]
    entry = {
        'lemma': first['lemma'], 'kind': first['kind'], 'count': 0,
        'pos_guess': first.get('pos_guess'), 'forms': {},
        'citations': [], 'shards': [], 'verdict': None, 'gloss': None,
        'notes': [], 'conflicts': [], 'files': set(),
        'lower': 0, 'other_kinds': set(),
    }
    for shard, record in zip(shard_names, records):
        entry['lower'] += record.get('lower', 0)
        if record['kind'] != 'name':
            entry['other_kinds'].add(record['kind'])
        entry['count'] += record.get('count', 0)
        if KIND_RANK.get(record['kind'], 9) < KIND_RANK.get(entry['kind'], 9):
            entry['kind'] = record['kind']
        for form, n in (record.get('forms') or {}).items():
            entry['forms'][form] = entry['forms'].get(form, 0) + n
        entry['citations'].extend(record.get('citations') or [])
        entry['files'].update(record.get('files') or [])
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
            for part in note.split('; '):
                if part and part not in entry['notes']:
                    entry['notes'].append(part)
    return entry


def pick_citations(citations, limit=5):
    """Same breadth-first source round-robin as reconcile_lemmas, with the
    esp-0mu non-Wikipedia preference: identical sort key, identical loop."""
    by_source = collections.OrderedDict()
    for citation in sorted(
            citations,
            key=lambda cit: cit['source'].startswith('wp-')):
        by_source.setdefault(citation['source'], []).append(citation)
    picked = []
    while len(picked) < limit and any(by_source.values()):
        for source in list(by_source):
            if by_source[source] and len(picked) < limit:
                picked.append(by_source[source].pop(0))
    return picked


def finalize(entry):
    """Post-merge fixes identical to the tail of reconcile_lemmas.merge."""
    others = entry.pop('other_kinds')
    if entry['lower'] == 0 and others & {'unknown', 'derived'}:
        entry['kind'] = 'name'
    elif entry['kind'] == 'name' and others:
        entry['kind'] = min(others, key=lambda k: KIND_RANK.get(k, 9))
    entry['citations'] = pick_citations(entry['citations'])
    files = entry.pop('files')
    entry['sources'] = sorted(files or {c['source']
                                        for c in entry['citations']})
    return entry


def main():
    parser = argparse.ArgumentParser(
        description='Streaming lemma reconcile (esp-4d9)')
    parser.add_argument('--shards', type=int, default=None)
    parser.add_argument('--out', default=DEFAULT_OUT)
    parser.add_argument('--min-count', type=int, default=2)
    parser.add_argument('--write-ledger', metavar='FILE', nargs='?',
                        const=LEDGER, default=None)
    parser.add_argument('--chunk-size', type=int, default=50000,
                        help='records per external-sort run')
    args = parser.parse_args()

    pattern = 'shard-*-of-%d.jsonl' % args.shards if args.shards else 'shard-*.jsonl'
    shard_files = sorted(glob.glob(os.path.join(SHARDS, pattern)))
    if not shard_files:
        sys.exit('no shard files matching %s in %s' % (pattern, SHARDS))

    import resource
    t0 = __import__('time').monotonic()

    merged = []  # (kind_rank, -count, first_encounter, spill_path)
    with tempfile.TemporaryDirectory(prefix='reconcile-stream-') as tmpdir:
        all_runs, shard_names = [], {}
        for path in shard_files:
            base = os.path.basename(path)
            runs = sorted_runs(path, args.chunk_size, tmpdir)
            all_runs.extend(runs)
            shard_names.update({run: base for run in runs})
        run_shards = [shard_names[run] for run in all_runs]

        # Entries spill to disk as they are produced; only the ordering
        # tuples stay in memory.
        entry_fd, entry_path = tempfile.mkstemp(dir=tmpdir, suffix='.entries')
        entry_out = os.fdopen(entry_fd, 'w', encoding='utf-8')

        def flush_entry(entry):
            entry_out.write(json.dumps(entry, ensure_ascii=False) + '\n')

        grouped = stream_groups(all_runs, run_shards)
        for lemma, shard_list, records, first_key in grouped:
            entry = finalize(merge_group(shard_list, records))
            if entry['count'] >= args.min_count or entry.get('verdict'):
                # First-encounter tie-break (shard index, line position):
                # the in-memory merge processes shard files in sorted order
                # and lines in file order, and its dict insertion order —
                # what sorted() stability tie-breaks on — is exactly this
                # key sequence. The line index stands in for the entry.
                merged.append((KIND_RANK.get(entry['kind'], 9),
                               -entry['count'], first_key,
                               len(merged)))
                flush_entry(entry)
        entry_out.close()

        ordered_idx = [t[3] for t in
                       sorted(merged, key=lambda t: (t[0], t[1], t[2]))]
        # Spill lines are raw JSON strings (~200 B each, ~70 MB for 355k
        # entries) — compact enough to hold for the reorder, unlike the
        # parsed dicts that made the in-memory merge peak at 5.1 GB.
        with open(entry_path, encoding='utf-8') as entries:
            lines = entries.readlines()
        with open(args.out, 'w', encoding='utf-8') as out:
            for line_no in ordered_idx:
                out.write(lines[line_no])
            # ordered_idx is the final output order; the ledger needs the
            # reviewed subset in that same order.
            if args.write_ledger:
                # Re-parse only reviewed lines, in output order.
                with open(args.write_ledger, 'w', encoding='utf-8') as fh:
                    n_reviewed = 0
                    for line_no in ordered_idx:
                        entry = json.loads(lines[line_no])
                        if not entry.get('verdict'):
                            continue
                        fh.write(json.dumps({
                            'lemma': entry['lemma'],
                            'verdict': entry['verdict'],
                            'gloss': entry['gloss'],
                            'note': '; '.join(entry['notes']) or None,
                            'reviewed_in': sorted(set(entry['shards'])),
                            'disputed': [c for c in entry['conflicts']
                                         if c['field'] == 'verdict'] or None,
                        }, ensure_ascii=False) + '\n')
                        n_reviewed += 1
                print('  ledger: %d verdicts → %s'
                      % (n_reviewed, args.write_ledger))

    n_kept = len(merged)
    peak_mb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
    print('merged %d shard files → %s' % (len(shard_files), args.out))
    print('  %d distinct lemmas kept' % n_kept)
    print('  peak RSS: %.0f MB, %.1f s'
          % (peak_mb, __import__('time').monotonic() - t0))
    return 0


def stream_groups(all_runs, run_shards):
    """Yield (lemma, [shard names], [records]) by k-way merging sorted runs.

    Records within a group are ordered by (shard index, original line
    position) — the in-memory merge processes shard files in sorted order
    and lines in file order, so this reproduces its per-record processing
    sequence exactly (verdicts-kept, conflicts order, note order)."""
    heap = []
    for idx, run in enumerate(all_runs):
        it = run_reader(run)
        try:
            lemma, pos, record = next(it)
            heapq.heappush(heap, (lemma, idx, pos, it, record))
        except StopIteration:
            pass
    current, shard_list, records = None, [], []
    first_key = None
    while heap:
        lemma, idx, pos, it, record = heapq.heappop(heap)
        if current is not None and lemma != current:
            yield current, shard_list, records, first_key
            shard_list, records = [], []
            first_key = None
        if first_key is None:
            first_key = (idx, pos)
        current = lemma
        shard_list.append(run_shards[idx])
        records.append(record)
        try:
            nxt = next(it)
            heapq.heappush(heap, (nxt[0], idx, nxt[1], it, nxt[2]))
        except StopIteration:
            pass
    if records:
        yield current, shard_list, records, first_key


if __name__ == '__main__':
    sys.exit(main())
