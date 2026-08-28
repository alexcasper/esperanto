#!/usr/bin/env python3
"""Merge: A = line parser (parse_uv.py), B = sequential (parse_uv2.py).
B only contributes apostrophe-cited roots not already in A, plus whitelisted
bare grammatical words that A missed (dek, cent, mil, ju, des, la)."""
import json, re, sys
sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))
import importlib
import parse_uv, parse_uv2
importlib.reload(parse_uv); importlib.reload(parse_uv2)

A = parse_uv.parse_entries(parse_uv.load_text())
# A quirks: 'L' bogus word carried the article entry; 'M' bogus → drop
A = [e for e in A if e[0] != 'M']
A = [('la', fs) if w == 'L' else (w, fs) for w, fs in A]

B = parse_uv2.parse()
a_words = {w for w, _ in A}

_OK_PUNCT = set(" '’()0-9,;:/ .?‖-―–—\"!")
def sane_en(en):
    if len(en) < 2 or len(en) > 120: return False
    for ch in en:
        if ch in _OK_PUNCT: continue
        if 'a' <= ch <= 'z' or ch in 'àáâäèéêëìíîïòóôöùúûüçñßæœåøđł': continue
        return False
    return True

rec = []
seen = set()
for e in B:
    w = e['word']
    if "'" in w and w not in a_words and w not in seen and sane_en(e['en']):
        seen.add(w); rec.append((w, [e['fr'], e['en'], e['de'], e['ru'], e['pl']]))

bare_extra = {'dek', 'cent', 'mil', 'ju', 'des'}
for w in bare_extra:
    if w not in a_words:
        for e in B:
            if e['word'] == w and sane_en(e['en']):
                A.append((w, [e['fr'], e['en'], e['de'], e['ru'], e['pl']])); break

# Pass C: overlap scan — entries are anchored at ". WORD" starts; catches
# entries the sequential parse skipped (cascade consumption).
from parse_uv2 import load_flat, WORD_RE, GLOSS_RE
t = load_flat()
START_RE = re.compile(r"[.\»]\s(" + WORD_RE.pattern + ")")
C = []
for m in START_RE.finditer(t):
    w = m.group(1)
    g = GLOSS_RE.match(t, m.end())
    if g and sane_en(g.group(2)):
            C.append((w, [g.group(1), g.group(2), g.group(3), g.group(4), g.group(5)]))
bare_ok = {w for w, _ in A} | bare_extra
C = [e for e in C if ("'" in e[0]) or (e[0] in bare_ok)]

final = A + rec + [e for e in C if e[0] not in a_words and e[0] not in seen]
words = {}
for w, fs in final:
    words.setdefault(w, fs)
out = [{'word': w, 'fr': f[0], 'en': f[1], 'de': f[2], 'ru': f[3], 'pl': f[4]}
       for w, f in words.items()]
json.dump(out, open('/tmp/uv_final.json', 'w', encoding='utf-8'),
          ensure_ascii=False, indent=0)
roots = [e for e in out if "'" in e['word']]
bares = [e for e in out if "'" not in e['word']]
print(f"FINAL {len(out)}  roots {len(roots)}  bare {len(bares)}")
print('BARES:', ' '.join(sorted(e['word'] for e in bares)))
have = {e['word'] for e in out}
miss = [p for p in ("abat'", "zum'", "bel'", "frat'in'", "unu'nombr'", "zorg'ant'",
                    "hund'", "in'", "ej'", "mal'", "boj'", "cent", "dek", "mil",
                    "la", "kaj", "kiu", "naŭ", "ŝi", "plej", "a", "o", "as")
        if p not in have]
print('MISSING:', miss if miss else 'none ✓')
# spot-check recovered entries
for p in ("frat'in'", "unu'nombr'", "zorg'ant'", "cent"):
    e = words.get(p)
    print(p, '→', (e[1] if e else None))
