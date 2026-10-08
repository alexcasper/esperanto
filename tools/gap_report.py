#!/usr/bin/env python3
"""Vocabulary gap: frequent corpus lemmas that DICT/entries.jsonl lacks.

Usage:
  python3 tools/gap_report.py [--min-sources 3] [--min-count 5]
                              [--mixed-wp 10] [--wp-only 50]
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
  foreign        a letter outside the Esperanto alphabet (q w x y), or a
                 Romance/German function word (della, beide, chose)
  participle     -anta/-inta/-onta/-ata/-ita/-ota and -nte/-te adverbials on
                 a verb we hold, or on a verb that is itself a candidate
                 (establita beside establi): inflection, not a headword
  capitalised    under a quarter of occurrences lower-case: names that wiki
                 reference lists lower-case now and then (anna, otto) and
                 country/place names (afganio); held out of the queue
                 pending a names policy, not rejected
  thin           below the evidence bar (below)
  queue          everything else: real gap

Evidence bar (esp-nuk). With the Vikipedio corpus, ~42.6k of the ~42.9k
sources are single wp-* articles, so a bare source count stops meaning
breadth: three stubs clear it. Sources are split by register and a lemma is
queued in the first tier it meets:

  broad    >= --min-sources non-Wikipedia sources (the pre-Vikipedio bar,
           unchanged in meaning)
  mixed    1+ non-Wikipedia source and >= --mixed-wp wp articles
  wp-only  no non-Wikipedia source, >= --wp-only wp articles; modern and
           technical vocabulary, reviewed with extra scrutiny

and --min-count occurrences in every tier. The queue is ordered by tier,
then non-Wikipedia sources, then wp articles, then count.

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
NON_ESPERANTO = re.compile(r'[qwxy]')
# Only forms with an open-class ending reach this test, and only lemmas not
# in the dictionary, so Esperanto homographs (para, sono) are excluded here
# by hand rather than by the filter.
FOREIGN_FUNCTION = set('''della delle dalla nella alla sulla degli dei
questo questa quelle cette notre votre comme elle une chose beide eine keine
meine seine diese desde este esta'''.split())
TIERS = ('broad', 'mixed', 'wp-only')
CAPITAL_SHARE = 0.25


def register(c):
    """(non-Wikipedia sources, wp-* article sources)."""
    wp = sum(1 for s in c.get('sources') or [] if s.startswith('wp-'))
    return len(c.get('sources') or []) - wp, wp


def tier(c, args):
    other, wp = register(c)
    if c['count'] < args.min_count:
        return None
    if other >= args.min_sources:
        return 'broad'
    if other >= 1 and wp >= args.mixed_wp:
        return 'mixed'
    if other == 0 and wp >= args.wp_only:
        return 'wp-only'
    return None


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


def classify(c, dict_words, roots, english, args, candidates=()):
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
    if NON_ESPERANTO.search(lemma) or lemma in FOREIGN_FUNCTION:
        return 'foreign'
    m = PARTICIPLE.match(lemma)
    # The verb may be held as a root only: UV files pov' as the adjective
    # 'pova', so 'povante' must be checked against roots, not words. Or it
    # may be a candidate itself: review the verb, not its participles.
    if m and ((m.group(1) + 'i') in dict_words or
              (m.group(1) + 'i') in candidates or
              esperanto.peel_affixes(m.group(1), roots) in roots):
        return 'participle'
    if 'lower' in c and c['lower'] < CAPITAL_SHARE * c['count']:
        return 'capitalised'
    if tier(c, args) is None:
        return 'thin'
    return 'queue'


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--min-sources', type=int, default=3)
    ap.add_argument('--min-count', type=int, default=5)
    ap.add_argument('--mixed-wp', type=int, default=10,
                    help='wp-* articles needed beside 1-2 other sources')
    ap.add_argument('--wp-only', type=int, default=50,
                    help='wp-* articles needed with no other source')
    ap.add_argument('--queue', default=QUEUE)
    ap.add_argument('--top', type=int, default=40)
    args = ap.parse_args()

    roots, dict_words = esperanto.load_vocabulary(ENTRIES)
    english = load_english()
    with open(CANDIDATES, encoding='utf-8') as fh:
        cands = [json.loads(line) for line in fh if line.strip()]
    lemmas = {c['lemma'] for c in cands}
    buckets = collections.defaultdict(list)
    for c in cands:
        buckets[classify(c, dict_words, roots, english, args, lemmas)].append(c)

    def order(c):
        other, wp = register(c)
        return (TIERS.index(tier(c, args)), -other, -wp, -c['count'],
                c['lemma'])
    queue = sorted(buckets['queue'], key=order)
    os.makedirs(os.path.dirname(args.queue), exist_ok=True)
    with open(args.queue, 'w', encoding='utf-8') as fh:
        for c in queue:
            other, wp = register(c)
            fh.write(json.dumps({
                'lemma': c['lemma'], 'kind': c['kind'], 'count': c['count'],
                'sources': len(c['sources']), 'tier': tier(c, args),
                'other_sources': other, 'wp_sources': wp, 'forms': c['forms'],
                # Prefer non-Wikipedia citations: wp-only lines read most
                # like reference prose and least like usage.
                'citations': sorted(c['citations'], key=lambda x:
                                    x['source'].startswith('wp-'))[:3]},
                ensure_ascii=False) + '\n')

    total = sum(len(v) for v in buckets.values())
    print('%d candidate lemmas against %d dictionary words'
          % (total, len(dict_words)))
    for name in ('in-dict', 'reviewed', 'closed-class', 'no-ending', 'english',
                 'foreign', 'participle', 'capitalised', 'thin', 'queue'):
        kinds = collections.Counter(c['kind'] for c in buckets[name])
        print('  %-12s %6d  %s' % (name, len(buckets[name]),
                                   ', '.join('%s=%d' % kv
                                             for kv in kinds.most_common())))
    print('queue: broad >= %d other sources | mixed 1+ other & >= %d wp | '
          'wp-only >= %d wp; all >= %d occurrences → %s'
          % (args.min_sources, args.mixed_wp, args.wp_only, args.min_count,
             args.queue))
    tiers = collections.Counter(tier(c, args) for c in queue)
    print('  tiers: ' + ', '.join('%s=%d' % (t, tiers[t]) for t in TIERS))
    for kind in ('unknown', 'derived'):
        top = [c for c in queue if c['kind'] == kind][:args.top]
        print('  top %s: %s' % (kind, ' '.join(
            '%s(%d/%d+%dwp)' % ((c['lemma'], c['count']) + register(c))
            for c in top)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
