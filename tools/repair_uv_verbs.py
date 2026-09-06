#!/usr/bin/env python3
"""Add the Fundamento verb roots the dictionary is missing.

Usage: python3 tools/repair_uv_verbs.py [--apply] [--calibrate]

`povi` and `voli` — the corpus's 2nd and 8th commonest verbs, 28560 lines
between them — are not in DICT/entries.jsonl. What is there is
`pova (adj) "be able, can"` and `vola (adj) "wish, will"`: verbal glosses filed
under an adjective ending.

The cause is in the source, not in the output. The Universala Vortaro gives
each root a gloss in five languages, and the English column is the only one
that cannot mark a verb:

    pov' pouvoir | be able, can | können | мочь | módz.
    vol' vouloir | wish, will | wollen | хотѣть | chcieć.

`pouvoir`, `können`, `мочь` and `módz` are all infinitives. `be able, can` is
not marked either way, and the importer read English alone. So this reads the
other four columns and proposes the citation form they imply.

Which column to trust is itself a measured question. Russian and Polish are no
help on their own: `ртуть` (mercury) ends in -ть and `rtęć` in -ć exactly as
their verbs do, and both voted `hidrarg'` a verb. French `mercure` ends in -re
like an infinitive. **German capitalises its nouns**, so it is the one column
that separates them, and the rule requires it. --calibrate checks that against
the 593 roots the importer already got right, which is the only reason to
believe the rule at all.

The reviewers' side of the failure is worth recording too, because it is a
pattern rather than an accident. Five of the nine missing verbs — povi,
remburi, sorĉi, trafi, volvi — were mined and then marked `inflection` by a
reviewer, one with the note "regular participle of povi". In every case an -o
or -a entry for the root already existed, so the -i form looked like an
inflected form of it. It is not. `povo` and `povi` are two words built from one
root, and neither is an inflection of the other.
"""
import argparse
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENTRIES = os.path.join(ROOT, 'DICT', 'entries.jsonl')
UV = os.path.join(ROOT, 'CORPUS',
                  'wsrc-Fundamento_de_Esperanto_Universala_vortaro.txt')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import esperanto                                          # noqa: E402
import promote_lemmas                                     # noqa: E402

SOURCE = 'Fundamento/UV-1905'
LINE = re.compile(r"^([a-zĉĝĥĵŝŭ]+)'\s+(.*?)\.?\s*$")
# German: a lowercase word ending -en or -n. Nouns are capitalised, which is
# what makes this the deciding column.
DE_VERB = re.compile(r'^[a-zäöüß]{2,}(en|eln|ern)$')
FR_VERB = re.compile(r'\b\w{3,}(er|ir|re|oir)\b\s*$')
RU_VERB = re.compile(r'(ть|ться|ти|чь|ѣть)$')
PL_VERB = re.compile(r'(ć|dz)$')
ENGLISH_VERB = re.compile(r'^to\s+\w')
# Roots that are affixes carry a gloss describing what they do, which can read
# as a verb in any language: `ek'` is glossed 'indique une action qui commence'.
AFFIX = set(esperanto.PREFIX) | set(esperanto.SUFFIX) | {'ek', 'mal'}


def uv_roots():
    """(root, french, english, german, russian, polish) for each UV line."""
    out = []
    with open(UV, encoding='utf-8') as fh:
        for line in fh:
            match = LINE.match(line.strip())
            if not match:
                continue
            columns = [c.strip() for c in match.group(2).split('|')]
            if len(columns) < 4:
                continue
            columns += [''] * (5 - len(columns))
            out.append((match.group(1),) + tuple(columns[:5]))
    return out


def is_verb(french, german, russian, polish):
    """German and Russian must both say verb.

    German alone is not enough: `rein` and `nüchtern` are adjectives that end
    like infinitives, and they put `pur'` and `sobr'` on the list. Russian
    alone is not enough either: `ртуть` (mercury) ends in -ть exactly as a verb
    does, and voted `hidrarg'` a verb. Together they separate, because the two
    languages mark the distinction in unrelated ways — German by capitalising
    nouns, Russian by inflection — so their errors do not coincide. French and
    Polish are checked but cannot decide: `mercure` and `sobre` end like
    infinitives, and `rtęć` like a verb.
    """
    first = lambda text: text.split(',')[0].strip()
    if not DE_VERB.match(first(german)):
        return False
    if russian and not RU_VERB.search(first(russian)):
        return False
    return bool(russian) or any((FR_VERB.search(french),
                                 PL_VERB.search(first(polish))))


def load_entries():
    with open(ENTRIES, encoding='utf-8') as fh:
        return [json.loads(line) for line in fh if line.strip()]


