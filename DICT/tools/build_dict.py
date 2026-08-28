#!/usr/bin/env python3
"""Build DICT/entries.jsonl from the parsed Universala Vortaro (Fundamento, 1905).

Input:  /tmp/uv_final.json  (word, fr, en, de, ru, pl) — produced by tools
        scrape_uv.py (Akademio de Esperanto HTML → uv_final.json).
Output: DICT/entries.jsonl — one JSON object per line, Esperanto sort order.

POS assignment:
  * grammatical bare words (no apostrophe): curated lookup table.
  * word-building affixes (UV affix entries): prefix/suffix.
  * roots: ending-based citation + gloss heuristics (documented in README).
"""
import json, re, sys

import os
IN = os.environ.get('UV_FINAL', '/tmp/uv_final.json')
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'entries.jsonl')
ALPHA = "abcĉdefgĝhĥijĵklmnoprsŝtuŭvz"
RANK = {c: i for i, c in enumerate(ALPHA)}

def sortkey(w):
    return [RANK.get(c, 99) for c in w.lower()]

# ---------------------------------------------------------------- grammar
ENDINGS = {'a', 'o', 'e', 'i', 'as', 'is', 'os', 'us', 'u', 'j', 'n'}
PRONOUNS = {'mi', 'vi', 'li', 'ŝi', 'ĝi', 'ni', 'ili', 'si', 'oni'}
NUMERALS = {'unu', 'du', 'tri', 'kvar', 'kvin', 'ses', 'sep', 'ok', 'naŭ',
            'dek', 'cent', 'mil'}
PREPS = {'al', 'apud', 'ĉe', 'ĉirkaŭ', 'da', 'de', 'dum', 'el', 'en',
         'ekster', 'ĝis', 'inter', 'je', 'kontraŭ', 'krom', 'kun', 'per',
         'po', 'por', 'post', 'preter', 'pri', 'pro', 'sen', 'sub', 'super',
         'sur', 'tra', 'trans', 'anstataŭ', 'antaŭ', 'malgraŭ', 'kvazaŭ'}
CONJ = {'kaj', 'aŭ', 'ke', 'ĉu', 'se', 'ĉar', 'ol', 'nek'}
CORR_ADJ = {'tia', 'ia', 'ĉia', 'nenia'}
CORR_ADV = {'kie', 'kial', 'kiel', 'kiam', 'tie', 'tial', 'tiel', 'tiam',
            'ĉie', 'ĉial', 'ĉiel', 'ĉiam', 'ie', 'ial', 'iel', 'iam',
            'nenie', 'nenial', 'neniel', 'neniam', 'kie'}
CORR_PRON = {'kiu', 'kio', 'kies', 'kiom', 'tiu', 'tio', 'tiom', 'ĉiu',
             'ĉio', 'ĉiom', 'iu', 'io', 'iom', 'ies', 'neniu', 'nenio',
             'nenies', 'neniom'}
ADVP = {'for', 'tuj', 'nun', 'jam', 'ĵus', 'ankoraŭ', 'plu', 'nur', 'eĉ',
        'preskaŭ', 'plej', 'pli', 'tre', 'tro', 'baldaŭ', 'ambaŭ', 'hieraŭ',
        'hodiaŭ', 'morgaŭ', 'do', 'ja', 'tamen', 'des', 'ju'}
PART = {'ajn', 'ĉi', 'jen', 'ne', 'jes'}
INTERJ = {'adiaŭ', 'ho', 'ha', }

PREFIXES = {'bo': 'in-law relation', 'dis': 'apart, asunder', 'ek': 'sudden start',
            'eks': 'former, ex-', 'fi': 'moral disdain', 'ge': 'both sexes together',
            'mal': 'opposite', 'mis': 'wrongly', 'pra': 'primeval, great-',
            're': 'again, back'}
SUFFIXES = {'aĉ': 'pejorative', 'aĵ': 'concrete thing', 'ad': 'continued action',
            'an': 'member', 'ar': 'collective', 'ĉj': 'male diminutive (names)',
            'ebl': 'possible, -able', 'ec': 'abstract quality', 'eg': 'augmentative',
            'ej': 'place', 'em': 'tendency', 'end': 'obligatory',
            'estr': 'chief', 'et': 'diminutive', 'id': 'offspring',
            'ig': 'causative (make)', 'iĝ': 'middle/inchoative (become)',
            'il': 'instrument', 'in': 'female', 'ind': 'worth, -worthy',
            'ist': 'professional', 'nj': 'female diminutive (names)',
            'obl': 'multiplicative (×)', 'on': 'fractional',
            'op': 'grouping', 'uj': 'container/country/plant',
            'ul': 'person with trait', 'um': 'indefinite suffix',
            'ant': 'active participle (being)', 'at': 'passive participle (being done)',
            'int': 'active participle (having)', 'it': 'passive participle (having been)',
            'ont': 'active participle (going to)', 'ot': 'passive participle (about to be)'}

AFFIX_SET = set(PREFIXES) | set(SUFFIXES)

# roots whose gloss hides adjective-ness (EN lacks -ous/-ful, FR not -eux)
ADJ_OVERRIDES = {'bel', 'bon', 'malbon', 'grand', 'long', 'alt', 'rapid',
                 'facil', 'malfacil', 'fort', 'malfort', 'ĝust', 'fals',
                 'san', 'malsan', 'varm', 'malvarm', 'blank', 'nigr', 'ruĝ',
                 'flav', 'verd', 'blu', 'griz', 'brun', 'glat', 'mol', 'dur',
                 'dik', 'simpl', 'plen', 'malplen', 'komplet', 'cert',
                 'official', 'natur', 'liber', 'egal', 'simil', 'diferenc',
                 'konstant', 'sentim', 'kuraĝ'}

