#!/usr/bin/env python3
"""Verify the derived figures quoted in prose against the data they come from.

Usage: python3 tools/check_figures.py [--fix] [--quiet] [FILE ...]

`tools/check_grammar_citations.py` made quotations machine-checkable, and the
figures beside them stayed unchecked. They drift, and they drift silently:

  * `DICT/README.md` says "Every count in this section was measured against
    entries.jsonl as it stands, not carried forward from an earlier pass", and
    its verb count read 4153 against an actual 4159.
  * GRAMMAR §6.1 said *Francujo* 172 occurrences against *Francio* 1. The
    corpus had grown to 299 against 85, and the claim — that the corpus is
    lopsided — survived only because the ratio happened to survive.
  * GRAMMAR §6.2 said negative correlatives appear on 5965 lines. 13761.

None of that was noticed by reading. A citation that goes stale can be caught
by looking at the source; a figure that goes stale looks exactly like a figure
that is right.

So a figure carries its derivation, the way a quotation carries `source:line`:

    **27366 entries.** <!--= total() -->
    noun 18101 <!--= count(pos='noun') -->
    *Francujo* 299 <!--= corpus(r'\\bFrancujo\\b') -->

The marker is an HTML comment, so it is invisible in rendered Markdown. The
checker reads the last number before it, evaluates the expression against the
current data, and reports a mismatch. `--fix` rewrites the prose number.

WHAT SHOULD NOT BE ANNOTATED. A study result is a dated snapshot, not a live
figure: the rho values in ANALYSIS/ describe an analysis run over a stated
corpus, and silently updating them would rewrite a finding rather than
maintain a count. Annotate figures that are *supposed* to track the data —
inventory counts, corpus frequencies, coverage — and date the rest.

Available in an expression:

    total()                    entries in DICT/entries.jsonl
    count(pos=, source=, has=) entries matching all given conditions;
                               `has` tests for a field being present
    corpus(regex)              lines matching, over the Esperanto-language
                               sources, using the same exclusion list as
                               find_examples, which is mine_lemmas' plus the
                               Fundamento's multilingual tables
    occurrences(regex)         matches rather than lines. Not the same number:
                               a list of country names puts several on one
                               line, and `Francujo` is 296 lines and 299
                               occurrences. Use whichever the prose claims
    sources()                  how many sources that is
    dated()                    sources with a date in RAW/DATES.tsv
    pct(a, b)                  100 * a / b
"""
import argparse
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

MARKER = re.compile(r'<!--=\s*(.+?)\s*-->')
# The figure is the last number before the marker. Commas and a percent sign
# are part of how it is written, not part of its value. A little prose may
# stand between the two — `**27366 entries.** <!--= total() -->` reads better
# than forcing the marker to butt against the digits — so anything without a
# digit in it is allowed to intervene, up to a short window.
FIGURE = re.compile(r'(\d[\d,]*(?:\.\d+)?)[^\d]{0,48}$')
TOLERANCE = 0.051          # a figure printed to one decimal place


class Data(object):
    """Loaded once, lazily, because a corpus scan is not free."""

    def __init__(self):
        self._entries = None
        self._files = None
        self._text = None
        self._corpus = {}

    @property
    def entries(self):
        if self._entries is None:
            path = os.path.join(ROOT, 'DICT', 'entries.jsonl')
            with open(path, encoding='utf-8') as fh:
                self._entries = [json.loads(line) for line in fh
                                 if line.strip()]
        return self._entries

    @property
    def text(self):
        """The whole corpus, joined. 30MB, read once, so a document with a
        dozen frequency claims does not read it a dozen times."""
        if self._text is None:
            self._text = '\n'.join(
                open(path, encoding='utf-8').read() for path in self.files)
        return self._text

    @property
    def files(self):
        if self._files is None:
            # The same list find_examples uses, which is the same list
            # mine_lemmas keeps plus the Fundamento's multilingual tables. A
            # figure in GRAMMAR/ was quoted from find_examples, so it has to
            # be checked over find_examples' corpus or the check is measuring
            # a different thing than the claim.
            import find_examples
            excluded = find_examples.EXCLUDE
            corpus = os.path.join(ROOT, 'CORPUS')
            self._files = [os.path.join(corpus, name)
                           for name in sorted(os.listdir(corpus))
                           if name.endswith('.txt') and name not in excluded]
        return self._files

    def namespace(self):
        def count(**conditions):
            field = conditions.pop('has', None)
            hits = 0
            for entry in self.entries:
                if field and field not in entry:
                    continue
                if all(entry.get(k) == v for k, v in conditions.items()):
                    hits += 1
            return hits

        def corpus(pattern):
            key = ('lines', pattern)
            if key not in self._corpus:
                compiled = re.compile(pattern)
                self._corpus[key] = sum(1 for line in self.text.split('\n')
                                        if compiled.search(line))
            return self._corpus[key]

        def occurrences(pattern):
            key = ('all', pattern)
            if key not in self._corpus:
                self._corpus[key] = len(re.findall(pattern, self.text))
            return self._corpus[key]

        def dated():
            import csv
            path = os.path.join(ROOT, 'RAW', 'DATES.tsv')
            with open(path, encoding='utf-8') as fh:
                return sum(1 for row in csv.DictReader(fh, delimiter='\t')
                           if row['written'])

        return {
            'total': lambda: len(self.entries),
            'count': count,
            'corpus': corpus,
            'occurrences': occurrences,
            'sources': lambda: len(self.files),
            'dated': dated,
            'pct': lambda a, b: 100.0 * a / b if b else 0.0,
            're': re,
        }


