#!/usr/bin/env python3
"""Measure which verbs take a direct object, from the corpus rather than assertion.

Usage: python3 tools/transitivity.py [--top N] [--calibrate] [--audit]
                                     [--pairs] [--min-clauses N] [--files N]

Transitivity is the hardest thing about Esperanto verbs for a learner —
*komenci* takes an object and *komenciĝi* does not — and DICT/entries.jsonl
records none of it. PIV marks verbs `tr.` or `ntr.` by lexicographic
assertion. The corpus can be asked instead.

For each verb occurrence this finds its clause and looks for an accusative
object anywhere in it, in either direction, because Esperanto word order is
free and *la libron mi legis* is as good as *mi legis la libron*.

Three things wear the accusative and are NOT objects. Each of them, left in,
makes an intransitive verb look transitive, and the first would do it to the
commonest intransitive verbs in the language:

  directional   `en la domon`, `sur la tablon`, `iri Parizon`. Motion toward.
                An accusative governed by a place preposition is excluded, and
                so is any accusative in `-en`, which is an adverb plus the
                directional -n (`hejmen`, `tien`, `supren`) and never an
                object.
  adverbial     `la tutan tagon`, `tri fojojn`, `unu momenton`. Time and
                measure. Excluded by a closed list of nouns, because the shape
                is identical to an object and nothing but the noun tells them
                apart.
  not accusative at all   The obvious test — a word ending in -n after a vowel
                that can carry one — is 40% noise on this corpus. Its
                commonest matches are `en`, `kun`, `nun`, `jen`, `tamen`,
                `sen`, `tien`, plus names like `Aslaksen` and `Morten`. Only
                `-on/-ojn/-an/-ajn`, the accusative pronouns and the `-un`
                correlatives count, and the stripped form has to be a word the
                dictionary knows.

A verb whose complement is an INFINITIVE reads low, and correctly so: this
counts nominal objects. 46% of `komenci`'s occurrences are followed straight by
an infinitive (`li komencis demandi`), so it measures 18% and is not
transitive in the sense measured here. `povi`, `devi`, `voli` and `kuraĝi` are
the same. They are not intransitive either — see --calibrate, and the
`uncertain` band in tools/annotate_transitivity.py.

And one thing that IS an object, of a different verb. `li iris vidi la
plimulton`, `ŝi sidis aŭskultante la horloĝojn`, `ĝi estos ĉirkaŭinta la
terglobon`: an infinitive or participle standing between a verb and an
accusative owns that accusative. Without this rule the auxiliary `esti` and
every verb of motion inherits the object of whatever follows it, which was
worth 4 to 8 points on exactly the verbs that must score zero. The search runs
outward from the verb and stops at the next verb in each direction.

--calibrate is the gate on all of it. Verbs whose transitivity is not in
dispute — *vidi*, *havi*, *fari*, *doni*, *preni* against *esti*, *iri*,
*veni*, *resti*, *sidi*, *stari*, *morti*, *okazi* — must separate cleanly. If
they do not, the measure is broken and no other number it prints means
anything.
"""
import argparse
import collections
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORPUS = os.path.join(ROOT, 'CORPUS')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import esperanto                                          # noqa: E402
import verb_frequency                                     # noqa: E402

WORD = re.compile(r"[a-zA-ZĉĝĥĵŝŭĈĜĤĴŜŬ']+|[.,;:!?—–]")
BOUNDARY = set('.,;:!?—–')
# A subordinator opens a new clause, so an object after it belongs to the new
# verb and not the one before. `ke` is the important one: in `li diris, ke li
# vidis la domon` the object is vidis's, and without this it counts for diris.
SUBORDINATOR = {'ke', 'kiu', 'kiun', 'kiuj', 'kiujn', 'kiam', 'kie', 'kial',
                'kiel', 'kiom', 'kies', 'ĉar', 'se', 'dum', 'kvankam', 'ol',
                'ĉu', 'kaj', 'sed', 'aŭ', 'nek', 'do', 'tamen'}
# Accusative that is an object: -on/-ojn/-an/-ajn, the pronouns, the -un
# correlatives. NOT -en, which is adverbial or directional.
ACC_ENDING = ('ojn', 'ajn', 'on', 'an')
ACC_PRONOUN = {'min', 'vin', 'lin', 'ŝin', 'ĝin', 'nin', 'ilin', 'sin',
               'onin', 'cin'}
