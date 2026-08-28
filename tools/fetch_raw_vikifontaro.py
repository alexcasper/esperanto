#!/usr/bin/env python3
"""Extract proofread scanned books from the eo.wikisource dump into RAW/.

Usage: python3 tools/fetch_raw_vikifontaro.py --dump PATH [--list] [--dry-run]

Why the dump and not the API: Vikifontaro has 12332 main-namespace pages, and
RAW/ batch 1 took 79 of them by scraping rendered HTML one page at a time. The
API rate-limits a crawl that size (it cut us off after 24 requests) and the
rendered HTML drags in page furniture that normalize_corpus.py then strips back
out. One 15 MB dump request replaces the whole crawl.

Why the Paĝo: namespace: main-namespace pages are mostly ProofreadPage
transclusion stubs ({{paĝokapo}} plus <pages index=... />), averaging 525
bytes. The text itself lives in ns=104 — 22214 pages across 666 scanned books.

Why this matters for quality: these are page scans, and the OCR behind an
unproofread scan is bad enough to invent lemmas — the same problem that makes
the archive.org Esperanto scans unusable. But Wikisource records a
<pagequality level="N"> per page, where 3 is proofread by a human and 4 is
validated by a second one. That metadata is the gate archive.org lacks, so we
take level 3+ pages only and report what each book contributed.

Selection is by criterion, not a hand-list: a book qualifies on published year
(<= 1929, from the index filename, keeping this to texts old enough to be
clearly out of copyright) and on having at least MIN_PAGES proofread pages.
Run --list to see every candidate and why it was taken or left.
"""
import bz2
import collections
import hashlib
import os
import re
import sys
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, 'RAW')
PROVENANCE = os.path.join(RAW, 'PROVENANCE.md')
DUMP_URL = ('https://dumps.wikimedia.org/eowikisource/latest/'
            'eowikisource-latest-pages-articles.xml.bz2')
INDEX_URL = 'https://eo.wikisource.org/wiki/Indekso:%s'

MIN_QUALITY = 3      # 3 = proofread by a human, 4 = validated by a second
MAX_YEAR = 1929      # published no later than this
MIN_PAGES = 100      # enough proofread pages to be worth a corpus file

# Already held in full from Project Gutenberg or the batch-1 wsrc- scrape; a
# second edition would double every lemma count without adding vocabulary.
EXCLUDE = ['Fundamenta Krestomatio',   # pg-8224
           'Vivo de Zamenhof',         # pg-26359
           'Alicio en Mirland',        # pg-17482
           'Fundamento de Esperanto']  # wsrc-Fundamento_de_Esperanto_*

QUALITY = re.compile(r'<pagequality level="(\d)"')
YEAR = re.compile(r'\b(1[6-9]\d\d)\b')
NOINCLUDE = re.compile(r'<noinclude>.*?</noinclude>', re.S)
NOINCLUDE_OPEN = re.compile(r'<noinclude>.*$', re.S)
COMMENT = re.compile(r'<!--.*?-->', re.S)
REF = re.compile(r'<ref[^>]*/>|<ref[^>]*>.*?</ref>', re.S | re.I)
TEMPLATE = re.compile(r'\{\{([^{}]*)\}\}')
TABLE = re.compile(r'\{\|.*?\|\}', re.S)
FILE_LINK = re.compile(r'\[\[\s*(?:File|Image|Dosiero|Bildo)\s*:[^\]]*\]\]',
                       re.I | re.S)
LINK_PIPED = re.compile(r'\[\[[^\]|]*\|([^\]]*)\]\]')
LINK_PLAIN = re.compile(r'\[\[([^\]|]*)\]\]')
EXTLINK = re.compile(r'\[(?:https?|//)\S+ ([^\]]*)\]')
TAG = re.compile(r'<[^>]+>')
QUOTES = re.compile(r"'{2,5}")
HEADING = re.compile(r'^\s*=+\s*(.*?)\s*=+\s*$', re.M)
PAGENUM = re.compile(r'^\s*\d{1,4}\s*$', re.M)


# Templates that are page furniture: nothing inside them is body text.
TEMPLATE_DROP = {'rh', 'runningheader', 'tab', '---', 'nop', 'pagequality',
                 'reflist', 'ppoem-close'}
