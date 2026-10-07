#!/usr/bin/env python3
"""Vocabulary gap: frequent corpus lemmas that DICT/entries.jsonl lacks.

Usage:
  python3 tools/gap_report.py [--min-sources 3] [--min-count 5]
                              [--queue DICT/shards/gap-queue.jsonl] [--top 40]

Reads DICT/candidates.jsonl (tools/mine_lemmas.py + tools/reconcile_lemmas.py)
and DICT/entries.jsonl, and sorts every unreviewed candidate into one bucket:

  in-dict        the citation form already has an entry (any layer)
  reviewed       verdicts.jsonl already holds a decision
  closed-class   name / fragment / known-root inflection kinds from the miner
  no-ending      no open-class ending (-o/-a/-e/-i): English 'that', 'which',
                 URL pieces 'http' — never an Esperanto content word
  english        every observed surface form is an English headword in
                 DICT/english-index.jsonl ('bee', 'more', 'some')
  participle     -anta/-inta/-onta/-ata/-ita/-ota and -nte/-te adverbials on
                 a verb we hold: inflection in Esperanto lexicography, not a
                 headword (mortigita, ridante)
  thin           below the evidence bar (--min-sources / --min-count)
  queue          everything else: real gap, ordered by sources then count

The queue is written for review (tools/review_shard.py verdict vocabulary);
the bucket counts are the gap analysis recorded in DICT/NOTES-v2.md.
"""
import argparse
import collections
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import esperanto  # noqa: E402  (path set above)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CANDIDATES = os.path.join(ROOT, 'DICT', 'candidates.jsonl')
ENTRIES = os.path.join(ROOT, 'DICT', 'entries.jsonl')
ENGLISH = os.path.join(ROOT, 'DICT', 'english-index.jsonl')
QUEUE = os.path.join(ROOT, 'DICT', 'shards', 'gap-queue.jsonl')

OPEN_ENDING = re.compile(r'[oaei]$')
# English function words are not headwords in an English->Esperanto index, but
# are what leaks through from Gutenberg front matter: 'were', 'these', 'take'.
ENGLISH_FUNCTION = set('''a about above after again all also an and any are as
at be because been before being below between both but by can could did do
does doing down during each few for from further had has have having he her
here hers him his how i if in into is it its just like made make me might
more most must my no nor not now of off on once one only or other our out over
own same she should so some such take than that the their them then there
these they this those through to too under until up upon very was we were
what when where which while who whom why will with would you your'''.split())
PARTICIPLE = re.compile(r'^(.+?)(a|i|o)n?t(a|e)$')


def load_english():
    words = set()
    with open(ENGLISH, encoding='utf-8') as fh:
        for line in fh:
            if line.strip():
                head = json.loads(line).get('english', '')
                for w in re.findall(r'[a-z]+', head.lower()):
                    words.add(w)
    return words | ENGLISH_FUNCTION


def is_english(form, english):
    form = form.strip("'’")
    return (form in english or (form.endswith('s') and form[:-1] in english)
            or (form.endswith('ed') and form[:-2] in english))


def classify(c, dict_words, roots, english, args):
    lemma = c['lemma']
    if lemma in dict_words:
        return 'in-dict'
    if c.get('verdict'):
        return 'reviewed'
    if c['kind'] not in ('unknown', 'derived'):
        return 'closed-class'
    if not OPEN_ENDING.search(lemma) or "'" in lemma:
        return 'no-ending'
    forms = c.get('forms') or {}
    if forms and all(is_english(f, english) for f in forms):
        return 'english'
    m = PARTICIPLE.match(lemma)
    # The verb may be held as a root only: UV files pov' as the adjective
    # 'pova', so 'povante' must be checked against roots, not words.
    if m and ((m.group(1) + 'i') in dict_words or
              esperanto.peel_affixes(m.group(1), roots) in roots):
        return 'participle'
    if len(c.get('sources') or []) < args.min_sources or \
            c['count'] < args.min_count:
        return 'thin'
    return 'queue'


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--min-sources', type=int, default=3)
    ap.add_argument('--min-count', type=int, default=5)
    ap.add_argument('--queue', default=QUEUE)
    ap.add_argument('--top', type=int, default=40)
    args = ap.parse_args()

    roots, dict_words = esperanto.load_vocabulary(ENTRIES)
    english = load_english()
    buckets = collections.defaultdict(list)
    with open(CANDIDATES, encoding='utf-8') as fh:
        for line in fh:
            if line.strip():
                c = json.loads(line)
                buckets[classify(c, dict_words, roots, english, args)].append(c)

    queue = sorted(buckets['queue'],
                   key=lambda c: (-len(c['sources']), -c['count'], c['lemma']))
    os.makedirs(os.path.dirname(args.queue), exist_ok=True)
    with open(args.queue, 'w', encoding='utf-8') as fh:
        for c in queue:
            fh.write(json.dumps({
                'lemma': c['lemma'], 'kind': c['kind'], 'count': c['count'],
                'sources': len(c['sources']), 'forms': c['forms'],
                'citations': c['citations'][:3]}, ensure_ascii=False) + '\n')

    total = sum(len(v) for v in buckets.values())
    print('%d candidate lemmas against %d dictionary words'
          % (total, len(dict_words)))
    for name in ('in-dict', 'reviewed', 'closed-class', 'no-ending', 'english',
                 'participle', 'thin', 'queue'):
        kinds = collections.Counter(c['kind'] for c in buckets[name])
        print('  %-12s %6d  %s' % (name, len(buckets[name]),
                                   ', '.join('%s=%d' % kv
                                             for kv in kinds.most_common())))
    print('queue (>= %d sources, >= %d occurrences) → %s'
          % (args.min_sources, args.min_count, args.queue))
    for kind in ('unknown', 'derived'):
        top = [c for c in queue if c['kind'] == kind][:args.top]
        print('  top %s: %s' % (kind, ' '.join(
            '%s(%d/%d)' % (c['lemma'], c['count'], len(c['sources']))
            for c in top)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
