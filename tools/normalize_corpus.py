#!/usr/bin/env python3
"""Normalize RAW/ sources into CORPUS/ — clean text for the DICT and GRAMMAR passes.

Input:  RAW/*.txt — 10 pg-*.txt (Project Gutenberg) and 79 wsrc-*.txt (Vikifontaro).
Output: CORPUS/<same basename>  — body text only, one file per source
        CORPUS/MANIFEST.tsv     — per-source record of what was stripped and why

Three source-specific concerns, each handled and reported separately:

  * pg-*.txt carry Project Gutenberg front/back matter. The body is exactly the
    span between the '*** START OF ... ***' and '*** END OF ... ***' markers;
    a missing marker is an error, not something to guess around.
  * wsrc-*.txt had their wikitext stripped upstream (PR #4) but kept the
    Vikifontaro page furniture: multilingual title lines, author attribution,
    page-range notes and prev/next navigation. That preamble ends at a
    run-together metadata line ('collectionFabeloj de AndersenHans Christian
    Andersen...', 'book...', or a bare page number followed by the title).
    Two index-like pages have no such line and fall back to pattern matching;
    the manifest flags them as 'wsrc-fallback' for eyeballing.
  * Six pg-* files are written in x-system ASCII (cx gx hx jx sx ux) rather than
    UTF-8 diacritics. Conversion is per-file and gated on the x-system being
    dominant, because 'aux'/'auxiliary'/'flux' are ordinary words in the
    English-Esperanto dictionary (pg-16967) and would be corrupted by it.
"""
import hashlib
import os
import re
import sys
import unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, 'RAW')
OUT = os.path.join(ROOT, 'CORPUS')

# ---------------------------------------------------------------- Gutenberg
PG_START = re.compile(r'\*\*\*\s*START OF TH[EI]S? PROJECT GUTENBERG')
# Older texts close the body with a bare 'End of Project Gutenberg's X, by Y'
# line and only then the fenced marker, so the earliest of the two wins.
PG_END = re.compile(r'\*\*\*\s*END OF TH[EI]S? PROJECT GUTENBERG'
                    r"|^End of (?:the )?Project Gutenberg('s)?\b")
PG_CREDIT = re.compile(r'^Produced by\b')
PG_NOTE = re.compile(r"^\s*TRANSCRIBER'?S NOTE", re.IGNORECASE)
# A centered title line ends the front matter the note belongs to.
PG_TITLE = re.compile(r'^\s{4,}\S')

# ---------------------------------------------------------------- Vikifontaro
# The run-together metadata line: a type marker or page number glued directly
# to the title, with no separating space.
WSRC_META = re.compile(r'^(?:collection|book|\d+)(?=[^\W\d_])')
# Page furniture: navigation, download prompts, page-range notes, index links.
WSRC_NAV = re.compile(r'^\s*(?:[←→►◄]|Elŝuti kiel|Indekso\s*:|\(p\.\s|Paĝo\.\s*$)')
WSRC_NAV_TAIL = re.compile(r'[→►]\s*$')
# Footnote markers: keep the note, drop the arrow that Vikifontaro prepends.
WSRC_FOOTNOTE = re.compile(r'^\s*↑\s*')

# ---------------------------------------------------------------- x-system
XSYS = [('cx', 'ĉ'), ('gx', 'ĝ'), ('hx', 'ĥ'), ('jx', 'ĵ'), ('sx', 'ŝ'),
        ('ux', 'ŭ')]
XSYS_MIN = 100  # below this, matches are foreign words, not Esperanto spelling


def xsystem_hits(text):
    return sum(len(re.findall(a, text, re.IGNORECASE)) for a, _ in XSYS)


def to_utf8_diacritics(text):
    for ascii_pair, letter in XSYS:
        text = text.replace(ascii_pair, letter)
        text = text.replace(ascii_pair.upper(), letter.upper())
        text = text.replace(ascii_pair.capitalize(), letter.upper())
    return text


# ---------------------------------------------------------------- h-system
# Zamenhof's own fallback spelling: ch gh hh jh sh for ĉ ĝ ĥ ĵ ŝ, and plain u
# for ŭ. Riskier to undo than the x-system, because 'gh' and 'ch' occur
# legitimately across morpheme boundaries in compounds (flug+haveno), and x
# is not an Esperanto letter at all. So convert only where the file shows the
# digraphs *and* essentially no diacritics — a file already using ĉ cannot be
# in the h-system, and its digraphs are compounds or foreign words.
HSYS = [('ch', 'ĉ'), ('gh', 'ĝ'), ('hh', 'ĥ'), ('jh', 'ĵ'), ('sh', 'ŝ')]
HSYS_MIN = 100
HSYS_MAX_DIACRITIC_RATIO = 0.05
DIACRITIC = re.compile(r'[ĉĝĥĵŝŭĈĜĤĴŜŬ]')
# ŭ is written as bare u and cannot be recovered by rule; these are the words
# where it actually occurs, which covers the great majority of tokens.
# Compounds where 'eu' or 'au' spans a morpheme boundary and is NOT a
# diphthong: ne+uzebla, ne+utila, tre+uzata.
U_COMPOUND = ['neuzebl', 'neuzat', 'neutil', 'neuzind', 'treuz', 'reuz']


