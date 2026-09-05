#!/usr/bin/env python3
"""Recover the headwords and variants the ReVo merge damaged, from the source.

Usage: python3 tools/repair_revo_headwords.py --articles DIR [--apply]

`tools/repair_headwords.py` made every headword a word again by truncating at
the comma, and said plainly that the second form could not be recovered from
the truncated string. It can be recovered from the source, and this does that.

The cause, read off the XML rather than guessed: ReVo writes a headword as a
`<kap>` in which `<tld/>` stands for the article's root, and an alternative
spelling as a nested `<var><kap>`:

    <kap><tld/>ulo, <var><kap><tld/>ulino</kap></var></kap>

The merge expanded `<tld/>` at the top level but not inside the nested `<kap>`,
so 'adultulo, adultulino' came out as 'adultulo,ulino' — the variant lost its
root, and the comma joined the two into something that is not a word. The same
flattening is why multi-word headwords lost their spaces.

So this reads each damaged entry's article, renders its `<kap>` properly, and
writes back the real headword with any variants in a `variants` field. An
entry whose article cannot be found, or whose rendered headword does not match
the truncated one, is left exactly as it is and reported.
"""
import argparse
import json
import os
import re
import sys
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENTRIES = os.path.join(ROOT, 'DICT', 'entries.jsonl')

# Inside a <kap>, these carry apparatus rather than the headword itself.
SKIP = {'ofc', 'fnt', 'rim', 'uzo', 'ref', 'refgrp', 'gra', 'lstyle'}
ENTITY = re.compile(r'&([A-Za-z][A-Za-z0-9_]*);')
X_SYSTEM = {'cx': 'ĉ', 'gx': 'ĝ', 'hx': 'ĥ', 'jx': 'ĵ', 'sx': 'ŝ', 'ux': 'ŭ',
            'Cx': 'Ĉ', 'Gx': 'Ĝ', 'Hx': 'Ĥ', 'Jx': 'Ĵ', 'Sx': 'Ŝ',
            'Ux': 'Ŭ'}
# The named entities ReVo uses for the Esperanto letters.
LETTER = {'ccirc': 'ĉ', 'gcirc': 'ĝ', 'hcirc': 'ĥ', 'jcirc': 'ĵ',
          'scirc': 'ŝ', 'ubreve': 'ŭ', 'Ccirc': 'Ĉ', 'Gcirc': 'Ĝ',
          'Hcirc': 'Ĥ', 'Jcirc': 'Ĵ', 'Scirc': 'Ŝ', 'Ubreve': 'Ŭ'}


def strip_entities(text):
    """Resolve the letter entities and drop the rest, so parsing succeeds."""
    return ENTITY.sub(lambda m: LETTER.get(m.group(1), ''), text)


def render(element, root):
    """The text of a <kap>, with <tld/> expanded — including inside <var>."""
    parts = []
    if element.text:
        parts.append(element.text)
    for child in element:
        if child.tag == 'tld':
            lit = child.get('lit')
            parts.append(lit + root[1:] if lit else root)
        elif child.tag == 'var':
            pass                       # collected separately, not inline
        elif child.tag not in SKIP:
            parts.append(render(child, root))
        if child.tail:
            parts.append(child.tail)
    # The XML wraps lines inside a <kap>, so a rendered form can carry a
    # newline and stray indentation: 'borela sigma-algebro' came out with its
    # variant split across two lines.
    return re.sub(r'\s+', ' ', ''.join(parts)).strip()


def headwords(kap, root):
    """(main form, [variant forms]) for one <kap>."""
    main = render(kap, root)
    # The comma before a <var> belongs to the apparatus, not to the word.
    main = main.split(',')[0].strip()
    variants = []
    for var in kap.iter('var'):
        for inner in var.iter('kap'):
            form = render(inner, root).split(',')[0].strip()
            if form and form != main:
                variants.append(form)
    return main, variants


def squash(form):
    return form.lower().replace(' ', '').replace('-', '').replace('’', '')


def article_root(tree):
    """The root an article's <tld/> stands for."""
    art = tree.find('.//art')
    if art is None:
        return None
    kap = art.find('kap')
    if kap is None:
        return None
    rad = kap.find('rad')
    return rad.text.strip() if rad is not None and rad.text else None


