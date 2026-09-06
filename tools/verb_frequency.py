#!/usr/bin/env python3
"""Which verbs the corpus actually uses, and how concentrated the choice is.

Usage: python3 tools/verb_frequency.py [--top N] [--affixes] [--audit]
                                       [--by-author] [--tense]

Esperanto's design claim is that a small root inventory plus productive
affixes covers the language. A verb frequency list tests that directly: if the
claim holds, a measurable share of verb TOKENS should be derivations —
ekvidi, plibonigi, komenciĝi — built on roots that are separately listed.
--affixes measures it.

The ending is not the test. Esperanto's verb endings look unambiguous and are
not, because the closed classes collide with them:

  -i   111571 tokens in the corpus, and the twelve commonest are mi, li, vi,
       pri, ili, ŝi, ĉi, ni, pli, ĝi, oni. Pronouns and prepositions, not
       verbs.
  -u   33157 tokens, the commonest being kiu, tiu, ĉu, unu, nu, du, ĉiu, iu.
       Correlatives and numerals.
  -as/-is/-os/-us are clean in Esperanto but not in the corpus, which contains
       Latin, French and English proper names.

So a token counts as a verb only when the infinitive it reduces to is listed
in DICT/entries.jsonl AS A VERB, or reduces by verbal affixes to one that is.
That gate is deliberately narrower than `analyse` returning 'known': with
27000 entries the morphology can build almost anything, so 'the result is a
word' stopped being evidence some time ago. --audit prints what the gate
turns away, which is the only way to know the gate is set right.

Four tiers, reported separately because they carry different confidence:

  listed       the infinitive is a dictionary entry with pos == verb.
  derived      it is not, but stripping verbal affixes reaches one that is —
               ekvidi -> vidi, plibonigi -> bonigi -> boni. This tier IS the
               design claim, so it is never silently merged into the first.
  root-listed  the infinitive is not listed in any form, but the same stem is
               a dictionary headword under -o, -a or -e. Fundamento Rule 6
               makes every root a verb by adding -i, and a source's choice of
               citation form is not a statement that the other endings are
               ungrammatical. This tier exists because the gate found the
               dictionary missing `povi` and `voli` outright — 21435 and 8362
               finite tokens, which would rank them third and sixth — while
               listing `pova (adj) be able, can` and `vola (adj) wish, will`,
               whose glosses are verbal. It is hundreds of roots, not two;
               see --audit. Reported separately and never merged, because it
               rests on a rule rather than on a lexicographer.
  rejected     none of the above. Counted and sampled, never included.

A root-listed lemma must additionally be attested in a FINITE or IMPERATIVE
form somewhere in the corpus — -as, -is, -os, -us or -u. A real verb gets
conjugated; a bare -i or a participle is not enough. This one rule removes two
different classes of junk that the audit found and nothing else caught:
`subite` and `rilate` are adverbs that end in -it-e and -at-e and so parse as
participles of `subi` and `rili`, worth 3245 spurious tokens between them; and
the corpus contains Latin and French, so `fili`, `ipsi`, `fati` and `mardi`
all look like infinitives whose stem happens to be a dictionary headword.
Neither class is ever conjugated.

Widening a rule without auditing what it now admits is how this project has
gone wrong before, so --audit prints the frequency head, a random sample and
the rejection list for exactly that check.
"""
import argparse
import collections
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORPUS = os.path.join(ROOT, 'CORPUS')
ENTRIES = os.path.join(ROOT, 'DICT', 'entries.jsonl')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import esperanto                                          # noqa: E402
import mine_lemmas                                        # noqa: E402

# Affixes that build a verb from another verb or from a non-verb root. Kept
# separate from esperanto.PREFIX/SUFFIX, which are the full derivational
# inventory: -in-, -ist- and -uj- build nouns and have no business here.
VERB_PREFIX = ['mal', 'ek', 're', 'dis', 'for', 'mis', 'retro', 'ne',
               'al', 'antaŭ', 'apud', 'ĉe', 'ĉirkaŭ', 'de', 'el', 'en',
               'inter', 'kontraŭ', 'krom', 'kun', 'per', 'post', 'preter',
               'pri', 'pro', 'sen', 'sub', 'super', 'sur', 'tra', 'trans',
               'kun', 'ge', 'eks', 'pli', 'plu']
