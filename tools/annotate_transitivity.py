#!/usr/bin/env python3
"""Record measured transitivity on the verb entries in DICT/entries.jsonl.

Usage: python3 tools/annotate_transitivity.py [--apply] [--min-clauses N]
                                              [--counts FILE] [--save-counts FILE]

The dictionary records no transitivity, and it is the hardest thing about
Esperanto verbs for a learner: *komenci* takes an object and *komenciĝi* does
not. PIV asserts it. `tools/transitivity.py` measures it over 698315 verb
clauses. This writes the measurement onto the entries as a field, with the
evidence attached, so a reader can see what it rests on.

THE THRESHOLDS ARE SET SO THAT NO CASE AS HARD AS THE HARDEST KNOWN CASE IS
DECIDED AUTOMATICALLY. Against the calibration set in tools/transitivity.py the
observed gap runs from 6.3% (`iri`, the highest undisputed intransitive) to
34.0% (`skribi`, the lowest undisputed transitive). The cut-offs sit INSIDE
that gap rather than at its edges:

    transitive     object share >= 40%
    intransitive   object share <= 5%
    uncertain      anything between

so `skribi` at 34.0%, `kompreni` at 39.6%, `iri` at 6.3% and `fali` at 5.0%
all come out `uncertain` and go to a human. Putting the cut-offs at the edges
of the gap instead would classify the whole calibration set correctly and would
be fitting the thresholds to the answer. Nothing in the calibration set is
misclassified under these; four of the twenty-four are declined.

`uncertain` is written rather than left blank, because a verb the corpus was
asked about and did not settle is different from a verb nobody measured, and
that band is where the genuinely ambitransitive verbs live.

A verb whose usual complement is an infinitive rather than a noun comes out
`uncertain`, which is the right answer rather than a failure: `komenci` 18.4%,
`povi` 14.6%, `devi` 12.6%, `voli` 18.5%. The measure counts nominal objects,
and these verbs take verbs. The 5% floor is low enough that none of them is
wrongly called intransitive.

Two limits are recorded on every entry rather than hidden. The measure has a
floor of about 6% from the bare directional accusative (*iri Parizon*), so
`intransitive` means "no more objects than a verb of motion picks up by
accident". And a transitive verb need not take an object in every clause — *li
skribis al mi* — so the share is a propensity, not a category.

This is derived data. `promote_lemmas.py --rebuild` re-promotes corpus-mined
entries from candidates and would drop the field from them, so re-run this
after any rebuild; it is idempotent and replaces what it finds.
"""
import argparse
import collections
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENTRIES = os.path.join(ROOT, 'DICT', 'entries.jsonl')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import esperanto                                          # noqa: E402
import transitivity                                       # noqa: E402
import verb_frequency                                     # noqa: E402

TRANSITIVE_AT = 40.0
INTRANSITIVE_AT = 5.0
MIN_CLAUSES = 100
FIELD = 'transitivity'


def verdict(share):
    if share >= TRANSITIVE_AT:
        return 'transitive'
    if share <= INTRANSITIVE_AT:
        return 'intransitive'
    return 'uncertain'


def measure(counts_file=None, save=None):
    """(seen, objects) — from a cached scan if given one, else by scanning."""
    if counts_file and os.path.exists(counts_file):
        cached = json.load(open(counts_file, encoding='utf-8'))
        return (collections.Counter(cached['seen']),
                collections.Counter(cached['objects']))
    verbs = verb_frequency.listed_verbs()
    stems = verb_frequency.listed_stems()
    roots, words = esperanto.load_vocabulary()
    seen, objects = transitivity.scan(
        verb_frequency.corpus_files(), verbs, stems, roots, words)[:2]
    if save:
        json.dump({'seen': dict(seen), 'objects': dict(objects)},
                  open(save, 'w', encoding='utf-8'))
    return seen, objects


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--min-clauses', type=int, default=MIN_CLAUSES)
    parser.add_argument('--counts', help='reuse a cached scan')
    parser.add_argument('--save-counts')
    args = parser.parse_args()

    seen, objects = measure(args.counts, args.save_counts)
    entries = [json.loads(line) for line in open(ENTRIES, encoding='utf-8')
               if line.strip()]

    tally = collections.Counter()
    changed = 0
    for entry in entries:
        if entry.get('pos') != 'verb':
            if FIELD in entry:            # a POS correction can strand one
                del entry[FIELD]
                changed += 1
            continue
        word = entry['word'].lower()
        clauses = seen.get(word, 0)
        if clauses < args.min_clauses:
            tally['too few clauses'] += 1
            if FIELD in entry:
                del entry[FIELD]
                changed += 1
            continue
        share = 100.0 * objects.get(word, 0) / clauses
        record = {
            'verdict': verdict(share),
            'object_share': round(share / 100.0, 3),
            'clauses': clauses,
            'basis': 'corpus',
        }
        tally[record['verdict']] += 1
        if entry.get(FIELD) != record:
            entry[FIELD] = record
            changed += 1

    total = sum(1 for e in entries if e.get('pos') == 'verb')
    print('%d verb entries; clause floor %d\n' % (total, args.min_clauses))
    for label in ('transitive', 'intransitive', 'uncertain', 'too few clauses'):
        print('   %-16s %5d  %4.1f%%'
              % (label, tally[label], 100.0 * tally[label] / max(total, 1)))
    print('\n%d entries would change' % changed)

    print('\ncalibration, as written to the file:')
    byword = {e['word'].lower(): e for e in entries}
    for label in ('transitive', 'intransitive'):
        for word in transitivity.CALIBRATION[label]:
            got = byword.get(word, {}).get(FIELD)
            if not got:
                print('   %-10s expected %-13s (no entry or too few clauses)'
                      % (word, label))
                continue
            flag = ''
            if got['verdict'] not in (label, 'uncertain'):
                flag = '   <-- MISCLASSIFIED'
            print('   %-10s expected %-13s -> %-13s %.1f%% of %d%s'
                  % (word, label, got['verdict'], 100 * got['object_share'],
                     got['clauses'], flag))

    if not args.apply:
        print('\n--dry-run by default. Re-run with --apply to write.')
        return 0

    tmp = ENTRIES + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as fh:
        for entry in entries:
            fh.write(json.dumps(entry, ensure_ascii=False) + '\n')
    os.replace(tmp, ENTRIES)
    print('\nwrote %s' % ENTRIES)
    return 0


if __name__ == '__main__':
    sys.exit(main())