# Templates whose *last* argument carries the text: {{lang|eo|vorto}},
# {{VdE|Buko|buko}} cross-references, {{SIC|as-printed|corrected}} where we
# prefer the correction so a known misprint does not enter DICT as a lemma.
TEMPLATE_LAST_ARG = {'lang', 'sic', 'vde', 'vdk', 'vdf'}
FORMAT_ARG = re.compile(r'^(?:\d+(?:px|%|em)?|[clrjm]|left|right|center|'
                        r'small|big)$', re.I)


def resolve_template(match):
    """Keep the text a template wraps, drop the formatting around it.

    Deleting templates wholesale loses real words: eo.wikisource wraps
    emphasis, dictionary entries and language marks in them, so
    'trad. el {{lang|pl|Prus}}' would silently become 'trad. el'.
    """
    parts = match.group(1).split('|')
    name = parts[0].strip().lower()
    if name in TEMPLATE_DROP:
        return ''
    args = [p.strip() for p in parts[1:]
            if '=' not in p and p.strip() and not FORMAT_ARG.match(p.strip())]
    if not args:
        return ''
    if name in TEMPLATE_LAST_ARG:
        return args[-1]
    return args[0]


def strip_page_furniture(wikitext):
    """Drop the per-page <noinclude> headers and footers.

    Must run per page and before the pages are joined: the trailing-noinclude
    pattern is unbounded, so on a joined book it would swallow everything from
    the first page's footer to the end of the volume.
    """
    return NOINCLUDE_OPEN.sub('', NOINCLUDE.sub('', wikitext))