VERB_SUFFIX = ['ig', 'iĝ', 'ad', 'et', 'eg', 'aĉ', 'um']

FINITE = {'as': 'present', 'is': 'past', 'os': 'future', 'us': 'conditional'}
CONJUGATED = set(FINITE.values()) | {'imperative'}
PARTICIPLE_TOKEN = re.compile(
    r'(?:ant|int|ont|at|it|ot)(?:ajn|aj|an|a|e)$')


def listed_verbs(path=ENTRIES):
    """Infinitives the dictionary calls verbs."""
    out = set()
    with open(path, encoding='utf-8') as fh:
        for line in fh:
            if not line.strip():
                continue
            entry = json.loads(line)
            if entry.get('pos') == 'verb':
                out.add(entry['word'].lower())
    return out


def listed_stems(path=ENTRIES):
    """stem -> the headword and pos the dictionary cites it under.

    Only -o, -a and -e headwords contribute. Anything else would let a
    two-letter fragment in, and the point of this index is to be narrower than
    esperanto.load_vocabulary's root set, not wider: that set includes every
    stem derived from every entry, so almost any string is in it.
    """
    out = {}
    with open(path, encoding='utf-8') as fh:
        for line in fh:
            if not line.strip():
                continue
            entry = json.loads(line)
            word = entry['word'].lower()
            if len(word) > 3 and word[-1] in 'oae' and "'" not in word:
                out.setdefault(word[:-1], (word, entry.get('pos')))
    return out


def reduce_to_listed(infinitive, verbs, max_depth=3):
    """(listed infinitive, [affixes stripped]) or (None, None).

    Peels one affix at a time and re-checks, so plibonigi reaches boni through
    pli- and -ig-. Depth is capped: without a cap, peeling finds a listed verb
    inside almost any long word, which is the failure this whole gate exists
    to avoid.
    """
    if infinitive in verbs:
        return infinitive, []
    stem, used = infinitive[:-1], []
    for _ in range(max_depth):
        for prefix in sorted(VERB_PREFIX, key=len, reverse=True):
            if stem.startswith(prefix) and len(stem) - len(prefix) >= 3:
                candidate = stem[len(prefix):]
                if candidate + 'i' in verbs:
                    return candidate + 'i', used + [prefix + '-']
                stem, used = candidate, used + [prefix + '-']
                break
        else:
            for suffix in sorted(VERB_SUFFIX, key=len, reverse=True):
                if stem.endswith(suffix) and len(stem) - len(suffix) >= 3:
                    candidate = stem[:-len(suffix)]
                    if candidate + 'i' in verbs:
                        return candidate + 'i', used + ['-' + suffix + '-']
                    stem, used = candidate, used + ['-' + suffix + '-']
                    break
            else:
                return None, None
        if stem + 'i' in verbs:
            return stem + 'i', used
    return None, None


def verb_form(token, verbs, stems, roots, words, cache):
    """(infinitive, form, tier) for a verb token, else (None, None, tier).

    form is present/past/future/conditional/imperative/infinitive/participle.
    """
    low = token.lower().strip("'")
    if low in cache:
        return cache[low]
    result = (None, None, 'not-a-verb')
    if low and low not in esperanto.GRAMMATICAL \
            and not esperanto.CORRELATIVE.match(low):
        infinitive, form = None, None
        tail = low[-2:]
        if tail in FINITE and len(low) > 3:
            infinitive, form = low[:-2] + 'i', FINITE[tail]
        elif PARTICIPLE_TOKEN.search(low):
            infinitive = esperanto.participle_infinitive(low, roots, words)
            form = 'participle'
        elif low.endswith('u') and len(low) > 3:
            infinitive, form = low[:-1] + 'i', 'imperative'
        elif low.endswith('i') and len(low) > 3:
            infinitive, form = low, 'infinitive'
        if infinitive:
            base, affixes = reduce_to_listed(infinitive, verbs)
            if base is not None:
                result = (infinitive, form,
                          'listed' if not affixes else 'derived')
            elif infinitive[:-1] in stems:
                result = (infinitive, form, 'root-listed')
            else:
                result = (None, None, 'rejected')
    cache[low] = result
    return result


