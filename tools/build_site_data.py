#!/usr/bin/env python3
"""Build web/src/data/ JSON bundles for the Esperanto worksite web app.

Reads the repo's artifacts and emits compact JSON the TanStack Start app
serves client-side:

  entries.json      DICT/entries.jsonl, one object per line (array)
  english-index.json  DICT/english-index.jsonl (array)
  sources.json      one record per RAW/ source, parsed from RAW/PROVENANCE.md
                    lines + CORPUS/MANIFEST.tsv (sha/lines/method join) +
                    mining-exclusion flags from tools/mine_lemmas.py

Run from repo root:  python3 tools/build_site_data.py
Regenerate after any DICT/RAW/CORPUS rebuild.
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'web', 'src', 'data')

PROV_LINE = re.compile(
    r'^-+\s+`([^`]+)`\s+—\s+(.*?)(?:\s+—\s+(sha256:[0-9a-f]+))?(?:\s+—\s+(.*?))?$'
)


def parse_provenance():
    """Parse RAW/PROVENANCE.md bullet lines into source records.

    Line shape (whitespace-dashed):
    - `file.txt` — Title — sha256:abcd1234 — Origin (licence) — URL
    Quarantined entries are struck through and noted.
    """
    sources = []
    path = os.path.join(ROOT, 'RAW', 'PROVENANCE.md')
    for line in open(path, encoding='utf-8'):
        line = line.rstrip('\n')
        m = re.match(r'^-+\s+(~~)?`([^`]+)`(?:~~)?\s+—\s+(.*?)(?:~~)?\s*$',
                     line)
        if not m:
            continue
        struck, fname, rest = m.group(1), m.group(2), m.group(3)
        # split the remainder on ' — ' into title / sha / origin / url
        parts = [p.strip() for p in rest.split('—')]
        rec = {'file': fname, 'title': parts[0] if parts else fname}
        for p in parts[1:]:
            if p.startswith('sha256:'):
                rec['sha'] = p[len('sha256:'):]
            elif p.startswith('http'):
                rec['url'] = p
            else:
                rec.setdefault('origin', p)
        if struck:
            rec['quarantined'] = True
            rec.setdefault('origin', 'QUARANTINED — see QUARANTINE/README.md')
        sources.append(rec)
    return sources


def parse_manifest():
    rows = {}
    path = os.path.join(ROOT, 'CORPUS', 'MANIFEST.tsv')
    cols = None
    for line in open(path, encoding='utf-8'):
        parts = line.rstrip('\n').split('\t')
        if cols is None:
            cols = parts
            continue
        row = dict(zip(cols, parts))
        rows[row['source']] = row
    return rows


def mining_exclusions():
    """Import the exclusion sets from tools/mine_lemmas.py (safe: it only
    defines constants and functions at module level; argv is not read)."""
    sys.path.insert(0, os.path.join(ROOT, 'tools'))
    import mine_lemmas
    return {'ENGLISH_HEAVY': set(mine_lemmas.ENGLISH_HEAVY),
            'MULTILINGUAL': set(mine_lemmas.MULTILINGUAL),
            'OCR_POOR': set(mine_lemmas.OCR_POOR)}


def main():
    os.makedirs(OUT, exist_ok=True)

    # entries + english index
    entries = [json.loads(l) for l in open(
        os.path.join(ROOT, 'DICT', 'entries.jsonl'), encoding='utf-8') if l.strip()]
    with open(os.path.join(OUT, 'entries.json'), 'w', encoding='utf-8') as fh:
        json.dump(entries, fh, ensure_ascii=False)
    index = [json.loads(l) for l in open(
        os.path.join(ROOT, 'DICT', 'english-index.jsonl'), encoding='utf-8') if l.strip()]
    with open(os.path.join(OUT, 'english-index.json'), 'w', encoding='utf-8') as fh:
        json.dump(index, fh, ensure_ascii=False)

    # sources
    manifest = parse_manifest()
    excl = mining_exclusions()
    sources = parse_provenance()
    for rec in sources:
        man = manifest.get(rec['file'])
        if man:
            rec['corpus'] = {
                'method': man.get('method'),
                'lines': int(man['out_lines']) if man.get('out_lines') else None,
                'sha': man.get('sha256'),
                'fixes': man.get('fixes'),
            }
        if rec['file'] in excl.get('ENGLISH_HEAVY', set()):
            rec['excluded'] = 'not Esperanto (English/French source)'
        elif rec['file'] in excl.get('MULTILINGUAL', set()):
            rec['excluded'] = 'multilingual tables'
        elif rec['file'] in excl.get('OCR_POOR', set()):
            rec['excluded'] = 'poor OCR / text quality'
    with open(os.path.join(OUT, 'sources.json'), 'w', encoding='utf-8') as fh:
        json.dump(sources, fh, ensure_ascii=False)

    # grammar (raw markdown; rendered client-side by the app)
    grammar = open(os.path.join(ROOT, 'GRAMMAR', 'grammar.md'), encoding='utf-8').read()
    with open(os.path.join(OUT, 'grammar.md'), 'w', encoding='utf-8') as fh:
        fh.write(grammar)

    print('entries: %d' % len(entries))
    print('english index: %d' % len(index))
    print('sources: %d (%d with manifest join)' %
          (len(sources), sum(1 for s in sources if s.get('corpus'))))
    print('grammar.md: %d bytes' % len(grammar))


if __name__ == '__main__':
    sys.exit(main())
