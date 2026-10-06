#!/usr/bin/env python3
"""Cross-link DICT/entries.jsonl entries to GRAMMAR/grammar.md sections (esp-hdt).

Adds a `grammar_refs` array to entries the guide explains, so the dictionary
is navigable alongside the grammar:

  - the 40 word-building affixes  -> section 2 (Morfologio affix inventory)
  - the 45 correlatives           -> section 3 (La tabelvortoj grid)
  - participle morphemes          -> section 2 (participles row)
  - -uj- and country-name notes   -> section 6.1
  - negative correlatives         -> section 6.2 as well

Section anchors are the markdown headings' numbering (`grammar.md#2-morfologio`
style is not portable across renderers, so refs use `GRAMMAR/grammar.md §N`
plainly plus the heading slug used by GitHub).

Idempotent: existing grammar_refs are replaced, not appended. Run after any
entries.jsonl rebuild:
    python3 tools/link_grammar.py [--dry-run]
"""
import argparse
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENTRIES = os.path.join(ROOT, 'DICT', 'entries.jsonl')

AFFIXES_2 = re.compile(r'^[a-zĉĝĥĵŝŭ]{1,4}$')  # affix words are short morphemes

CORRELATIVE_ENDS = ('o', 'u', 'a', 'es', 'e', 'am', 'al', 'el', 'om')
CORRELATIVE_INITS = ('i', 'ki', 'ti', 'ĉi', 'neni')

NEGATIVE = re.compile(r'^neni')

PARTICIPLE_MORPHEMES = {'ant', 'int', 'ont', 'at', 'it', 'ot'}


def refs_for(entry):
    word = entry['word']
    pos = entry['pos']
    refs = []

    # 1. Word-building affixes -> section 2 (Morfologio)
    if pos in ('prefix', 'suffix'):
        refs.append(('2', 'Morfologio — affix inventory'))

    # 2. The correlative grid -> section 3 (La tabelvortoj)
    # noun POS catches 'ĉio', which O'Connor lists as a noun
    if pos in ('pron', 'adv', 'adj', 'particle', 'noun') and '-' not in word:
        init = next((p for p in CORRELATIVE_INITS
                     if word.startswith(p) and len(word) > len(p)), None)
        if init:
            rest = word[len(init):]
            if rest in CORRELATIVE_ENDS and init in ('ĉi', 'neni', 'ki', 'ti', 'i'):
                refs.append(('3', 'Sintakso — La tabelvortoj (correlatives)'))
                # negatives also -> 6.2 (single negation)
                if NEGATIVE.search(word):
                    refs.append(('6.2', 'Negation is single, not doubled'))

    # 3. Participle morphemes -> section 2 and 6.6
    if pos == 'suffix' and word in ('ant', 'int', 'ont', 'at', 'it', 'ot'):
        refs.append(('2', 'Morfologio — participles'))
        if word in ('at', 'it'):
            refs.append(('6.6', 'Passive participles: ongoing action (-ata) vs resulting state (-ita)'))

    # 4. -uj- country/container and country nouns -> 6.1
    if word == 'ujo' or (pos == 'suffix' and word == 'uj'):
        refs.append(('6.1', 'Country names: -ujo dominates, not -io'))

    # 5. Demonstrative particle ĉi -> 6.4
    if word == 'ĉi' and pos in ('particle', 'adv'):
        refs.append(('6.4', 'Demonstrative particle ĉi: preposed vs postposed'))

    # 6. Distributive preposition po -> 6.11
    if word == 'po' and pos == 'prep':
        refs.append(('6.11', 'Distributive preposition po'))

    # 7. Indefinite preposition je -> 6.13
    if word == 'je' and pos == 'prep':
        refs.append(('6.13', 'Indefinite preposition je'))
    # 5. Corpus-mined derivations whose morphology is segmented into affixes
    #    (tools/promote_lemmas.py) -> section 2, so a reader of ekridi or
    #    kompatindulo can reach the affix table that explains the word.
    #    Scoped to corpus-mined: other layers' segmentation predates the
    #    root-stock check and is not reliable enough to link from.
    morph = entry.get('morphology') or {}
    if entry.get('source') == 'corpus-mined' and \
            (morph.get('prefixes') or morph.get('suffixes')):
        refs.append(('2', 'Morfologio — affix inventory'))
        if any(s.get('m') in PARTICIPLE_MORPHEMES
               for s in morph.get('suffixes') or []):
            refs.append(('2', 'Morfologio — participles'))

    return refs


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    entries = [json.loads(l) for l in open(ENTRIES, encoding='utf-8') if l.strip()]
    changed = 0
    for entry in entries:
        refs = refs_for(entry)
        if refs:
            new = [{'section': s, 'topic': t} for s, t in refs]
            if entry.get('grammar_refs') != new:
                entry['grammar_refs'] = new
                changed += 1
        elif 'grammar_refs' in entry:
            del entry['grammar_refs']
            changed += 1

    print('%d entries linked (%d total)' % (changed, len(entries)))
    if args.dry_run:
        return 0

    tmp = ENTRIES + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as fh:
        for entry in entries:
            fh.write(json.dumps(entry, ensure_ascii=False) + '\n')
    os.replace(tmp, ENTRIES)
    return 0


if __name__ == '__main__':
    sys.exit(main())