def scan(files, verbs, stems, roots, words):
    """Count every verb token in these corpus files."""
    counts = collections.Counter()
    forms = collections.defaultdict(collections.Counter)
    by_tier = collections.defaultdict(collections.Counter)
    tiers = collections.Counter()
    affixes = collections.Counter()
    rejected = collections.Counter()
    cache = {}
    for name in files:
        path = os.path.join(CORPUS, name)
        text = open(path, encoding='utf-8').read()
        for token in esperanto.TOKEN.findall(text):
            infinitive, form, tier = verb_form(token, verbs, stems, roots,
                                               words, cache)
            tiers[tier] += 1
            if infinitive is None:
                if tier == 'rejected':
                    rejected[token.lower()] += 1
                continue
            counts[infinitive] += 1
            forms[infinitive][form] += 1
            by_tier[tier][infinitive] += 1
            if tier == 'derived':
                base, used = reduce_to_listed(infinitive, verbs)
                for affix in used:
                    affixes[affix] += 1
    # A root-listed lemma has only Rule 6 behind it, so make the corpus
    # corroborate it: keep it only where the text actually conjugates it.
    dropped = collections.Counter()
    for verb in list(by_tier['root-listed']):
        if not (CONJUGATED & set(forms[verb])):
            dropped[verb] = counts[verb]
            tiers['root-listed'] -= counts[verb]
            tiers['unconjugated'] += counts[verb]
            del counts[verb], forms[verb]
            del by_tier['root-listed'][verb]
    return counts, forms, tiers, affixes, rejected, by_tier, dropped


def corpus_files():
    excluded = mine_lemmas.ENGLISH_HEAVY | mine_lemmas.MULTILINGUAL
    return [f for f in sorted(os.listdir(CORPUS))
            if f.endswith('.txt') and f not in excluded]


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--top', type=int, default=40)
    parser.add_argument('--affixes', action='store_true',
                        help='derived-vs-simple share and the affix inventory')
    parser.add_argument('--audit', action='store_true',
                        help='what the dictionary gate turns away')
    parser.add_argument('--tense', action='store_true',
                        help='form distribution per verb')
    parser.add_argument('--by-author', action='store_true',
                        help='is the ranking a property of the language or of '
                             'whoever wrote the text')
    args = parser.parse_args()

    verbs = listed_verbs()
    stems = listed_stems()
    roots, words = esperanto.load_vocabulary()
    files = corpus_files()
    counts, forms, tiers, affixes, rejected, by_tier, dropped = scan(
        files, verbs, stems, roots, words)
    total = sum(counts.values())
    print('%d verb tokens over %d files, %d distinct verbs'
          % (total, len(files), len(counts)))
    for tier in ('listed', 'derived', 'root-listed', 'unconjugated',
                 'rejected'):
        print('   %-12s %8d tokens  %6d distinct'
              % (tier, tiers[tier], len(by_tier[tier])))
    print()

    if args.audit:
        audit(rejected, counts, total, by_tier, stems, dropped)
        return 0
    if args.affixes:
        report_affixes(counts, forms, affixes, verbs, total)
        return 0
    if args.by_author:
        by_author(verbs, stems, roots, words)
        return 0

    header = '%-6s %-16s %9s %7s %8s' % ('rank', 'verb', 'tokens', 'share',
                                         'cumul')
    if args.tense:
        header += '   %s' % 'form distribution'
    print(header)
    running = 0
    for rank, (verb, count) in enumerate(counts.most_common(args.top), 1):
        running += count
        line = ('%-6d %-16s %9d %6.2f%% %7.1f%%'
                % (rank, verb, count, 100.0 * count / total,
                   100.0 * running / total))
        if args.tense:
            spread = forms[verb]
            shown = sum(spread.values())
            line += '   ' + ' '.join(
                '%s %.0f%%' % (form[:4], 100.0 * n / shown)
                for form, n in spread.most_common(4))
        print(line)
    print('\nthe top %d cover %.1f%% of all verb tokens'
          % (args.top, 100.0 * running / total))
    ranked = [c for _v, c in counts.most_common()]
    for cut in (10, 50, 100, 500, 1000):
        if cut <= len(ranked):
            print('   top %-5d %5.1f%%' % (cut, 100.0 * sum(ranked[:cut])
                                           / total))
    running, need = 0, 0
    for count in ranked:
        running += count
        need += 1
        if running >= 0.9 * total:
            break
    print('   %d verbs (%.1f%% of the %d distinct) cover 90%% of tokens'
          % (need, 100.0 * need / len(ranked), len(ranked)))
    hapax = sum(1 for c in ranked if c == 1)
    print('   %d verbs occur exactly once (%.1f%% of distinct verbs)'
          % (hapax, 100.0 * hapax / len(ranked)))
    return 0