def claimed_value(text, position):
    """The number immediately before a marker, and where it sits."""
    match = FIGURE.search(text[:position])
    if not match:
        return None, None, None
    raw = match.group(1)
    return float(raw.replace(',', '')), match.start(1), match.end(1)


def same(claimed, actual):
    if float(actual) == int(actual) and float(claimed) == int(claimed):
        return int(claimed) == int(actual)
    return abs(claimed - actual) <= TOLERANCE


def render(value, sample):
    """Format like the figure it replaces: keep thousands separators and dp."""
    if float(value) == int(value) and '.' not in sample:
        text = '%d' % int(value)
        return '{:,}'.format(int(value)) if ',' in sample else text
    places = len(sample.split('.')[1]) if '.' in sample else 1
    return '%.*f' % (places, value)


def check(path, data, fix, problems, checked):
    text = open(path, encoding='utf-8').read()
    edits = []
    for marker in MARKER.finditer(text):
        expression = marker.group(1)
        where = '%s: %s' % (os.path.relpath(path, ROOT), expression)
        claimed, start, end = claimed_value(text, marker.start())
        if claimed is None:
            problems.append('%s : no figure before the marker' % where)
            continue
        try:
            actual = eval(expression, {'__builtins__': {}}, data.namespace())
        except Exception as error:                    # noqa: BLE001
            problems.append('%s : expression failed — %s: %s'
                            % (where, type(error).__name__, error))
            continue
        if same(claimed, actual):
            checked.append(where)
            continue
        problems.append('%s : prose says %s, data says %s'
                        % (where, render(claimed, text[start:end]),
                           render(actual, text[start:end])))
        edits.append((start, end, render(actual, text[start:end])))

    if fix and edits:
        for start, end, replacement in reversed(edits):
            text = text[:start] + replacement + text[end:]
        open(path, 'w', encoding='utf-8').write(text)
        print('  fixed %d figures in %s' % (len(edits),
                                            os.path.relpath(path, ROOT)))
    return len(edits)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('files', nargs='*')
    parser.add_argument('--fix', action='store_true',
                        help='rewrite stale figures in place')
    parser.add_argument('--quiet', action='store_true')
    args = parser.parse_args()

    paths = args.files
    if not paths:
        paths = []
        for folder in ('DICT', 'GRAMMAR', 'ANALYSIS'):
            directory = os.path.join(ROOT, folder)
            if not os.path.isdir(directory):
                continue
            paths += [os.path.join(directory, name)
                      for name in sorted(os.listdir(directory))
                      if name.endswith('.md')]

    data = Data()
    problems, checked = [], []
    for path in paths:
        check(path, data, args.fix, problems, checked)

    if not args.quiet:
        for where in checked:
            print('  ok    %s' % where)
    for problem in problems:
        print('  %s  %s' % ('FIXED' if args.fix else 'STALE', problem))
    print('\n%d figures checked, %d %s'
          % (len(checked) + len(problems), len(problems),
             'corrected' if args.fix else 'stale'))
    return 0 if args.fix or not problems else 1


if __name__ == '__main__':
    sys.exit(main())
