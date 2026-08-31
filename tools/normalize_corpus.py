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
  * Many pg-* files are written in ASCII rather than UTF-8 diacritics, in the
    x-system (cx gx hx jx sx ux) or Zamenhof's h-system (ch gh hh jh sh).
    Undoing either is gated per file on measuring the result — see
    conversion_is_sound — because 'aux', 'auxiliary', 'such' and 'Schiller'
    are ordinary words that the same substitutions would corrupt.
"""
import hashlib
import os
import re
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import esperanto  # noqa: E402  (path set above)

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
DIACRITIC = re.compile(r'[ĉĝĥĵŝŭĈĜĤĴŜŬ]')
# ŭ is written as bare u and cannot be recovered by rule; these are the words
# where it actually occurs, which covers the great majority of tokens.
# Compounds where 'eu' or 'au' spans a morpheme boundary and is NOT a
# diphthong: ne+uzebla, ne+utila, tre+uzata.
U_COMPOUND = ['neuzebl', 'neuzat', 'neutil', 'neuzind', 'treuz', 'reuz']


def hsystem_hits(text):
    return sum(len(re.findall(r'\w*%s\w*' % a, text, re.IGNORECASE))
               for a, _ in HSYS)


# Whether to undo an ASCII spelling system is decided by measuring the result
# rather than by a proxy. The proxy tried first was "convert only if the file
# has essentially no diacritics already", which is wrong in both directions:
#
#   * it rejected pg-24575, a Czech-language textbook that writes its Esperanto
#     in the h-system and merely quotes a few diacritic spellings, so regho,
#     ghi, chiuj and ech reached the review queue as vocabulary;
#   * it accepted pg-60429, whose diacritics had been mangled to replacement
#     characters and so counted as none, and whose 104 "digraphs" were all in
#     the English licence and the name Schiller.
#
# Converting a word and asking whether the result is Esperanto settles both.
# Counted over distinct spellings the two populations do not overlap: every
# genuine x- or h-system source in RAW/ improves at least 4 spellings for each
# one it breaks (usually 20 to 1), while the three files that must not be
# converted all break more than they fix — the English and French Ekzercaro
# translations at roughly 1 gain per 3 losses, pg-60429 at 6 against 22.
SOUND_RATIO = 2.0
_vocabulary = None


def vocabulary():
    global _vocabulary
    if _vocabulary is None:
        _vocabulary = esperanto.load_vocabulary()
    return _vocabulary


def conversion_is_sound(text, convert, ratio=SOUND_RATIO):
    """True if converting this text makes more Esperanto words than it breaks.

    Distinct spellings are counted, not occurrences, so one frequent foreign
    word cannot decide the file on its own: 'such' appears 285 times in one
    English grammar and would otherwise outweigh every real conversion.
    """
    roots, words = vocabulary()
    gained = broken = 0
    for word in {w.lower() for w in WORDLIKE.findall(text)}:
        converted = convert(word)
        if converted == word:
            continue
        if esperanto.analyse(converted, roots, words)[1] != 'unknown':
            gained += 1
        else:
            broken += 1
    return gained >= ratio * broken and gained > 0


# Foreign spellings that must survive an h-system file untouched. This catches
# the common damage but not every case: a foreign name whose 'ch' sits between
# vowels (Michael) is indistinguishable by rule from an h-system spelling and
# is still converted. Converting
# blindly turned the German names Schneider and Bloch into "Sĉneider" and
# "Bloĉ" — 'sch' is not an Esperanto sequence, and no Esperanto word ends in a
# bare ĉ/ĝ/ĥ/ĵ/ŝ, so both are detectable per word rather than per file.
FOREIGN_MARK = re.compile(r'sch|[qwxy]', re.IGNORECASE)
WORDLIKE = re.compile(r'[A-Za-zĉĝĥĵŝŭĈĜĤĴŜŬ]+')


def convert_word(word):
    if FOREIGN_MARK.search(word):
        return word
    converted = word
    for digraph, letter in HSYS:
        converted = converted.replace(digraph, letter)
        converted = converted.replace(digraph.upper(), letter.upper())
        converted = converted.replace(digraph.capitalize(), letter.upper())
    # A long word does not end in a bare circumflexed consonant, so such a
    # result means the digraph belonged to a foreign name (Bloch -> "Bloĉ").
    # Short words are the exception: eĉ is exactly that shape, and blocking it
    # left 'ech' unconverted in three h-system sources.
    if len(converted) > 3 and converted[-1:] in 'ĉĝĥĵŝĈĜĤĴŜ':
        return word
    return converted


# UTF-8 read as Latin-1 and re-encoded, twice over: 'ĝ' (C4 9D) becomes 'Ä\x9d'
# and then 'Ã\x84Â\x9d'. One RAW source arrived this way, and the damage was
# invisible downstream because the result is valid UTF-8 — the file simply had
# no diacritics, which then made the h-system gate misfire on its English
# licence text. Undo it by round-tripping each run of high Latin-1 characters
# until it stops changing, and only where it succeeds: a run that is genuinely
# Latin-1 (Achtélik, a French quotation) fails to decode as UTF-8 and is left
# exactly as found.
MOJIBAKE_RUN = re.compile('[\u00c2-\u00c5][\u0080-\u00ff]'
                          '(?:[\u00c2-\u00c5][\u0080-\u00ff])*')
MOJIBAKE_MIN = 20


def unmojibake_run(run, rounds=3):
    for _ in range(rounds):
        try:
            candidate = run.encode('latin-1').decode('utf-8')
        except (UnicodeEncodeError, UnicodeDecodeError):
            return run
        run = candidate
    return run


def repair_mojibake(text):
    return MOJIBAKE_RUN.sub(lambda m: unmojibake_run(m.group()), text)


def from_hsystem(text):
    text = WORDLIKE.sub(lambda m: convert_word(m.group()), text)
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


def unsound_hits(verdict):
    return int(verdict.split(':')[1]) if str(verdict).startswith('unsound') else 0


def spelling_verdict(hits, minimum, sound):
    """How the manifest records a conversion decision.

    Three outcomes worth distinguishing: converted, rejected by measurement
    ('unsound' — the file looked like an ASCII spelling and is not one), and
    never a candidate ('left' — a handful of incidental matches, which almost
    every source has).
    """
    if not hits:
        return '-'
    if sound:
        return 'converted:%d' % hits
    return ('unsound:%d' if hits >= minimum else 'left:%d') % hits


def normalize(path):
    name = os.path.basename(path)
    with open(path, encoding='utf-8') as fh:
        text = fh.read()
    # Before anything else: a mis-encoded file has no diacritics to reason
    # about, so every later decision about its orthography would be made on
    # false evidence.
    mojibake = len(MOJIBAKE_RUN.findall(text))
    if mojibake >= MOJIBAKE_MIN:
        text = repair_mojibake(text)
    else:
        mojibake = 0
    lines = text.splitlines()

    if name.startswith('pg-'):
        body, method, head, tail = slice_gutenberg(lines, name)
    elif name.startswith(('wsdump-', 'ia-')):
        # Extracted from the Wikisource dump or fetched from archive.org:
        # neither carries the Vikifontaro page furniture, and routing them
        # through that stripper would have them judged against a preamble
        # they do not have.
        body, method, head, tail = (
            lines, 'wsdump-clean' if name.startswith('wsdump-') else 'ia-clean',
            0, 0)
    else:
        body, method, head, tail = slice_vikifontaro(lines)

    body = clean(body)
    text = '\n'.join(body) + '\n'

    hits = xsystem_hits(text)
    x_sound = hits >= XSYS_MIN and conversion_is_sound(text, to_utf8_diacritics)
    if x_sound:
        text = to_utf8_diacritics(text)
    hsystem_count = hsystem_hits(text)
    h_sound = (hsystem_count >= HSYS_MIN
               and conversion_is_sound(text, convert_word))
    if h_sound:
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
        'xsystem': spelling_verdict(hits, XSYS_MIN, x_sound),
        'hsystem': spelling_verdict(hsystem_count, HSYS_MIN, h_sound),
        'mojibake': mojibake or '-',
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
               'tail_stripped', 'xsystem', 'hsystem', 'mojibake', 'homoglyphs',
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
             sum(1 for r in records
                 if str(r['hsystem']).startswith('converted'))))
    # Most of these are unremarkable: any long Esperanto text has a hundred
    # compounds whose morpheme boundary spells 'gh' or 'ch'. Only the files
    # where the pattern is dense enough to have fooled a threshold are worth
    # naming, so print the count and then the worst offenders.
    rejected = sorted(
        ((max(unsound_hits(r['xsystem']), unsound_hits(r['hsystem'])), r)
         for r in records
         if unsound_hits(r['xsystem']) or unsound_hits(r['hsystem'])),
        reverse=True, key=lambda pair: pair[0])
    print('  %d file(s) looked like an ASCII spelling and measured otherwise%s'
          % (len(rejected), ':' if rejected else ''))
    for hits, record in rejected[:5]:
        print('      %-58s %d matches' % (record['source'][:58], hits))
    mojibake = [r['source'] for r in records if r['mojibake'] != '-']
    if mojibake:
        print('  mojibake repaired: %s' % ', '.join(mojibake))
    print('  wsrc fallback (verify by hand): %s'
          % (', '.join(r['source'] for r in records
                       if r['method'] == 'wsrc-fallback') or 'none'))
    for failure in failures:
        print('  ERROR %s' % failure, file=sys.stderr)
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