def hsystem_hits(text):
    return sum(len(re.findall(r'\w*%s\w*' % a, text, re.IGNORECASE))
               for a, _ in HSYS)


def is_hsystem(text):
    hits = hsystem_hits(text)
    if hits < HSYS_MIN:
        return False
    return len(DIACRITIC.findall(text)) < hits * HSYS_MAX_DIACRITIC_RATIO


def from_hsystem(text):
    for digraph, letter in HSYS:
        text = text.replace(digraph, letter)
        text = text.replace(digraph.upper(), letter.upper())
        text = text.replace(digraph.capitalize(), letter.upper())
    # ŭ occurs only in the diphthongs aŭ and eŭ, so inside an h-system file
    # every 'au' and 'eu' is one — a word list was too narrow and left
    # ankorau, lau, fraulino and ĉirkau behind. The exception is a compound
    # where a prefix ending in e meets a root starting with u (ne+uzebla), so
    # those are protected explicitly.
    protected = {}
    for i, word in enumerate(U_COMPOUND):
        token = '\x00%d\x00' % i
        protected[token] = word
        text = re.sub(r'\b%s' % word, token, text, flags=re.IGNORECASE)
    text = re.sub(r'au', 'aŭ', text)
    text = re.sub(r'AU', 'AŬ', text)
    text = re.sub(r'Au', 'Aŭ', text)
    text = re.sub(r'eu', 'eŭ', text)
    text = re.sub(r'EU', 'EŬ', text)
    text = re.sub(r'Eu', 'Eŭ', text)
    for token, word in protected.items():
        text = text.replace(token, word)
    return text


# ------------------------------------------------------------- homoglyphs
# Three Dua Libro pages carry Cyrillic letters inside otherwise-Latin words
# (роv for pov, ѵоrt for vort) — invisible to a reader, but they split the
# affected words off as unexplained near-miss lemmas downstream.
HOMOGLYPH = {'а': 'a', 'е': 'e', 'о': 'o', 'р': 'p', 'с': 'c', 'у': 'y',
             'х': 'x', 'і': 'i', 'ѵ': 'v', 'ј': 'j', 'ѕ': 's',
             'А': 'A', 'Е': 'E', 'О': 'O', 'Р': 'P', 'С': 'C', 'Х': 'X',
             'І': 'I', 'Ј': 'J'}
CYRILLIC = re.compile(r'[Ѐ-ӿ]')
MIXED_TOKEN = re.compile(r'\b(?=\w*[Ѐ-ӿ])(?=\w*[A-Za-zĉĝĥĵŝŭ])\w+\b')


def repair_homoglyphs(text):
    """Latinise Cyrillic letters that appear inside otherwise-Latin words.

    Only mixed-script tokens are touched, so genuine Russian glosses — the
    Universala Vortaro carries a whole Russian column — are left alone.
    """
    def fix(match):
        return ''.join(HOMOGLYPH.get(ch, ch) for ch in match.group())
    return MIXED_TOKEN.sub(fix, text)


# ---------------------------------------------------------------- slicing
def strip_pg_frontmatter(lines):
    """Drop the proofreader credit and transcriber's note the body opens with."""
    i = 0
    while i < len(lines) and not lines[i].strip():
        i += 1
    if i < len(lines) and PG_CREDIT.match(lines[i]):
        while i < len(lines) and lines[i].strip():
            i += 1
        while i < len(lines) and not lines[i].strip():
            i += 1
    if i < len(lines) and PG_NOTE.match(lines[i]):
        j = i
        while j < len(lines) and not PG_TITLE.match(lines[j]):
            j += 1
        i = j
    return i


def slice_gutenberg(lines, name):
    start = end = None
    for i, line in enumerate(lines):
        if start is None and PG_START.search(line):
            start = i + 1
        elif start is not None and PG_END.search(line):
            end = i
            break
    if start is None or end is None:
        raise ValueError('%s: missing Gutenberg %s marker'
                         % (name, 'START' if start is None else 'END'))
    body = lines[start:end]
    front = strip_pg_frontmatter(body)
    return body[front:], 'pg-markers', start + front, len(lines) - end