ACC_CORRELATIVE = re.compile(r'^(ki|ti|i|ĉi|neni)un$')
# Prepositions that take the accusative to mark motion toward. An accusative
# they govern is a destination, not an object.
PLACE_PREPOSITION = {'en', 'sur', 'sub', 'super', 'antaŭ', 'post', 'inter',
                     'trans', 'ĉe', 'apud', 'kontraŭ', 'ekster', 'ĉirkaŭ',
                     'preter', 'al', 'ĝis', 'tra'}
# Nouns whose accusative measures time or extent rather than naming an object.
FINITE_FORMS = {'present', 'past', 'future', 'conditional', 'imperative'}
NUMERAL = re.compile(r'^(unu|du|tri|kvar|kvin|ses|sep|ok|naŭ|dek|cent|mil)+$')
ADVERBIAL_NOUN = {
    'tago', 'nokto', 'horo', 'jaro', 'semajno', 'monato', 'minuto', 'sekundo',
    'momento', 'fojo', 'foje', 'vespero', 'mateno', 'tempo', 'daŭro',
    'paŝo', 'metro', 'kilometro', 'mejlo', 'colo', 'futo', 'jarcento',
    'matene', 'vespere', 'semajnfino', 'dimanĉo', 'lundo', 'mardo',
    'merkredo', 'ĵaŭdo', 'vendredo', 'sabato',
}
# Determiners and modifiers that may stand between a preposition and its noun,
# so `en la grandan domon` is still governed by `en`.
MODIFIER_ENDING = ('a', 'an', 'aj', 'ajn', 'la')


def is_accusative_object(token, roots, words):
    """Does this token wear an accusative that could mark an object?"""
    low = token.lower()
    if low in esperanto.GRAMMATICAL:
        return False
    if low in ACC_PRONOUN or ACC_CORRELATIVE.match(low):
        return True
    if not low.endswith(ACC_ENDING) or len(low) < 4:
        return False
    # Without this the corpus's names and its OCR debris are objects: `man`,
    # `Sha'ban`, `Aslaksen`. The check is on the de-accusatived form, so a
    # genuine object only has to be a word, not a headword.
    base = strip_accusative(low)
    return (base in words or base in roots
            or esperanto.strip_ending(base) in roots)


def strip_accusative(token):
    low = token.lower()
    for ending, base in (('ojn', 'oj'), ('ajn', 'aj'), ('on', 'o'),
                         ('an', 'a')):
        if low.endswith(ending):
            return low[:-len(ending)] + base
    return low


def governed_by_place(tokens, index):
    """Walk back over modifiers: is a place preposition governing this noun?"""
    step = index - 1
    while step >= 0 and index - step <= 4:
        low = tokens[step].lower()
        if low in PLACE_PREPOSITION:
            return True
        if (low == 'la' or low.endswith(('an', 'ajn'))
                or NUMERAL.match(low)):
            step -= 1
            continue
        return False
    return False


def is_adverbial(tokens, index):
    """Time and measure, including the ones with the noun left out.

    `la okan de Majo` is a date with `tagon` elided, and `ĉiun vesperon` puts
    the adverbial marking on the correlative, which is found first. Both were
    counted as objects of `okazi` and `sidi` before this looked past the single
    token to the phrase.
    """
    token = tokens[index]
    base = strip_accusative(token)
    if base.endswith('j'):
        base = base[:-1]
    if base in ADVERBIAL_NOUN:
        return True
    low = token.lower()
    modifier = (ACC_CORRELATIVE.match(low) or low.endswith(('an', 'ajn'))
                or NUMERAL.match(base[:-1] if base.endswith('a') else base))
    if not modifier:
        return False
    # A modifier is adverbial only by what it modifies: the head noun a token
    # or two later, or a following `de` for the elided-noun date.
    for step in range(index + 1, min(index + 4, len(tokens))):
        following = tokens[step].lower()
        if following == 'de' and NUMERAL.match(
                base[:-1] if base.endswith('a') else base):
            return True
        head = strip_accusative(following)
        if head.endswith('j'):
            head = head[:-1]
        if head in ADVERBIAL_NOUN:
            return True
        if following.endswith(('on', 'ojn')):
            return False
    return False


def clause_bounds(tokens, index):
    """The clause holding the verb at `index`: to the nearest boundary each way."""
    start = index - 1
    while start >= 0:
        low = tokens[start].lower()
        if low in BOUNDARY or low in SUBORDINATOR:
            break
        start -= 1
    end = index + 1
    while end < len(tokens):
        low = tokens[end].lower()
        if low in BOUNDARY or low in SUBORDINATOR:
            break
        end += 1
    return start + 1, end


