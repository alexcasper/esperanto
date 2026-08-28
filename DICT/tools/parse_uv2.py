#!/usr/bin/env python3
"""Sequential-cursor parser for the Universala Vortaro (Fundamento 1905)."""
import re, json, sys

import os
SRC = os.environ.get('UV_HTML', '/tmp/uv.html')
PRE_END = 'oddzielnie.'
L = "abcĉdefgĝhĥijĵklmnoprsŝtuŭvz"
WORD = f"[{L}{L.upper()}]+(?:'[{L}{L.upper()}]+)*'?"
GLOSS = (r"\s*([^|]{1,300}?)\s*\|\s*([^|]{1,300}?)\s*\|\s*([^|]{1,300}?)\s*\|"
         r"\s*([^|]{1,300}?)\s*\|\s*(.{1,350}?)\s*\.\s*(?=[A-Za-zĉĝĥĵŝŭĈĜĤĴŜŬ]|$)")
WORD_RE = re.compile(WORD)
GLOSS_RE = re.compile(GLOSS)

def load_flat():
    h = open(SRC, encoding='utf-8', errors='replace').read()
    txt = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', h, flags=re.S)
    txt = re.sub(r'<[^>]+>', ' ', txt).replace('\u00a0', ' ')
    txt = re.sub(r'\s+', ' ', txt)
    i = txt.find("zum'")
    j = txt.find('Akademio :', i)
    return txt[txt.find(PRE_END) + len(PRE_END):j]

def parse():
    t = load_flat()
    pos = 0; entries = []
    while pos < len(t):
        m = WORD_RE.search(t, pos)
        if not m: break
        w = m.group(0); start = m.start()
        # lookback: real entries follow '.', '»', a section-header letter,
        # or text start — never a plain letter (mid-gloss capture)
        k = start - 1
        while k >= 0 and t[k] == ' ': k -= 1
        prev = t[k] if k >= 0 else ''
        follows_header = k >= 1 and t[k].isupper() and t[k - 1] == ' '
        ok_start = prev in ('', '.', '»') or follows_header
        g = GLOSS_RE.match(t, m.end()) if ok_start else None
        if g and w:
            keep = True
            if len(w) == 1 and w.isupper():
                m2 = WORD_RE.match(t, g.end())
                if m2 and GLOSS_RE.match(t, m2.end()):
                    keep = False
            if keep:
                entries.append({'word': w,
                                'fr': g.group(1), 'en': g.group(2),
                                'de': g.group(3), 'ru': g.group(4), 'pl': g.group(5)})
                pos = g.end(); continue
        pos = m.end()
    return entries

if __name__ == '__main__':
    E = parse()
    roots = [e for e in E if "'" in e['word']]
    bares = [e for e in E if "'" not in e['word']]
    print(f"total {len(E)}  roots {len(roots)}  bare {len(bares)}", file=sys.stderr)
    json.dump(E, open('/tmp/uv_entries.json', 'w', encoding='utf-8'),
              ensure_ascii=False, indent=0)
    print('BARES:', ' '.join(e['word'] for e in bares), file=sys.stderr)
    # sanity spot-checks
    have = {e['word'] for e in E}
    for probe in ("abat'", "zum'", "bel'", "frat'in'", "unu'nombr'", "zorg'ant'",
                  "la", "kaj", "kiu", "ĉi", "naŭ", "ŝi", "oni", "plej", "je",
                  "a", "o", "i", "as", "in'", "ej'", "mal'", "boj'", "hund'"):
        if probe not in have: print('MISSING:', probe, file=sys.stderr)
    # uppercase / weird words
    print('UPPERCASE:', [e['word'] for e in E if e['word'][0].isupper()][:20], file=sys.stderr)
