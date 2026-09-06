#!/usr/bin/env python3
"""Verify every citation in GRAMMAR/ against CORPUS/.

Usage: python3 tools/check_grammar_citations.py [--context N] [--quiet]

GRAMMAR/index.md promises that claims are cited in the form *quoted text* —
`source:line` and that "citations are machine-checkable: each quotation appears
at the line given". Nothing checked it. This does, and it checks the promise
that actually matters: not that the file and line exist, but that the quoted
words are there.

Two failure modes, and only the second is caught by a weaker check:

  the line moved   CORPUS/ is derived. Re-running normalize_corpus.py after a
                   change to hyphen rejoining or mojibake repair shifts line
                   numbers in any file it touches, and every citation into that
                   file silently goes stale while still pointing at a real
                   line.
  the quote drifted  A quotation edited for length in the prose no longer
                   matches the source it names.

A quotation is allowed to span a few corpus lines, because the prose wraps and
the corpus does not, so the comparison joins a window around the cited line and
collapses whitespace before matching. Punctuation is compared as written: a
citation that silently modernises the source's punctuation is a citation that
has drifted.

A quotation may be shortened, but the elision has to be marked with `…` and is
then matched segment by segment. Shortening one silently is exactly the defect
this catches: a citation here ended `Argentinio, Tunizio, Aŭstralio)` where the
source reads `Argentinio, Tunizio, Aŭstralio, 11 poŝtaj abonantoj)`, closing a
bracket the source had not closed and making a list look complete.
"""
import argparse
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GRAMMAR = os.path.join(ROOT, 'GRAMMAR')
CORPUS = os.path.join(ROOT, 'CORPUS')

CITATION = re.compile(r'`?([a-zA-Z][\w.\-]*?)(?:\.txt)?`?:(\d+)`?')
# A quoted span: *italic* or “double quoted”, the two forms the guide uses.
# Non-greedy and with no length floor, because a floor makes the asterisks
# pair up wrong: a short span like *Ne,* fails the floor, the engine then opens
# a span at its CLOSING asterisk, and every quotation after it in the paragraph
# is captured off by one — which is the prose between two quotations rather
# than a quotation. Short spans are dropped after matching instead.
QUOTE = re.compile(r'\*([^*]+?)\*|“([^”]+?)”')
MIN_QUOTE = 8


def normalise(text):
    """Whitespace, blockquote markers and emphasis.

    Markdown wraps and the corpus does not, so whitespace has to go. Two more
    were found the hard way, each of which made a correct citation look broken:
    a `>` blockquote wraps across lines and leaves `— > Portugalujo` in the
    middle of the quotation, and CORPUS/ preserves the source's own `_italic_`
    markers, so `"Ne, nenion _strangan_," mi diris` never matches a prose
    quotation that tidied them away.
    """
    text = re.sub(r'(?m)^\s*>\s?', ' ', text)
    text = text.replace('_', '').replace('*', '')
    return re.sub(r'\s+', ' ', text).strip()


def matches(quote, window):
    """Is this quotation present, allowing marked elisions?

    Segments must appear in order and without overlapping, so `…` cannot be
    used to stitch together words the source has in the other order.
    """
    at = 0
    for segment in (s.strip() for s in quote.split('…')):
        if not segment:
            continue
        found = window.find(segment, at)
        if found < 0:
            return False
        at = found + len(segment)
    return True


def quotes_near(text, position):
    """Quoted spans in the paragraph holding this citation, nearest first.

    The guide puts the quotation before the citation in a blockquote and after
    it in running prose, so both sides of the paragraph are searched.
    """
    start = text.rfind('\n\n', 0, position)
    end = text.find('\n\n', position)
    block = text[start + 2 if start >= 0 else 0:
                 end if end >= 0 else len(text)]
    cut = position - (start + 2 if start >= 0 else 0)
    def spans(fragment):
        # Bold is `**x**`, and its doubled asterisks pair up with the single
        # asterisks of the italic quotations around them, offsetting every
        # span in the paragraph. Dropping the markers is safe here because
        # only the CONTENT of each quotation is wanted, never its position.
        fragment = fragment.replace('**', '')
        return [q for q in (a or b for a, b in QUOTE.findall(fragment))
                if len(normalise(q)) >= MIN_QUOTE]
    return list(reversed(spans(block[:cut]))) + spans(block[cut:])


def check(path, context, problems, checked):
    text = open(path, encoding='utf-8').read()
    for match in CITATION.finditer(text):
        source, line = match.group(1) + '.txt', int(match.group(2))
        where = '%s -> %s:%d' % (os.path.basename(path), source, line)
        full = os.path.join(CORPUS, source)
        if not os.path.exists(full):
            problems.append('%s : no such source' % where)
            continue
        lines = open(full, encoding='utf-8').readlines()
        if not 1 <= line <= len(lines):
            problems.append('%s : line out of range, file has %d'
                            % (where, len(lines)))
            continue
        candidates = quotes_near(text, match.start())
        if not candidates:
            checked.append((where, 'line exists; no quotation to verify'))
            continue
        window = normalise(''.join(lines[max(0, line - 1 - context):
                                         line + context]))
        for quote in candidates:
            if matches(normalise(quote), window):
                checked.append((where, 'quotation verified'))
                break
        else:
            problems.append('%s : quotation not found within %d lines\n'
                            '        wanted: %s\n        window: %s'
                            % (where, context, normalise(candidates[0])[:90],
                               window[:90]))


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--context', type=int, default=2,
                        help='corpus lines either side of the cited line that '
                             'a quotation may span (default 2)')
    parser.add_argument('--quiet', action='store_true')
    args = parser.parse_args()

    problems, checked = [], []
    for name in sorted(os.listdir(GRAMMAR)):
        if name.endswith('.md'):
            check(os.path.join(GRAMMAR, name), args.context, problems, checked)

    verified = sum(1 for _w, note in checked if note == 'quotation verified')
    if not args.quiet:
        for where, note in checked:
            print('  ok    %-44s %s' % (where, note))
    for problem in problems:
        print('  FAIL  %s' % problem)
    print('\n%d citations: %d quotations verified, %d line-only, %d broken'
          % (len(checked) + len(problems), verified,
             len(checked) - verified, len(problems)))
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main())