def find_object(tokens, start, end, verb_index, verb_at, finite_at, is_finite,
                roots, words):
    """(token, index) of this verb's object, or None, plus what was rejected.

    Searches outward from the verb and stops at the next verb in each
    direction, because the nearer verb owns the accusative: in `li iris vidi
    la plimulton` the object is vidi's. Right first at equal distance, since
    verb-object is the unmarked order.
    """
    rejected = []

    def look(indices, leftward=False):
        for i in indices:
            if verb_at[i]:
                return None                       # a nearer verb owns it
            # An infinitive does not claim an accusative standing between it
            # and a preceding finite verb: in `lasis ilin fali` and `kuŝigis
            # min por dormi` the accusative is the finite verb's, and the
            # infinitive is its complement. Left-hand search only, because
            # that is the only side the construction puts it on.
            if leftward and not is_finite and any(finite_at[j]
                                                  for j in range(start, i)):
                return None
            token = tokens[i]
            if token in BOUNDARY:
                return None
            if not is_accusative_object(token, roots, words):
                continue
            if governed_by_place(tokens, i):
                rejected.append((token, 'directional'))
                continue
            if is_adverbial(tokens, i):
                rejected.append((token, 'adverbial'))
                continue
            return (token, i)
        return None

    return (look(range(verb_index + 1, end)) or
            look(range(verb_index - 1, start - 1, -1), leftward=True)), rejected


def scan(files, verbs, stems, roots, words, keep_examples=0):
    """Per verb: clauses seen, clauses with an object, and what was rejected."""
    seen = collections.Counter()
    objects = collections.Counter()
    rejected = collections.Counter()
    examples = collections.defaultdict(list)
    cache = {}
    for name in files:
        path = os.path.join(CORPUS, name)
        for lineno, line in enumerate(open(path, encoding='utf-8'), 1):
            tokens = WORD.findall(line)
            if len(tokens) < 3:
                continue
            # Every verb in the line, including the participles and infinitives
            # that are not counted themselves but do claim an object.
            analysed = [verb_frequency.verb_form(t, verbs, stems, roots, words,
                                                 cache)
                        if t not in BOUNDARY else (None, None, None)
                        for t in tokens]
            verb_at = [a[0] is not None for a in analysed]
            finite_at = [a[1] in FINITE_FORMS for a in analysed]
            for index, token in enumerate(tokens):
                if token in BOUNDARY:
                    continue
                infinitive, form, tier = analysed[index]
                if not infinitive or form == 'participle':
                    continue
                start, end = clause_bounds(tokens, index)
                seen[infinitive] += 1
                found, thrown = find_object(tokens, start, end, index,
                                            verb_at, finite_at,
                                            form in FINITE_FORMS,
                                            roots, words)
                for _tok, reason in thrown:
                    rejected[reason] += 1
                if found:
                    objects[infinitive] += 1
                    if keep_examples and len(examples[infinitive]) < keep_examples:
                        examples[infinitive].append(
                            (name, lineno, found[0],
                             ' '.join(tokens[start:end])[:100]))
    return seen, objects, rejected, examples


CALIBRATION = {
    'transitive': ['vidi', 'havi', 'fari', 'doni', 'preni', 'trovi', 'porti',
                   'meti', 'skribi', 'legi', 'aŭdi', 'kompreni'],
    'intransitive': ['esti', 'iri', 'veni', 'resti', 'sidi', 'stari', 'morti',
                     'okazi', 'kuŝi', 'dormi', 'fali', 'aperi'],
}