def calibrate(rows, byword):
    """The rule has to recover the roots the importer already got right."""
    known_verb = {r[0] for r in rows if byword.get(r[0] + 'i', {}).get('pos')
                  == 'verb'}
    known_noun = {r[0] for r in rows
                  if (r[0] + 'i') not in byword
                  and byword.get(r[0] + 'o', {}).get('pos') == 'noun'}
    called = {r[0] for r in rows if is_verb(r[1], r[3], r[4], r[5])}
    hit = len(known_verb & called)
    false = len(known_noun & called)
    print('roots the dictionary already files as verbs: %d' % len(known_verb))
    print('   the rule recovers %d of them (%.1f%%)'
          % (hit, 100.0 * hit / max(len(known_verb), 1)))
    print('roots with only a noun entry: %d' % len(known_noun))
    print('   the rule calls %d of them verbs (%.1f%%)'
          % (false, 100.0 * false / max(len(known_noun), 1)))
    print('\n   the ones it calls verbs despite a noun entry — each should be a\n'
          '   real verb the dictionary is missing, not a mistake:')
    for root in sorted(known_noun & called):
        row = next(r for r in rows if r[0] == root)
        print('      %-12s en=%-26s de=%s' % (root, row[2][:26], row[3][:20]))
    return called


def propose(rows, byword):
    """Verb entries the Fundamento implies and the dictionary lacks."""
    out = []
    for root, french, english, german, russian, polish in rows:
        if root in AFFIX or (root + 'i') in byword:
            continue
        if ENGLISH_VERB.match(english):
            continue        # the importer would have caught this one already
        if not is_verb(french, german, russian, polish):
            continue
        entry = {
            'word': root + 'i',
            'pos': 'verb',
            'root': root,
            'gloss_en': english,
            'source': SOURCE,
            'morphology': {'stem': root, 'ending': 'i'},
            # The English column is the one that cannot mark a verb, and it is
            # why these were missed. Recording where the verb reading comes
            # from keeps the entry checkable, and explains a gloss like
            # `sorĉi: witchcraft`, which is the UV's English verbatim against
            # a French column that reads `pratiquer la magie`.
            'note': ('verb reading from the UV French/German/Russian columns; '
                     'the English column does not mark it'),
        }
        if french:
            entry['gloss_fr'] = french
        out.append(entry)
    return out


def stale_verdicts(words):
    """Reviewer judgements these additions contradict.

    Not corrected here. CLAUDE.md is explicit that verdicts.jsonl is human
    judgement rather than derived data, and rewriting someone's verdict is a
    decision, not a repair. Reporting it is the repair.
    """
    path = os.path.join(ROOT, 'DICT', 'verdicts.jsonl')
    if not os.path.exists(path):
        return []
    out = []
    with open(path, encoding='utf-8') as fh:
        for line in fh:
            if not line.strip():
                continue
            record = json.loads(line)
            if record.get('lemma') in words and record.get('verdict') != 'lemma':
                out.append(record)
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--calibrate', action='store_true')
    args = parser.parse_args()

    rows = uv_roots()
    entries = load_entries()
    byword = {e['word'].lower(): e for e in entries}
    print('%d UV roots parsed, %d dictionary entries\n' % (len(rows),
                                                           len(entries)))
    if args.calibrate:
        calibrate(rows, byword)
        return 0

    additions = propose(rows, byword)
    print('%d verb entries the Fundamento implies and the dictionary lacks:\n'
          % len(additions))
    for entry in additions:
        existing = [(w, byword[w].get('pos'))
                    for w in (entry['root'] + 'o', entry['root'] + 'a',
                              entry['root'] + 'e') if w in byword]
        print('   %-12s %-28s fr=%-20s dictionary has %s'
              % (entry['word'], entry['gloss_en'][:28],
                 entry.get('gloss_fr', '')[:20], existing or 'nothing'))

    stale = stale_verdicts({e['word'] for e in additions})
    if stale:
        print('\n%d of these were mined and rejected by a reviewer as an\n'
              'inflection. DICT/verdicts.jsonl is human judgement and is not\n'
              'rewritten here — reported so someone can decide:' % len(stale))
        for record in stale:
            print('   %-12s verdict=%-12s %s'
                  % (record['lemma'], record['verdict'],
                     record.get('note', '')))

    if not args.apply:
        print('\n--dry-run by default. Re-run with --apply to write.')
        return 0

    merged = sorted(entries + additions,
                    key=lambda e: promote_lemmas.sortkey(e['word']))
    tmp = ENTRIES + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as fh:
        for entry in merged:
            fh.write(json.dumps(entry, ensure_ascii=False) + '\n')
    os.replace(tmp, ENTRIES)
    print('\nwrote %s: %d entries (%d added)'
          % (ENTRIES, len(merged), len(additions)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