def audit(rejected, counts, total, by_tier, stems, dropped, seed=20260906):
    """The gate is only trustworthy if you look at what it refuses, and the
    root-listed tier is only trustworthy if you look at what it admits.

    Three views, because the frequency head and a random sample fail
    differently: the head catches a systematic error big enough to matter, the
    sample catches one spread thinly across the tail."""
    import random
    admitted = by_tier['root-listed']
    print('ROOT-LISTED TIER — the widened rule. %d tokens, %d distinct.'
          % (sum(admitted.values()), len(admitted)))
    print('\n  frequency head — each should be a plain Esperanto verb whose\n'
          '  root the dictionary happens to cite as a noun or adjective:')
    for verb, count in admitted.most_common(20):
        cited, pos = stems.get(verb[:-1], ('?', '?'))
        print('     %-16s %7d   dictionary has %s (%s)'
              % (verb, count, cited, pos))
    print('\n  random sample of 20 from the tail, which is where a widened\n'
          '  rule goes wrong without showing up in the head:')
    tail = [v for v, c in admitted.items() if c <= 3]
    for verb in random.Random(seed).sample(tail, min(20, len(tail))):
        cited, pos = stems.get(verb[:-1], ('?', '?'))
        print('     %-16s %7d   dictionary has %s (%s)'
              % (verb, admitted[verb], cited, pos))

    print('\nNEVER CONJUGATED — %d lemmas, %d tokens, dropped from the\n'
          'root-listed tier because the corpus never inflects them:'
          % (len(dropped), sum(dropped.values())))
    for verb, count in dropped.most_common(15):
        print('   %-16s %7d' % (verb, count))

    print('\nREJECTED — %d token types, %d tokens. Each should be a name, a\n'
          'foreign word, a scan error or a non-verb, NOT a verb:'
          % (len(rejected), sum(rejected.values())))
    for token, count in rejected.most_common(25):
        print('   %-24s %d' % (token, count))
    print('\n%d verbs occur once only (%.1f%% of distinct verbs)'
          % (sum(1 for c in counts.values() if c == 1),
             100.0 * sum(1 for c in counts.values() if c == 1)
             / max(len(counts), 1)))


def report_affixes(counts, forms, affixes, verbs, total):
    """The design claim, measured."""
    derived_types = derived_tokens = 0
    for verb, count in counts.items():
        base, used = reduce_to_listed(verb, verbs)
        if used:
            derived_types += 1
            derived_tokens += count
    print('derivations built on a separately listed verb:')
    print('   %d of %d distinct verbs (%.1f%%)'
          % (derived_types, len(counts), 100.0 * derived_types / len(counts)))
    print('   %d of %d verb tokens (%.1f%%)'
          % (derived_tokens, total, 100.0 * derived_tokens / total))
    print('\nthe affixes doing the work, by token:')
    for affix, count in affixes.most_common(20):
        print('   %-10s %8d' % (affix, count))


