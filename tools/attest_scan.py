#!/usr/bin/env python3
"""Attestation by direct corpus scan: occurrences and distinct sources of a
dictionary word's inflected forms.

Usage (library): attest(words_with_pos) -> {word: {'count': n, 'sources': k,
                                         'sources_lit': l, 'sources_wiki': w}}
       python3 tools/attest_scan.py WORD[:POS] ...   # spot check

Independent of the miner's lemma keys. That matters for entries promoted
before esp-rac: their `attestation.sources` was counted from at most five
picked citations, and once an entry is promoted its stem becomes a root, so
re-mining files its inflections under the stem (rompiĝis -> rompiĝ) and the
original candidate record is no longer there to read (esp-58p).

Forms counted, by part of speech (the regular Esperanto paradigm only — no
participles, which are inflections the dictionary does not list):
  noun/adj  -o/-a, -oj/-aj, -on/-an, -ojn/-ajn
  adv       -e, -en
  verb      -i, -as, -is, -os, -us, -u
  other     the word itself
Scans the same files the miner reads (mine_lemmas.corpus_files()).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import esperanto  # noqa: E402
import mine_lemmas  # noqa: E402


def forms(word, pos):
    if pos in ('noun', 'adj') and word[-1:] in 'oa':
        return {word, word + 'j', word + 'n', word + 'jn'}
    if pos == 'adv' and word.endswith('e'):
        return {word, word + 'n'}
    if pos == 'verb' and word.endswith('i'):
        stem = word[:-1]
        return {word} | {stem + e for e in ('as', 'is', 'os', 'us', 'u')}
    return {word}


def attest(entries):
    """entries: iterable of (word, pos). Returns {word: {count, sources,
    sources_lit, sources_wiki}}: the register split matches the web lane's
    tools/mine_concordance.py (wp-* articles are wiki, every other source
    literary), so both writers of `attestation` produce the same shape."""
    owner = {}
    for word, pos in entries:
        for form in forms(word.lower(), pos):
            owner.setdefault(form, set()).add(word)
    result = {w: {'count': 0, 'sources': set()} for w, _ in entries}
    for name in mine_lemmas.corpus_files():
        with open(os.path.join(mine_lemmas.CORPUS, name), encoding='utf-8') as fh:
            for line in fh:
                for match in esperanto.TOKEN.finditer(line):
                    words = owner.get(match.group().lower().strip("'"))
                    if not words:
                        continue
                    for word in words:
                        result[word]['count'] += 1
                        result[word]['sources'].add(name)
    out = {}
    for w, r in result.items():
        wiki = sum(1 for s in r['sources'] if s.startswith('wp-'))
        out[w] = {'count': r['count'], 'sources': len(r['sources']),
                  'sources_lit': len(r['sources']) - wiki, 'sources_wiki': wiki}
    return out


if __name__ == '__main__':
    pairs = []
    for arg in sys.argv[1:]:
        word, _, pos = arg.partition(':')
        pairs.append((word, pos or 'noun'))
    for word, att in attest(pairs).items():
        print(word, att)
