#!/usr/bin/env python3
"""Restore diacritics that a scan dropped, but only where the answer is certain.

Usage: python3 tools/repair_diacritics.py [--apply] [--limit N]

Scans lose Esperanto diacritics in characteristic ways — ĉ read as o, ĝ as a
or S — so ĉiuj arrives as 'oiuj' and ĉar as 'oar'. These are not rare: one
240k-token source alone yields hundreds, and at that frequency they reach a
reviewer's queue looking like real vocabulary.

The repair is deliberately conservative, and the conditions matter more than
the substitutions:

  * the token as written must NOT be a word the dictionary knows, so nothing
    correct is ever touched;
  * exactly ONE candidate restoration may produce a known word. If two do, the
    token is ambiguous and is left alone rather than guessed at;
  * only single-character substitutions are tried.

So a repair only happens when the text says something that is not a word and
precisely one diacritic restoration makes it one. Everything else — proper
nouns, loanwords, genuinely unknown vocabulary — is left exactly as found.

Run without --apply to see what it would change and check the sample.
"""
import argparse
import collections
import glob
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import esperanto  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORPUS = os.path.join(ROOT, 'CORPUS')

# What a scan turns each diacritic into, observed in this corpus.
CONFUSIONS = {
    'ĉ': ('o', 'c', 'e', '6'),
    'ĝ': ('a', 'S', 'g', 'e'),
    'ŝ': ('s', 'S', 'g'),
    'ĵ': ('j', 'i'),
    'ĥ': ('h',),
    'ŭ': ('u', 'ii'),
}
TOKEN = re.compile(r'[A-Za-zĉĝĥĵŝŭĈĜĤĴŜŬ]{2,}')

# The repair only ever produces a word from this closed list. An earlier
# version accepted any form the dictionary could build, and a dry run showed
# why that fails: with 24k entries the morphology can build almost anything,
# so Petronius became "Petronĵus", the English 'our' became "ĉur" and the name
# Alicio became "Aliĉio" — 21580 such "repairs". Restricting the target to
# high-frequency function words makes the transformation checkable by eye:
# these are words a damaged Esperanto text certainly contains, and no English
# word or proper noun restores into one.
TARGETS = {
    'ĉi', 'ĉu', 'ĉe', 'ĉar', 'ĉiu', 'ĉiuj', 'ĉio', 'ĉia', 'ĉiam', 'ĉies',
    'ĉiel', 'ĉirkaŭ', 'ĉefe', 'ĉesi', 'ĉiel',
    'ĝi', 'ĝin', 'ĝis', 'ĝia', 'ĝiaj', 'ĝuste', 'ĝoji',
    'ŝi', 'ŝin', 'ŝia', 'ŝiaj', 'ŝati',
    'ĵus', 'ĥoro',
    'aŭ', 'kaŭ', 'laŭ', 'antaŭ', 'ankaŭ', 'ankoraŭ', 'kvazaŭ', 'baldaŭ',
    'hodiaŭ', 'preskaŭ', 'apenaŭ', 'malgraŭ', 'anstataŭ',
}


def candidates(token):
    """Every single-character diacritic restoration of this token."""
    for position, char in enumerate(token):
        for correct, wrongs in CONFUSIONS.items():
            for wrong in wrongs:
                if len(wrong) == 1 and char == wrong:
                    yield token[:position] + correct + token[position + 1:]


# Short damaged forms collide with ordinary French and German words, and
# several sources quote both at length: 'ce', 'ou', 'au', 'ai', 'ein', 'aus'
# would all be "repaired" inside a French letter. Repairs are therefore
# restricted to tokens of three characters or more, and these are never
# touched.
FOREIGN_WORDS = {'ein', 'eine', 'sein', 'aus', 'aux', 'ais', 'ces', 'cet',
                 'ceux', 'aim', 'air', 'ait', 'eau', 'oui', 'sur', 'son',
                 'ans', 'auf', 'ich', 'sie', 'sich', 'cas', 'cause'}
# A file only qualifies if it carries damage that cannot be anything else:
# 'oiuj' and 'oirkaŭ' are not words in any language, so their presence is
# proof the scan dropped diacritics here.
DAMAGE_PROOF = re.compile(r'\b(oiuj?|oirkaŭ|oiam|oio|oiel|ains|aisi)\b', re.I)
MIN_PROOF = 3


def repair_token(token, words, roots):
    low = token.lower()
    if len(low) < 3 or low in FOREIGN_WORDS:
        return None
    if esperanto.analyse(low, roots, words)[1] != 'unknown':
        return None
    fixes = {c for c in candidates(low) if c in TARGETS}
    if len(fixes) != 1:
        return None                      # zero: nothing to say; two: ambiguous
    fixed = fixes.pop()
    if token[0].isupper():
        fixed = fixed[0].upper() + fixed[1:]
    return fixed


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--limit', type=int, default=12)
    args = parser.parse_args()

    roots, words = esperanto.load_vocabulary()
    cache = {}
    changes = collections.Counter()
    touched = 0

    for path in sorted(glob.glob(os.path.join(CORPUS, '*.txt'))):
        text = open(path, encoding='utf-8').read()
        if len(DAMAGE_PROOF.findall(text)) < MIN_PROOF:
            continue          # no proof this file lost diacritics: leave it
        edits = 0

        def replace(match):
            nonlocal edits
            token = match.group()
            if token not in cache:
                cache[token] = repair_token(token, words, roots)
            fixed = cache[token]
            if fixed and fixed != token:
                edits += 1
                changes['%s → %s' % (token, fixed)] += 1
                return fixed
            return token

        repaired = TOKEN.sub(replace, text)
        if edits and args.apply:
            with open(path, 'w', encoding='utf-8') as fh:
                fh.write(repaired)
        if edits:
            touched += 1

    total = sum(changes.values())
    print('%s%d repairs across %d files'
          % ('' if args.apply else '[dry run] ', total, touched))
    for change, count in changes.most_common(args.limit):
        print('  %6d  %s' % (count, change))
    return 0


if __name__ == '__main__':
    sys.exit(main())