def slice_vikifontaro(lines):
    """Drop the Vikifontaro preamble. Returns (body, method, head, tail)."""
    for i, line in enumerate(lines):
        if WSRC_META.match(line):
            return lines[i + 1:], 'wsrc-marker', i + 1, 0
    # No metadata line (index/TOC pages): strip the leading furniture block,
    # including the title and author lines it repeats.
    author = title = None
    for line in lines[:20]:
        stripped = line.strip()
        if stripped.startswith('de ') and author is None:
            author = stripped[3:].strip()
        if stripped.startswith('Indekso') and title is None:
            title = stripped.split(':', 1)[-1].strip()
    # Stop at the first line that is not furniture. Erring towards keeping a
    # stray title line beats advancing past real content on a blank line, which
    # is what a last-match scan does to the Grammar and index pages.
    head = 0
    while head < len(lines):
        stripped = lines[head].strip()
        if (not stripped or WSRC_NAV.match(lines[head]) or stripped == author
                or stripped == title):
            head += 1
            continue
        break
    return lines[head:], 'wsrc-fallback', head, 0


# ---------------------------------------------------------------- cleanup
def clean(lines):
    out = []
    for line in lines:
        line = line.replace(' ', ' ')  # NBSP → space
        if WSRC_NAV.match(line):
            continue
        # Short trailing-arrow lines are next-page links, not prose.
        if WSRC_NAV_TAIL.search(line) and len(line.strip()) < 60:
            continue
        line = WSRC_FOOTNOTE.sub('', line)
        out.append(line.rstrip())
    # Collapse runs of blank lines and trim the edges.
    collapsed, blank = [], 0
    for line in out:
        if line:
            blank = 0
        else:
            blank += 1
            if blank > 1:
                continue
        collapsed.append(line)
    while collapsed and not collapsed[0]:
        collapsed.pop(0)
    while collapsed and not collapsed[-1]:
        collapsed.pop()
    return collapsed


def normalize(path):
    name = os.path.basename(path)
    with open(path, encoding='utf-8') as fh:
        lines = fh.read().splitlines()

    if name.startswith('pg-'):
        body, method, head, tail = slice_gutenberg(lines, name)
    elif name.startswith('wsdump-'):
        # Extracted from the Wikisource dump, which has no page furniture to
        # strip — only the shared cleanup below applies.
        body, method, head, tail = lines, 'wsdump-clean', 0, 0
    else:
        body, method, head, tail = slice_vikifontaro(lines)

    body = clean(body)
    text = '\n'.join(body) + '\n'

    hits = xsystem_hits(text)
    converted = hits >= XSYS_MIN
    if converted:
        text = to_utf8_diacritics(text)
    hsystem = is_hsystem(text)
    if hsystem:
        text = from_hsystem(text)
    homoglyphs = len(MIXED_TOKEN.findall(text))
    if homoglyphs:
        text = repair_homoglyphs(text)
    text = unicodedata.normalize('NFC', text)

    return {
        'source': name,
        'in_lines': len(lines),
        'out_lines': text.count('\n'),
        'head_stripped': head,
        'tail_stripped': tail,
        'method': method,
        'xsystem': 'converted:%d' % hits if converted else
                   ('left:%d' % hits if hits else '-'),
        'hsystem': 'converted' if hsystem else '-',
        'homoglyphs': homoglyphs or '-',
        'sha256': hashlib.sha256(text.encode('utf-8')).hexdigest()[:12],
        'text': text,
    }


def main():
    sources = sorted(f for f in os.listdir(RAW) if f.endswith('.txt'))
    if not sources:
        sys.exit('no RAW/*.txt sources found')
    os.makedirs(OUT, exist_ok=True)

    records, failures = [], []
    for name in sources:
        try:
            record = normalize(os.path.join(RAW, name))
        except ValueError as exc:
            failures.append(str(exc))
            continue
        with open(os.path.join(OUT, name), 'w', encoding='utf-8') as fh:
            fh.write(record.pop('text'))
        records.append(record)

    columns = ['source', 'method', 'in_lines', 'out_lines', 'head_stripped',
               'tail_stripped', 'xsystem', 'hsystem', 'homoglyphs',
               'sha256']
    with open(os.path.join(OUT, 'MANIFEST.tsv'), 'w', encoding='utf-8') as fh:
        fh.write('\t'.join(columns) + '\n')
        for record in records:
            fh.write('\t'.join(str(record[c]) for c in columns) + '\n')

    kept = sum(r['out_lines'] for r in records)
    dropped = sum(r['in_lines'] for r in records) - kept
    print('normalized %d/%d sources → %s' % (len(records), len(sources), OUT))
    print('  %d body lines kept, %d furniture lines dropped' % (kept, dropped))
    print('  x-system converted: %d file(s); h-system converted: %d file(s)'
          % (sum(1 for r in records if r['xsystem'].startswith('converted')),
             sum(1 for r in records if r['hsystem'] == 'converted')))
    print('  wsrc fallback (verify by hand): %s'
          % (', '.join(r['source'] for r in records
                       if r['method'] == 'wsrc-fallback') or 'none'))
    for failure in failures:
        print('  ERROR %s' % failure, file=sys.stderr)
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
