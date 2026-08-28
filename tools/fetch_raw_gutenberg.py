#!/usr/bin/env python3
"""Fetch curated Esperanto texts from Project Gutenberg into RAW/.

Usage: python3 tools/fetch_raw_gutenberg.py [--dry-run]

Gutenberg carries 145 Esperanto titles; RAW/ batch 1 took 10 and the corpus
already holds 79 Vikifontaro pages, most of them translations. This batch is
therefore selected, not exhaustive, and weighted towards what the DICT and
GRAMMAR passes are short of:

  canon       Zamenhof's own Esperanto and the Fundamento-era reference texts.
  grammar     Metalinguistic works — grammars, courses, a syntax study. These
              are largely English prose *about* Esperanto, so they are gold for
              rule citations and noise for lemma mining; the batch notes in
              RAW/PROVENANCE.md say which ones.
  originala   Works written in Esperanto rather than translated into it, which
              is the attested native usage the dictionary needs.
  movado      Movement prose and periodicals — original journalism, congress
              reports, biography.

Deliberately skipped: the 27 bilingual issues of *The Esperantist*, and the
translations of foreign classics (11 Ibsen plays, Goethe, Shakespeare, Poe,
the Grobe translations), since RAW/ is already translation-heavy.

Every candidate is gated on Gutenberg's own copyright status — anything not
public domain is reported and skipped, never written — and on a sha256
exact-copy check against the files already in RAW/.
"""
import hashlib
import os
import re
import subprocess
import sys
import time
import html

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, 'RAW')
PROVENANCE = os.path.join(RAW, 'PROVENANCE.md')
BIBREC = 'https://www.gutenberg.org/ebooks/%s'
PLAINTEXT = 'https://www.gutenberg.org/ebooks/%s.txt.utf-8'

CANDIDATES = [
    # (ebook id, category)
    ('8224', 'canon'),       # Fundamenta Krestomatio
    ('11307', 'canon'),      # El la Biblio (Psalmaro, Sentencoj, Predikanto)
    ('7787', 'grammar'),     # A Complete Grammar of Esperanto — Reed
    ('8177', 'grammar'),     # The Esperanto Teacher — Fryer
    ('47855', 'grammar'),    # Esperanta sintakso — Fruictier
    ('24525', 'grammar'),    # Karlo: Facila Legolibro — Privat
    ('74344', 'originala'),  # Perdita kaj retrovita — Boirac
    ('55954', 'originala'),  # Stranga heredaĵo — Luyken
    ('64579', 'originala'),  # Idoj de Orfeo — Bulthuis
    ('63064', 'originala'),  # Salome — Bulthuis
    ('69123', 'originala'),  # Saltego trans jarmiloj — Forge
    ('42774', 'originala'),  # Mondo kaj koro — Kalocsay
    ('52111', 'originala'),  # Ama Stelaro — Baena
    ('62118', 'originala'),  # Legendoj — Kuhl
    ('48896', 'originala'),  # Verdaj fajreroj — Frenkel
    ('32035', 'originala'),  # Laŭroj — La Revuo prize anthology
    ('47259', 'originala'),  # La Vendreda Klubo — Dietterle
    ('76273', 'originala'),  # Por kaj kontraŭ Esperanto — Vallienne
    ('61581', 'originala'),  # La kialo de la vivo
    ('61579', 'originala'),  # Al mia fratineto — Muller
    ('63105', 'originala'),  # Tri Noveloj — Fiŝer
    ('26359', 'movado'),     # Vivo de Zamenhof — Privat
    ('26959', 'movado'),     # La Lastaj Tagoj de D-ro Zamenhof — Jung
    ('57184', 'movado'),     # Dokumentoj de Esperanto — Möbusz
    ('55574', 'movado'),     # Raporto pri la oka kongreso — Katryn
    ('42028', 'movado'),     # En Rusujo per Esperanto — Rivier
    ('25311', 'movado'),     # El la vivo de esperantistoj — Stankiević
    ('52062', 'movado'),     # Literatura Mondo 1922/1
    ('52063', 'movado'),     # Literatura Mondo 1922/2
    ('52064', 'movado'),     # Literatura Mondo 1922/3
]

