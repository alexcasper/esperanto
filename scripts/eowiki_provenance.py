#!/usr/bin/env python3
"""Generate the per-article provenance index for the Vikipedio batch
(esp-4g8): RAW/PROVENANCE-eowiki-20261001.tsv with one line per wp-*.txt
file — title, sha256 (12-hex, the PROVENANCE.md convention), source URL.
Attribution chain for the CC BY-SA 4.0 licence: PROVENANCE.md block points
here; every article is traceable to its dump and its live URL."""
import hashlib
import os
import sys

RAW = sys.argv[1] if len(sys.argv) > 1 else 'RAW'
OUT = os.path.join(RAW, 'PROVENANCE-eowiki-20261001.tsv')

rows = []
for name in sorted(os.listdir(RAW)):
    if not (name.startswith('wp-') and name.endswith('.txt')):
        continue
    title = name[3:-4].replace('_', ' ')
    # Underscore-flattened slashes restored for the URL form.
    url_title = name[3:-4]
    with open(os.path.join(RAW, name), 'rb') as fh:
        h = hashlib.sha256(fh.read()).hexdigest()[:12]
    rows.append((name, title, h,
                 'https://eo.wikipedia.org/wiki/' + url_title))

with open(OUT, 'w', encoding='utf-8') as fh:
    fh.write('file\ttitle\tsha256\turl\n')
    for r in rows:
        fh.write('\t'.join(r) + '\n')
print('wrote %s (%d articles)' % (OUT, len(rows)))