VERB_FR = re.compile(r'(er|ir|oir|re)$')
ADJ_DE = re.compile(r'(isch|lich|haft|los|bar|ig)$', re.I)
ADJ_FR = re.compile(r'(eux|euse|ible|able)$', re.I)
ADJ_EN = re.compile(r'(ous|ful|ish|able|ible|y|al|ic|ive|ent)$')

def classify_bare(w):
    if w in ENDINGS: return 'ending'
    if w == 'la': return 'art'
    if w in PRONOUNS: return 'pron'
    if w in NUMERALS: return 'num'
    if w in PREPS: return 'prep'
    if w in CONJ: return 'conj'
    if w in CORR_ADJ: return 'adj'
    if w in CORR_ADV: return 'adv'
    if w in CORR_PRON: return 'pron'
    if w in ADVP: return 'adv'
    if w in PART: return 'particle'
    if w in INTERJ: return 'interj'
    return 'particle'

def pos_for_root(stem, fr, de, en):
    if stem in ADJ_OVERRIDES:
        return 'adj'
    en = en or ''
    fr = (fr or '').strip().lower()
    de_l = (de or '').strip().lower()
    de_inf = de_l.endswith('en') and len(de_l) > 3
    fr_inf = fr.endswith(('er', 'ir', 'oir')) or (fr.endswith('re') and len(fr) > 3)
    if en.startswith('to '):
        return 'verb'
    if en and ADJ_EN.search(en.split(',')[0]):
        return 'adj'
    if fr and ADJ_FR.search(fr) and en and ADJ_EN.search(en.split()[-1]):
        return 'adj'
    if fr_inf and de_inf:
        return 'verb'
    if fr.endswith(('oir', 'ir')) and len(fr) > 3:
        return 'verb'
    if fr.endswith('er') and de_inf and not ADJ_DE.search(de_l):
        return 'verb'
    return 'noun'

ENDING_FOR = {'noun': 'o', 'verb': 'i', 'adj': 'a'}

def segment(stem, roots):
    """Split stem into affixes + core stem if every remainder is a known root.
    Returns (prefixes, core, suffixes) or None."""
    pre = []
    s = stem
    changed = True
    while changed:
        changed = False
        for p in sorted(PREFIXES, key=len, reverse=True):
            if s.startswith(p) and s[len(p):] in roots:
                pre.append(p); s = s[len(p):]; changed = True
                break
    suf = []
    changed = True
    while changed:
        changed = False
        for p in sorted(SUFFIXES, key=len, reverse=True):
            if s.endswith(p) and s[:-len(p)] in roots and len(p) >= 2:
                suf.insert(0, p); s = s[:-len(p)]; changed = True
                break
    if not pre and not suf:
        return None
    if s in roots or not s:
        return (pre, s, suf)
    return None

def build():
    raw = json.load(open(IN, encoding='utf-8'))
    # root set (apostrophe-stripped, lowercased) for morphology validation
    root_set = set()
    for e in raw:
        w = e['word']
        if "'" in w:
            root_set.add(w.replace("'", '').lower())
    entries = []
    stats = {'affix': 0, 'bare': 0, 'root': 0, 'compound': 0}
    for e in raw:
        w = e['word']
        base = {
            'gloss_en': e['en'].strip(),
            'gloss_fr': e['fr'].strip(),
            'source': 'Fundamento/UV-1905',
        }
        if "'" not in w:
            pos = classify_bare(w)
            stats['bare'] += 1
            entries.append({'word': w, 'pos': pos, **base})
            continue
        stem = w.replace("'", '')
        parts = w.split("'")
        parts = [p for p in parts if p]
        core = parts[0] if len(parts) == 1 else parts
        is_affix = stem.lower() in AFFIX_SET and len(parts) == 1
        if is_affix:
            pos = 'prefix' if stem.lower() in PREFIXES else 'suffix'
            stats['affix'] += 1
            entries.append({
                'word': stem.lower(), 'pos': pos, 'root': stem.lower(),
                'gloss_en': base['gloss_en'] or (
                    PREFIXES.get(stem.lower()) or SUFFIXES.get(stem.lower(), '')),
                **{k: v for k, v in base.items() if k != 'gloss_en'}})
            continue
        if stem.lower() in NUMERALS:
            entries.append({'word': stem.lower(), 'pos': 'num', **base})
            continue
        pos = pos_for_root(stem.lower(), e['fr'], e['de'], e['en'])
        word = stem + ENDING_FOR.get(pos, 'o')
        ent = {'word': word, 'pos': pos, 'root': stem.lower(), **base}
        seg = segment(stem.lower(), root_set)
        if seg:
            pre, core_s, suf = seg
            morph = {}
            if pre:
                morph['prefixes'] = [{'m': p, 'gloss': PREFIXES[p]} for p in pre]
            morph['stem'] = core_s
            if suf:
                morph['suffixes'] = [{'m': p, 'gloss': SUFFIXES[p]} for p in suf]
            morph['ending'] = ENDING_FOR.get(pos, 'o')
            ent['morphology'] = morph
            stats['compound' if (pre or suf) else 'root'] += 1
        else:
            ent['morphology'] = {'stem': stem.lower(),
                                 'ending': ENDING_FOR.get(pos, 'o')}
            stats['root'] += 1
        entries.append(ent)
    entries.sort(key=lambda x: sortkey(x['word']))
    with open(OUT, 'w', encoding='utf-8') as f:
        for ent in entries:
            f.write(json.dumps(ent, ensure_ascii=False) + '\n')
    print(f"wrote {len(entries)} entries → {OUT}")
    print("stats:", stats)
    from collections import Counter
    print("pos dist:", dict(Counter(e['pos'] for e in entries)))

if __name__ == '__main__':
    build()