def page_to_text(wikitext):
    """Wikitext to plain text, run on a whole book once the pages are joined.

    Joining first matters: ProofreadPage splits a page mid-construct, so a
    '{{c|' or '[[link' opened at the foot of one page closes at the head of the
    next, and per-page conversion leaves both halves as visible markup.
    """
    text = COMMENT.sub('', wikitext)
    text = REF.sub('', text)
    text = TABLE.sub('', text)
    # Innermost templates resolve first, so nesting unwinds outward.
    for _ in range(8):
        collapsed = TEMPLATE.sub(resolve_template, text)
        if collapsed == text:
            break
        text = collapsed
    text = FILE_LINK.sub('', text)
    text = LINK_PIPED.sub(r'\1', text)
    text = LINK_PLAIN.sub(r'\1', text)
    text = EXTLINK.sub(r'\1', text)
    text = TAG.sub('', text)
    text = QUOTES.sub('', text)
    text = HEADING.sub(r'\1', text)
    text = re.sub(r'^[*#:;]+\s*', '', text, flags=re.M)
    text = PAGENUM.sub('', text)
    # Last resort: a handful of links in a table of contents are left unclosed
    # in the source itself. Keep their text, drop the stray brackets.
    text = re.sub(r'\[\[|\]\]|\{\{|\}\}', '', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return '\n'.join(line.rstrip() for line in text.splitlines()).strip()


def page_sort_key(title):
    tail = title.rsplit('/', 1)[-1]
    return (0, int(tail)) if tail.isdigit() else (1, tail)


def read_books(dump_path):
    """Group ns=104 pages into books keyed by their index file."""
    books = collections.defaultdict(list)
    with bz2.open(dump_path, 'rb') as fh:
        for _, elem in ET.iterparse(fh, events=('end',)):
            # Only <page> may be cleared: clearing its children on their own end
            # events would empty <title>/<text> before we ever read them.
            if elem.tag.rsplit('}', 1)[-1] != 'page':
                continue
            if elem.findtext('.//{*}ns') == '104':
                title = elem.findtext('.//{*}title') or ''
                text = elem.findtext('.//{*}revision/{*}text') or ''
                match = QUALITY.search(text)
                level = int(match.group(1)) if match else 0
                index = title.split(':', 1)[-1].rsplit('/', 1)[0]
                books[index].append((title, level, text))
            elem.clear()
    return books


def assess(index, pages):
    good = [p for p in pages if p[1] >= MIN_QUALITY]
    years = YEAR.findall(index)
    year = max((int(y) for y in years), default=None)
    reasons = []
    if any(name in index for name in EXCLUDE):
        reasons.append('already held from Gutenberg')
    if year is None:
        reasons.append('no year in index name')
    elif year > MAX_YEAR:
        reasons.append('published %d > %d' % (year, MAX_YEAR))
    if len(good) < MIN_PAGES:
        reasons.append('only %d proofread pages' % len(good))
    return good, year, reasons


def slug(index):
    stem = re.sub(r'\.(djvu|pdf)$', '', index, flags=re.I)
    # Keep any letter or digit, so Prévost and Molière survive as
    # themselves rather than as Pr_vost and Moli_re.
    return re.sub(r'[^\w]+', '_', stem, flags=re.UNICODE).strip('_')


def main():
    argv = sys.argv[1:]
    if '--dump' not in argv:
        sys.exit('usage: %s --dump PATH [--list] [--dry-run]\n  dump: %s'
                 % (os.path.basename(sys.argv[0]), DUMP_URL))
    dump = argv[argv.index('--dump') + 1]
    dry_run = '--dry-run' in argv
    listing = '--list' in argv

    books = read_books(dump)
    candidates = []
    for index, pages in books.items():
        good, year, reasons = assess(index, pages)
        candidates.append((index, pages, good, year, reasons))
    candidates.sort(key=lambda c: -len(c[2]))

    if listing:
        print('%d scanned books in the dump; quality gate: level >= %d, '
              'year <= %d, >= %d pages\n' % (len(books), MIN_QUALITY, MAX_YEAR,
                                             MIN_PAGES))
        print('%-52s %6s %6s %s' % ('index', 'pages', 'proof', 'verdict'))
        for index, pages, good, year, reasons in candidates[:40]:
            print('%-52s %6d %6d %s' % (index[:52], len(pages), len(good),
                                        '; '.join(reasons) or 'TAKE'))
        return 0

    existing = {}
    for name in os.listdir(RAW):
        if name.endswith('.txt'):
            with open(os.path.join(RAW, name), 'rb') as fh:
                existing[hashlib.sha256(fh.read()).hexdigest()] = name

    added, skipped = [], []
    for index, pages, good, year, reasons in candidates:
        if reasons:
            if len(good) >= MIN_PAGES:   # only report near-misses, not all 666
                skipped.append((index, '; '.join(reasons)))
            continue
        joined = '\n'.join(
            strip_page_furniture(text)
            for _title, _level, text in sorted(good,
                                               key=lambda p: page_sort_key(p[0])))
        blob = ('%s\n\n(Vikifontaro, %d proofread pages of %d scanned)\n\n%s\n'
                % (slug(index).replace('_', ' '), len(good), len(pages),
                   page_to_text(joined))).encode('utf-8')
        digest = hashlib.sha256(blob).hexdigest()
        if digest in existing:
            skipped.append((index, 'exact copy of %s' % existing[digest]))
            continue
        name = 'wsdump-%s.txt' % slug(index)
        if not dry_run:
            with open(os.path.join(RAW, name), 'wb') as fh:
                fh.write(blob)
        existing[digest] = name
        added.append({'file': name, 'index': index, 'year': year,
                      'proofread': len(good), 'scanned': len(pages),
                      'bytes': len(blob), 'sha': digest[:12]})

    if added and not dry_run:
        with open(PROVENANCE, 'a', encoding='utf-8') as fh:
            fh.write('\n## Batch 3 — Vikifontaro, proofread scans from the XML dump\n\n')
            fh.write('Extracted from the eo.wikisource dump (%s) by '
                     '`tools/fetch_raw_vikifontaro.py`. Only pages a human has '
                     'proofread (ProofreadPage quality level >= %d) are '
                     'included, and only books published %d or earlier; '
                     'unproofread OCR is left out because it invents lemmas. '
                     'One file per book, pages joined in order.\n\n'
                     % (DUMP_URL, MIN_QUALITY, MAX_YEAR))
            for rec in added:
                fh.write('- `%(file)s` — %(index)s — Vikifontaro — %(year)d — '
                         '%(proofread)d/%(scanned)d proofread pages — '
                         'sha256:%(sha)s — ' % rec)
                fh.write('%s\n' % (INDEX_URL % rec['index'].replace(' ', '_')))

    print('%s%d books added, %d near-misses skipped'
          % ('[dry run] ' if dry_run else '', len(added), len(skipped)))
    for rec in added:
        print('  + %-54s %4d pp %8d B' % (rec['file'][:54], rec['proofread'],
                                          rec['bytes']))
    for index, why in skipped:
        print('  - %-54s %s' % (index[:54], why))
    return 0


if __name__ == '__main__':
    sys.exit(main())