def by_author(verbs, stems, roots, words):
    """Is this ranking Esperanto, or is it whoever wrote the most?

    The diachronic study found every rate-based measure was carried by one
    writer. The same question has to be asked here before any frequency claim
    means anything about the language.
    """
    import csv
    dates = os.path.join(ROOT, 'RAW', 'DATES.tsv')
    pooled = collections.defaultdict(list)
    with open(dates, encoding='utf-8') as fh:
        for row in csv.DictReader(fh, delimiter='\t'):
            if row['written'] and row['attributed']:
                pooled[row['attributed']].append(row['source'])
    excluded = mine_lemmas.ENGLISH_HEAVY | mine_lemmas.MULTILINGUAL
    rankings = {}
    for who, sources in sorted(pooled.items()):
        files = [s for s in sources
                 if s not in excluded and os.path.exists(
                     os.path.join(CORPUS, s))]
        if not files:
            continue
        counts = scan(files, verbs, stems, roots, words)[0]
        if sum(counts.values()) < 5000:
            continue
        rankings[who] = counts
    print('%d authors with 5000+ verb tokens each\n' % len(rankings))
    pool = collections.Counter()
    for counts in rankings.values():
        pool.update(counts)
    reference = [v for v, _c in pool.most_common(20)]
    print('%-26s %s' % ('author', 'rank of the corpus top 10 in their own use'))
    for who, counts in sorted(rankings.items()):
        order = [v for v, _c in counts.most_common()]
        places = []
        for verb in reference[:10]:
            places.append(str(order.index(verb) + 1) if verb in order else '—')
        print('%-26s %s' % (who[:26], ' '.join('%3s' % p for p in places)))
    print('\ncorpus top 10: %s' % ', '.join(reference[:10]))

    # An eyeballed table is not a result. Mean pairwise rank agreement over
    # the verbs every author uses says how much of this ranking is the
    # language and how much is the writer.
    import itertools
    shared = set(reference[:30])
    for counts in rankings.values():
        shared &= set(counts)
    pairs = []
    for a, b in itertools.combinations(sorted(rankings), 2):
        first = sorted(shared, key=lambda v: -rankings[a][v])
        second = sorted(shared, key=lambda v: -rankings[b][v])
        rho = spearman([(first.index(v), second.index(v)) for v in shared])
        if rho is not None:
            pairs.append((rho, a, b))
    if pairs:
        pairs.sort()
        mean = sum(p[0] for p in pairs) / len(pairs)
        print('\n%d verbs are used by all %d authors. Mean pairwise rank\n'
              'agreement on them: rho = %+.2f over %d author pairs.'
              % (len(shared), len(rankings), mean, len(pairs)))
        print('   least alike: %s vs %s, rho=%+.2f'
              % (pairs[0][1][:22], pairs[0][2][:22], pairs[0][0]))
        print('   most alike:  %s vs %s, rho=%+.2f'
              % (pairs[-1][1][:22], pairs[-1][2][:22], pairs[-1][0]))


def spearman(pairs):
    """Rank correlation, ties averaged. Same implementation as
    tools/diachronic.py, kept local so neither tool imports the other."""
    if len(pairs) < 4:
        return None

    def ranks(values):
        order = sorted(range(len(values)), key=lambda i: values[i])
        out = [0.0] * len(values)
        i = 0
        while i < len(order):
            j = i
            while (j + 1 < len(order)
                   and values[order[j + 1]] == values[order[i]]):
                j += 1
            mean = (i + j) / 2.0 + 1
            for k in range(i, j + 1):
                out[order[k]] = mean
            i = j + 1
        return out

    xs, ys = ranks([p[0] for p in pairs]), ranks([p[1] for p in pairs])
    n = len(pairs)
    mx, my = sum(xs) / n, sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    den = (sum((x - mx) ** 2 for x in xs)
           * sum((y - my) ** 2 for y in ys)) ** 0.5
    return num / den if den else None


if __name__ == '__main__':
    sys.exit(main())
