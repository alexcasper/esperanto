#!/usr/bin/env python3
"""Parse the Universala Vortaro (Fundamento de Esperanto, 1905) from the
Akademio de Esperanto's HTML rendering into structured entries.

Entry format in source:  WORD\n FR | EN | DE | RU | PL .
WORD may carry apostrophes (root citation, e.g. abat', unu'nombr') or be a
bare grammatical word/ending (kaj, kiu, a, o, as...).
"""
import re, json, sys, unicodedata

import os
SRC = os.environ.get('UV_HTML', '/tmp/uv.html')
PRE_END = 'oddzielnie.'  # end of the multilingual preface

EPAR = "abcĉdefgĝhĥijĵklmnoprsŝtuŭvz"

def load_text():
    h = open(SRC, encoding='utf-8', errors='replace').read()
    txt = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', h, flags=re.S)
    txt = re.sub(r'<[^>]+>', ' ', txt)
    txt = txt.replace('\u00a0', ' ')
    txt = re.sub(r'[ \t]+', ' ', txt)
    # end body at footer after last root zum'
    i = txt.find("zum'")
    j = txt.find('Akademio :', i)
    body = txt[txt.find(PRE_END) + len(PRE_END):j]
    return body

WORD_RE = re.compile(r'^[abĉdefgĝhĥijĵklmnoprsŝtuŭvzABĈDEFGĜHĤIJĴKLMNOPRSŜTUŬVZ][abĉdefgĝhĥijĵklmnoprsŝtuŭvzABĈDEFGĜHĤIJĴKLMNOPRSŜTUŬVZ\']*$')

def parse_entries(body):
    lines = body.split('\n')
    entries = []
    i = 0
    while i < len(lines):
        ln = lines[i].strip()
        m = WORD_RE.match(ln)
        if m and m.group(0):  # candidate entry word on its own line
            word = ln
            gloss_lines = []
            j = i + 1
            while j < len(lines):
                nxt = lines[j].strip()
                if WORD_RE.match(nxt) and nxt:
                    break
                gloss_lines.append(nxt)
                j += 1
            gloss = ' '.join(x for x in gloss_lines if x)
            gloss = re.sub(r'\s+', ' ', gloss).strip()
            if gloss.count('|') == 4:
                fields = [f.strip() for f in gloss.split('|')]
                # terminal period on last field
                fields[4] = re.sub(r'\s*\.$', '', fields[4]).strip()
                entries.append((word, fields))
            i = j
        else:
            i += 1
    return entries

if __name__ == '__main__':
    body = load_text()
    entries = parse_entries(body)
    print(f"parsed {len(entries)} entries", file=sys.stderr)
    roots = [e for e in entries if "'" in e[0]]
    bares = [e for e in entries if "'" not in e[0]]
    print(f"root-cited: {len(roots)}  bare: {len(bares)}", file=sys.stderr)
    print("BARE WORDS:", ' '.join(w for w, _ in bares), file=sys.stderr)
    with open('/tmp/uv_entries.json', 'w', encoding='utf-8') as f:
        json.dump([{'word': w, 'fr': fs[0], 'en': fs[1], 'de': fs[2], 'ru': fs[3], 'pl': fs[4]}
                   for w, fs in entries], f, ensure_ascii=False, indent=0)
    for w, fs in entries[:3] + entries[-3:]:
        print(w, '||', ' | '.join(fs)[:110])