def calibrate(seen, objects):
    """The gate. If these two sets do not separate, nothing else is evidence."""
    print('Verbs whose transitivity is not in dispute. If these do not\n'
          'separate, the measure is broken.\n')
    scores = {}
    for label in ('transitive', 'intransitive'):
        print('  expected %s:' % label)
        for verb in CALIBRATION[label]:
            if seen[verb] < 50:
                print('     %-12s too few clauses (%d)' % (verb, seen[verb]))
                continue
            ratio = 100.0 * objects[verb] / seen[verb]
            scores.setdefault(label, []).append(ratio)
            print('     %-12s %5.1f%%   (%d of %d clauses)'
                  % (verb, ratio, objects[verb], seen[verb]))
        print()
    if len(scores) == 2:
        lo = min(scores['transitive'])
        hi = max(scores['intransitive'])
        print('  lowest transitive %.1f%%, highest intransitive %.1f%%' % (lo, hi))
        print('  %s' % ('SEPARATED — the measure discriminates'
                        if lo > hi else
                        'OVERLAP — read the two lists before trusting anything'))
    return scores


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--top', type=int, default=40)
    parser.add_argument('--min-clauses', type=int, default=200)
    parser.add_argument('--files', type=int,
                        help='limit to the first N corpus files, for a quick '
                             'pass while iterating')
    parser.add_argument('--calibrate', action='store_true')
    parser.add_argument('--audit', action='store_true')
    parser.add_argument('--pairs', action='store_true',
                        help='-ig-/-iĝ- pairs, where transitivity is the whole '
                             'point of the affix')
    args = parser.parse_args()

    verbs = verb_frequency.listed_verbs()
    stems = verb_frequency.listed_stems()
    roots, words = esperanto.load_vocabulary()
    files = verb_frequency.corpus_files()
    if args.files:
        files = files[:args.files]
    seen, objects, rejected, examples = scan(
        files, verbs, stems, roots, words,
        keep_examples=3 if args.audit else 0)

    print('%d verb clauses over %d files; %d carried an object'
          % (sum(seen.values()), len(files), sum(objects.values())))
    print('   excluded as directional %d, as adverbial %d\n'
          % (rejected['directional'], rejected['adverbial']))

    if args.calibrate:
        calibrate(seen, objects)
        return 0
    if args.audit:
        audit(seen, objects, examples, args.min_clauses)
        return 0
    if args.pairs:
        pairs(seen, objects, args.min_clauses)
        return 0

    ranked = sorted(((100.0 * objects[v] / n, v, objects[v], n)
                     for v, n in seen.items() if n >= args.min_clauses),
                    reverse=True)
    print('%-6s %-16s %8s %10s %8s' % ('', 'verb', 'object%', 'clauses',
                                       'with obj'))
    print('  most transitive:')
    for ratio, verb, got, n in ranked[:args.top // 2]:
        print('  %-6s %-16s %7.1f%% %10d %8d' % ('', verb, ratio, n, got))
    print('\n  least transitive:')
    for ratio, verb, got, n in ranked[-(args.top // 2):]:
        print('  %-6s %-16s %7.1f%% %10d %8d' % ('', verb, ratio, n, got))
    return 0


def audit(seen, objects, examples, min_clauses):
    """What is actually being counted as an object."""
    ranked = sorted(((100.0 * objects[v] / n, v, n)
                     for v, n in seen.items() if n >= min_clauses),
                    reverse=True)
    print('what got counted as an object, at the transitive end:')
    for ratio, verb, _n in ranked[:6]:
        print('   %s (%.1f%%)' % (verb, ratio))
        for name, lineno, token, clause in examples[verb]:
            print('      %-28s %-12s %s' % ('%s:%d' % (name[:20], lineno),
                                            token, clause))
    print('\nand at the intransitive end, where a hit is suspicious:')
    for ratio, verb, _n in ranked[-6:]:
        print('   %s (%.1f%%)' % (verb, ratio))
        for name, lineno, token, clause in examples[verb]:
            print('      %-28s %-12s %s' % ('%s:%d' % (name[:20], lineno),
                                            token, clause))


def pairs(seen, objects, min_clauses):
    """-ig- makes a verb transitive and -iĝ- makes it intransitive. Does it?"""
    print('%-18s %-9s   %-18s %-9s' % ('-ig- form', 'object%',
                                       '-iĝ- form', 'object%'))
    rows = []
    for verb in sorted(seen):
        if not verb.endswith('igi') or seen[verb] < min_clauses:
            continue
        partner = verb[:-3] + 'iĝi'
        if seen[partner] < min_clauses:
            continue
        rows.append((verb, 100.0 * objects[verb] / seen[verb], seen[verb],
                     partner, 100.0 * objects[partner] / seen[partner],
                     seen[partner]))
    for a, ra, na, b, rb, nb in sorted(rows, key=lambda r: -(r[1] - r[4])):
        print('%-18s %6.1f%% (%5d)   %-18s %6.1f%% (%5d)'
              % (a, ra, na, b, rb, nb))
    if rows:
        gap = sum(r[1] - r[4] for r in rows) / len(rows)
        print('\n%d pairs, mean gap %.1f points in the predicted direction'
              % (len(rows), gap))


if __name__ == '__main__':
    sys.exit(main())