PG_MARKERS = (re.compile(r'\*\*\*\s*START OF TH[EI]S? PROJECT GUTENBERG'),
              re.compile(r'\*\*\*\s*END OF TH[EI]S? PROJECT GUTENBERG'
                         r"|^End of (?:the )?Project Gutenberg('s)?\b", re.M))


DELAY = 2.0     # Gutenberg resets connections on rapid sequential requests
RETRIES = 4


def fetch(url):
    last = ''
    for attempt in range(RETRIES):
        time.sleep(DELAY * (2 ** attempt - 1) + (DELAY if attempt else 0))
        out = subprocess.run(['curl', '-sSL', '-m', '90', url],
                             capture_output=True)
        if out.returncode == 0 and out.stdout:
            return out.stdout
        last = out.stderr.decode()[:160] or 'empty response'
        print('    retry %d/%d %s (%s)' % (attempt + 1, RETRIES, url, last),
              file=sys.stderr)
    raise IOError('%s: %s' % (url, last))


def untag(fragment):
    return ' '.join(html.unescape(re.sub(r'<[^>]+>', ' ', fragment)).split())


def bibrec(eid):
    """Title, author and Gutenberg's copyright status for one ebook."""
    page = fetch(BIBREC % eid).decode('utf-8', 'replace')
    rights = re.search(r'rights">([^<]+)', page)
    title = re.search(r'itemprop="headline">(.*?)</td>', page, re.S)
    author = re.search(r'itemprop="creator">(.*?)</a>', page, re.S)
    return {
        'title': untag(title.group(1)) if title else '(unknown title)',
        'author': untag(author.group(1)) if author else '(unknown author)',
        'rights': untag(rights.group(1)) if rights else '(rights not stated)',
    }


def existing_hashes():
    hashes = {}
    for name in os.listdir(RAW):
        if not name.endswith('.txt'):
            continue
        with open(os.path.join(RAW, name), 'rb') as fh:
            hashes[hashlib.sha256(fh.read()).hexdigest()] = name
    return hashes


def main():
    dry_run = '--dry-run' in sys.argv
    hashes = existing_hashes()
    added, skipped = [], []

    for eid, category in CANDIDATES:
        name = 'pg-%s.txt' % eid
        target = os.path.join(RAW, name)
        if os.path.exists(target):
            skipped.append((name, 'already in RAW/'))
            continue

        meta = bibrec(eid)
        if 'public domain' not in meta['rights'].lower():
            skipped.append((name, 'rights: %s' % meta['rights']))
            continue

        body = fetch(PLAINTEXT % eid)
        text = body.decode('utf-8', 'replace')
        digest = hashlib.sha256(body).hexdigest()
        if digest in hashes:
            skipped.append((name, 'exact copy of %s' % hashes[digest]))
            continue
        if not all(marker.search(text) for marker in PG_MARKERS):
            skipped.append((name, 'no Gutenberg START/END markers'))
            continue

        if not dry_run:
            with open(target, 'wb') as fh:
                fh.write(body)
        hashes[digest] = name
        added.append({'file': name, 'id': eid, 'category': category,
                      'sha': digest[:12], 'bytes': len(body), **meta})

    if added and not dry_run:
        with open(PROVENANCE, 'a', encoding='utf-8') as fh:
            fh.write('\n## Batch 2 — Project Gutenberg, curated\n\n')
            fh.write('Selected by category (see tools/fetch_raw_gutenberg.py '
                     'for the criteria); `grammar` sources are largely English '
                     'prose about Esperanto and should be filtered out of '
                     'lemma mining.\n\n')
            for rec in added:
                fh.write('- `%(file)s` — %(title)s — %(author)s — '
                         '%(category)s — sha256:%(sha)s — Project Gutenberg '
                         '(%(rights)s) — https://www.gutenberg.org/ebooks/'
                         '%(id)s\n' % rec)

    print('%s%d added, %d skipped'
          % ('[dry run] ' if dry_run else '', len(added), len(skipped)))
    for rec in added:
        print('  + %-14s %-10s %7d B  %s'
              % (rec['file'], rec['category'], rec['bytes'], rec['title'][:48]))
    for name, why in skipped:
        print('  - %-14s %s' % (name, why))
    return 0


if __name__ == '__main__':
    sys.exit(main())