def index_article(path):
    """Every headword the article defines, as {form: [variants]}."""
    try:
        with open(path, encoding='utf-8') as fh:
            tree = ET.fromstring(strip_entities(fh.read()))
    except (ET.ParseError, UnicodeDecodeError):
        return None, None
    root = article_root(ET.ElementTree(tree))
    if not root:
        return None, None
    forms = {}
    for drv in tree.iter('drv'):
        kap = drv.find('kap')
        if kap is None:
            continue
        main, variants = headwords(kap, root)
        if main:
            forms[main.lower()] = (main, variants)
            # Also index without spaces and hyphens. A multi-word headword
            # reached us with its spaces already flattened away — that is the
            # other half of the same defect — so 'aleksandrolagranda' has to
            # find 'Aleksandro la Granda', and it can only do so on a key that
            # ignores the separators the merge dropped.
            forms.setdefault(squash(main), (main, variants))
    return root, forms


def article_name(root):
    name = root.lower()
    for letter, pair in (('ĉ', 'cx'), ('ĝ', 'gx'), ('ĥ', 'hx'),
                         ('ĵ', 'jx'), ('ŝ', 'sx'), ('ŭ', 'ux')):
        name = name.replace(letter, pair)
    return name


def find_article(directory, root):
    for candidate in (article_name(root), article_name(root).replace('-', ''),
                      article_name(root)[:-1], article_name(root)[:-2]):
        path = os.path.join(directory, candidate + '.xml')
        if len(candidate) >= 3 and os.path.exists(path):
            return path
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--articles', required=True)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--limit', type=int, default=12)
    args = parser.parse_args()

    with open(ENTRIES, encoding='utf-8') as fh:
        entries = [json.loads(line) for line in fh if line.strip()]

    cache = {}
    # A form-level index over every article fetched, used when the entry's own
    # root does not lead to the right article. The merge recorded the last
    # component of a compound as the root — aerarmeo came out with root 'arme'
    # rather than 'aer' — so those entries point at an article that is not
    # theirs. Matching on the form instead is sound as long as exactly one
    # article defines it; where two do, the entry is left alone.
    everywhere, ambiguous = {}, set()
    for name in sorted(os.listdir(args.articles)):
        if not name.endswith('.xml'):
            continue
        found_root, forms = index_article(os.path.join(args.articles, name))
        if not forms:
            continue
        for key, value in forms.items():
            if key in everywhere and everywhere[key][0] != value[0]:
                ambiguous.add(key)
            everywhere[key] = value

    recovered, respaced, unmatched = [], [], []
    no_article, wrong_article = [], []
    for entry in entries:
        raw = entry.get('revo_raw')
        long_head = (len(entry['word']) >= 18
                     and (entry.get('source') or '').startswith('ReVo'))
        if not raw and not long_head:
            continue
        root = entry.get('root')
        if not root:
            continue
        if root not in cache:
            path = find_article(args.articles, root)
            cache[root] = index_article(path) if path else (None, None)
        found_root, forms = cache[root]
        if not forms:
            no_article.append(entry['word'])
            continue
        # The fetcher retries a missing article under a shortened name and
        # caches the result under the name asked for, so aliz.xml can hold the
        # article for ali — a different word entirely. Repairing an entry from
        # an unrelated article is the one way this tool could invent a
        # headword, so the article has to say it is the root we wanted.
        if article_name(found_root) != article_name(root):
            forms = None
        match = None
        for key in (entry['word'].lower(), squash(entry['word'])):
            if forms and key in forms:
                match = forms[key]
                break
            if key in everywhere and key not in ambiguous:
                match = everywhere[key]
                if forms is None:
                    wrong_article.append(
                        '%s: root %s, matched elsewhere' % (entry['word'], root))
                break
        if not match:
            unmatched.append('%s (%s)' % (entry['word'], raw or 'long'))
            continue
        true_form, variants = match
        if true_form != entry['word'] or variants:
            (respaced if ' ' in true_form else recovered).append(
                '%-24s %-26s %s' % (raw or entry['word'], true_form,
                                    ', '.join(variants) or '—'))
        entry['word'] = true_form
        if variants:
            entry['variants'] = variants
        entry.pop('revo_raw', None)

    print('%sfrom %d articles' % ('' if args.apply else '[dry run] ',
                                  len(cache)))
    print('  %d entries repaired, of which %d regained a space'
          % (len(recovered) + len(respaced), len(respaced)))
    for row in recovered[:args.limit]:
        print('      %s' % row)
    for row in respaced[:args.limit]:
        print('      %s' % row)
    print('  %d had no article, %d had the wrong article, '
          '%d did not match their article'
          % (len(no_article), len(wrong_article), len(unmatched)))
    for row in wrong_article[:4]:
        print('      %s' % row)
    for row in unmatched[:6]:
        print('      %s' % row)

    if args.apply:
        with open(ENTRIES, 'w', encoding='utf-8') as fh:
            for entry in entries:
                fh.write(json.dumps(entry, ensure_ascii=False) + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
