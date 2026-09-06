#!/usr/bin/env python3
"""Restore ReVo headwords the dictionary is missing, and say why they went.

Usage: python3 tools/restore_revo_gaps.py --cache DIR [--apply] [--audit]

`ANALYSIS/verbs.md` found 1033 lemmas the corpus conjugates while the
dictionary records only the root's noun or adjective — `eniri` 2628 tokens,
`foriri` 2153, `forlasi` 1602. The bead treated that as review work. It is
mostly not: ReVo lists these, and the merge dropped them for reasons that are
recoverable.

Measured over 970 cached ReVo articles, the causes separate cleanly:

  no English gloss   The dominant one by far — 220 of the 229 missing `-i`
                     headwords. DICT/tools/merge_revo.py skips any derivation
                     ReVo has not translated into English (`skip_noen`), and
                     ReVo often leaves a transparent derivation untranslated
                     precisely BECAUSE it is transparent: reordigi, doloriĝi,
                     ekkompati, foruzi. Project-wide that rule dropped 11793
                     of 30648 derivation heads. Changing it is a policy
                     decision about whether a derivation earns an entry
                     without a gloss, so this tool does NOT touch them.

  simply absent      56 headwords ReVo DOES gloss in English and the
                     dictionary lacks anyway. Nothing decides against them.
                     These are what this tool restores.

  a self-referential verdict   3 of those 56 were mined and then rejected by a
                     reviewer as an `inflection` OF THEMSELVES: `fiksi` noted
                     "past passive participle of fiksi", `forlasi` noted
                     "infinitive of forlasi, judged separately in this shard",
                     `rediri` noted "past tense of rediri". The same mistake
                     that hid `povi` behind `povo` and `pova` (see
                     tools/repair_uv_verbs.py). The dictionary holds `fiksa`,
                     `fikse`, `fikseco` and `fiksiĝi` but not `fiksi`;
                     `forlasebla` and `forlaso` but not `forlasi`.

Presence is tested space- and case-insensitively, which is not fussiness:
merge_revo.py squashes whitespace out of a headword, so ReVo's
`Aleksandro la Granda` arrives as `aleksandrolagranda`, and a naive check
reports it missing and re-adds the damaged form beside the repaired one.
`tools/repair_revo_headwords.py` restored those spaces; 53 of the 59
candidates on the first pass were that same defect coming back round.

Entries are built exactly as DICT/tools/merge_revo.py builds them — same POS
from the ending, same source tag from `<ofc>` — so a later full re-merge
against the complete ReVo source produces the same rows and skips these as
duplicates rather than conflicting with them.
"""
import argparse
import collections
import importlib.util
import json
import os
import sys
from pathlib import Path

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENTRIES = os.path.join(ROOT, 'DICT', 'entries.jsonl')
VERDICTS = os.path.join(ROOT, 'DICT', 'verdicts.jsonl')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import promote_lemmas                                     # noqa: E402
import repair_revo_headwords                              # noqa: E402
import xml.etree.ElementTree as ET                        # noqa: E402
import re                                                 # noqa: E402

# A headword is restorable only if it is genuinely ONE word. merge_revo.py
# squashes whitespace, so a multi-word term arrives welded together and cannot
# be told apart from a real compound by looking at its output — `propozicia
# kalkulo` becomes `propoziciakalkulo`, and one candidate arrived as
# `turniĝantapontoturneblaopiv1`, two variants and a source marker run into
# one string. So the ReVo <kap> is re-rendered WITH its spaces and anything
# containing one is left for a full re-merge to do properly.
PLURAL = re.compile(r'(oj|aj|ojn|ajn)$')


def single_word(kap, rad):
    rendered = repair_revo_headwords.render(kap, rad).strip()
    rendered = rendered.split(',')[0].strip()
    if not rendered or ' ' in rendered or any(c.isdigit() for c in rendered):
        return None
    # A plural is an inflected form, not a citation form: ReVo lists `fratoj`
    # under frat, and `frato` is the headword a dictionary carries.
    if PLURAL.search(rendered):
        return None
    # merge_revo.py lowercases every headword, so restoring a proper name
    # through it would file `Vincento` as `vincento`. Names need the
    # capitalisation the full re-merge and repair pass give them.
    if rendered[:1].isupper():
        return None
    return rendered


