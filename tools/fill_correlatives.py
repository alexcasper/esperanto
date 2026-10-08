#!/usr/bin/env python3
"""Fill the correlative cells no dictionary layer supplies (esp-f76).

Usage: python3 tools/fill_correlatives.py [--dry-run]

GRAMMAR/grammar.md §3 sets out the 45 tabelvortoj; after the UV, ReVo and
O'Connor layers six cells were still empty (ties, ĉial, ĉies, ĉiom, nenial,
neniom — found by esp-hdt). tools/mine_lemmas.py skips correlatives by design
(they are closed-class, not vocabulary to discover), so the review pipeline
can never fill them. This tool does, holding them to the corpus-mined
standard of evidence:

  attestation  direct corpus scan of the word (tools/attest_scan.py)
  citations    three passages chosen by hand for genuine usage from distinct
               sources, pinned by file and line, and checked against CORPUS/
               on every run, so a corpus change cannot silently stale them
  source       `correlative-grid` — the cell is licensed by the paradigm, and
               the citations show it in use

Idempotent: cells already present (in any layer) are left alone.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import attest_scan  # noqa: E402
import esperanto  # noqa: E402
import mine_lemmas  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENTRIES = os.path.join(ROOT, 'DICT', 'entries.jsonl')
ALPHA = 'abcĉdefgĝhĥijĵklmnoprsŝtuŭvz'
RANK = {c: i for i, c in enumerate(ALPHA)}
SOURCE_TAG = 'correlative-grid'

# POS follows the UV's own filing of the filled cells' row-mates: -al adv
# (kial, tial, ial), -es and -om pron (kies, ies; kiom, tiom, iom).
CELLS = {
    'ties': ('pron', "that one's; the latter's (possessive of tiu)",
             [('ia-dlibra.kul.pl.49099.txt', 2649),
              ('ia-eowiki-Araba_lingvo-20200723.pdf.txt', 151),
              ('ia-LaHeroojDeLaNovaTagiolaKronikoDeNabil.txt', 5908)]),
    'ĉial': ('adv', 'for every reason, on all accounts',
             [('pg-32035.txt', 361), ('pg-52064.txt', 679),
              ('pg-64579.txt', 2072)]),
    'ĉies': ('pron', "everyone's, everybody's",
             [('pg-20943.txt', 446), ('ia-dlibra.kul.pl.49099.txt', 1428),
              ('ia-LaHeroojDeLaNovaTagiolaKronikoDeNabil.txt', 12787)]),
    'ĉiom': ('pron', 'all of it, the whole amount',
             [('pg-19030.txt', 752), ('pg-37642.txt', 443),
              ('ia-poemo-de-utnoa-eo-1jun-2023.txt', 12320)]),
    'nenial': ('adv', 'for no reason, on no account',
               [('pg-18178.txt', 1962), ('pg-31348.txt', 1850),
                ('pg-11511.txt', 398)]),
    'neniom': ('pron', 'none, no amount, not at all',
               [('pg-11511.txt', 538), ('ia-dlibra.kul.pl.49099.txt', 579),
                ('ia-poemo-de-utnoa-eo-1jun-2023.txt', 4754)]),
}


def citation(word, name, lineno):
    path = os.path.join(mine_lemmas.CORPUS, name)
    with open(path, encoding='utf-8') as fh:
        for i, line in enumerate(fh, 1):
            if i == lineno:
                break
        else:
            sys.exit('%s: %s has no line %d' % (word, name, lineno))
    if not any(m.group().lower() == word
               for m in esperanto.TOKEN.finditer(line)):
        sys.exit('%s: not found at %s:%d — corpus changed; re-pick citations'
                 % (word, name, lineno))
    text = ' '.join(line.split())
    if len(text) > 160:
        cut = text.lower().find(word)
        start = max(0, cut - 70)
        text = ('…' if start else '') + text[start:start + 150] + '…'
    return {'source': name, 'text': text}


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    with open(ENTRIES, encoding='utf-8') as fh:
        entries = [json.loads(l) for l in fh if l.strip()]
    present = {e['word'].lower() for e in entries}
    todo = [w for w in CELLS if w not in present]
    counts = attest_scan.attest([(w, CELLS[w][0]) for w in todo])
    added = []
    for word in todo:
        pos, gloss, cites = CELLS[word]
        added.append({
            'word': word, 'pos': pos, 'gloss_en': gloss, 'source': SOURCE_TAG,
            'attestation': counts[word],
            'citations': [citation(word, n, i) for n, i in cites],
        })
    merged = sorted(entries + added,
                    key=lambda e: [RANK.get(c, 99) for c in e['word'].lower()])
    if not args.dry_run and added:
        tmp = ENTRIES + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as fh:
            for entry in merged:
                fh.write(json.dumps(entry, ensure_ascii=False) + '\n')
        os.replace(tmp, ENTRIES)
    print('%s%d correlative cells added (%s); %d already present'
          % ('[dry run] ' if args.dry_run else '', len(added),
             ', '.join('%s %d/%d' % (e['word'], e['attestation']['count'],
                                     e['attestation']['sources'])
                       for e in added) or '-', len(CELLS) - len(todo)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