def merge_module():
    """The merge's own parser, so restored rows match a future re-merge."""
    path = os.path.join(ROOT, 'DICT', 'tools', 'merge_revo.py')
    spec = importlib.util.spec_from_file_location('merge_revo', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def squash(word):
    """Space- and case-insensitive key, matching repair_revo_headwords."""
    return ''.join(word.lower().split())


def survey(cache, merge, present):
    """Every ReVo head the dictionary lacks, with the reason it is missing."""
    missing, untranslated, unreadable, mangled = [], 0, 0, 0
    for name in sorted(os.listdir(cache)):
        if not name.endswith('.xml'):
            continue
        path = os.path.join(cache, name)
        try:
            heads = merge.parse_article(Path(path))
            article = ET.fromstring(re.sub(
                r'<!DOCTYPE.*?>', '',
                repair_revo_headwords.strip_entities(
                    open(path, encoding='utf-8').read()), flags=re.S))
        except Exception:                                 # noqa: BLE001
            unreadable += 1
            continue
        rad = (article.findtext('.//rad') or '').strip()
        spaced = set()
        for drv in article.findall('.//drv'):
            kap = drv.find('kap')
            if kap is not None:
                word = single_word(kap, rad)
                if word:
                    spaced.add(squash(word))
        for head in heads:
            word = head['word']
            # A comma in a headword is the mis-merge repair_headwords.py
            # already handles; leave those alone.
            if not word or ',' in word or squash(word) in present:
                continue
            if squash(word) not in spaced:
                mangled += 1
                continue
            if not head['gloss_en']:
                untranslated += 1
                continue
            missing.append(head)
    return missing, untranslated, unreadable, mangled


def build(head, merge):
    source = 'ReVo'
    ofc = head['ofc']
    if ofc.isdigit() and len(ofc) <= 2:
        source = 'ReVo/OA-%s' % ofc
    elif ofc == '*':
        source = 'ReVo/UV-*'
    entry = {
        'word': head['word'],
        'pos': merge.POS.get(head['tail'], 'noun'),
        'gloss_en': head['gloss_en'],
        'root': head['rad'],
        'source': source,
    }
    if head['gloss_fr']:
        entry['gloss_fr'] = head['gloss_fr']
    return entry


def verdicts():
    out = {}
    if not os.path.exists(VERDICTS):
        return out
    with open(VERDICTS, encoding='utf-8') as fh:
        for line in fh:
            if line.strip():
                record = json.loads(line)
                out[record['lemma'].lower()] = record
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--cache', required=True,
                        help='directory of fetched ReVo article XML')
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--audit', action='store_true')
    args = parser.parse_args()

    merge = merge_module()
    entries = [json.loads(line) for line in open(ENTRIES, encoding='utf-8')
               if line.strip()]
    present = {squash(e['word']) for e in entries}
    missing, untranslated, unreadable, mangled = survey(
        args.cache, merge, present)

    judged = verdicts()
    by_verdict = collections.Counter(
        (judged.get(h['word'].lower()) or {}).get('verdict', 'none')
        for h in missing)

    print('%d articles unreadable in the cache' % unreadable)
    print('%d ReVo heads absent because ReVo gives no English gloss '
          '(policy, untouched)' % untranslated)
    print('%d absent but not a single word — the whitespace defect; left for '
          'a full re-merge' % mangled)
    print('%d ReVo heads absent with an English gloss — restorable\n'
          % len(missing))
    for verdict, count in by_verdict.most_common():
        print('   reviewer verdict %-14s %d' % (verdict, count))

    if args.audit:
        print('\nthe restorable heads:')
        for head in sorted(missing, key=lambda h: h['word']):
            record = judged.get(head['word'].lower())
            note = ''
            if record:
                note = '   [%s: %s]' % (record.get('verdict'),
                                        record.get('note', '')[:44])
            print('   %-20s %-9s %r%s'
                  % (head['word'], merge.POS.get(head['tail'], 'noun'),
                     head['gloss_en'][:34], note))
        return 0

    if not args.apply:
        print('\n--dry-run by default. Re-run with --apply to write.')
        return 0

    additions = [build(head, merge) for head in missing]
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
