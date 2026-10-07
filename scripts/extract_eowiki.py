#!/usr/bin/env python3
"""Extract curated Vikipedio (eo.wikipedia) articles from a pages-articles
dump into RAW/ as wp-<Title>.txt (esp-4g8).

Dump: https://dumps.wikimedia.org/eowiki/<date>/eowiki-<date>-pages-articles
-multistream.xml.bz2 — the dump file, per the bead's robots/AI-policy rule
(no live scraping of article pages). Python's bz2 reads multistream
(concatenated-stream) files transparently.

Two passes:

  stats   Parse every ns-0 page, strip wiki furniture, write a per-article
          TSV (title, redirect, raw_chars, clean_chars) so the curation
          cutoff is chosen from the real size distribution, not a guess.

  write   Emit RAW/wp-<Title>.txt for articles passing the curation rule
          (cleaned-prose size in [MIN, MAX] chars), sha256-deduped against
          existing RAW/*.txt. Titles use underscores like the existing
          ia-eowiki-* files. RAW/ keeps fetched-text convention: files hold
          cleaned plain prose (no wikitext, templates, refs, tables,
          categories), so normalize_corpus.py treats them like wsdump-* —
          already clean, shared cleanup only.

Sections dropped as furniture (list/reference material, not prose):
Referencoj, Fontoj, Notoj, Eksteraj ligiloj, Vidu ankaŭ, Bibliografio,
Literaturo, Piednoto(j), Rilataj artikoloj.
"""
import argparse
import bz2
import hashlib
import os
import re
import sys
import xml.etree.ElementTree as ET

from mwparserfromhell import parse as wikistring_parse

# Section headings whose whole section is reference/navigation furniture.
DROP_SECTIONS = {
    'referencoj', 'fontoj', 'notoj', 'eksteraj ligiloj', 'vidu ankaŭ',
    'bibliografio', 'literaturo', 'piednoto', 'piednotoj', 'fontnotoj',
    'rilataj artikoloj', 'ekstera ligilo', 'plia legado',
}

REDIRECT = re.compile(r'^#(?:REDIRECT|ALIDIREKTI)', re.IGNORECASE)


def iter_pages(dump_path):
    """Yield (title, ns, is_redirect, wikitext) for every page in the dump."""
    with bz2.open(dump_path, 'rb') as fh:
        context = ET.iterparse(fh, events=('end',))
        for _, elem in context:
            if not elem.tag.endswith('}page'):
                continue
            title = elem.findtext('./{*}title') or ''
            ns = elem.findtext('./{*}ns') or ''
            redirect = elem.find('./{*}redirect') is not None
            text = elem.findtext('./{*}revision/{*}text') or ''
            yield title, ns, redirect, text
            elem.clear()


def strip_section_level(code, drop_names):
    """mwparserfromhell filter_headings gives no parent-section access, so
    walk the section skeleton ourselves: find headings by level, delete the
    spans of sections whose heading matches drop_names."""
    import mwparserfromhell as mw
    offsets = []
    for match in re.finditer(r'^(={2,6})\s*(.+?)\s*\1\s*$', code,
                             re.MULTILINE):
        offsets.append((match.start(), match.end(),
                        match.group(2).strip().lower(), len(match.group(1))))
    killed = []
    for i, (start, end, name, level) in enumerate(offsets):
        if name.split('[')[0].strip() in drop_names:
            nxt = offsets[i + 1] if i + 1 < len(offsets) else None
            # Section ends at the next heading of level <= this one.
            stop = nxt[0] if nxt and nxt[3] <= level else len(code)
            if stop > start:
                killed.append((start, stop))
    for start, stop in reversed(killed):
        code = code[:start] + code[stop:]
    return code


def clean_wikitext(text):
    """Wikitext -> plain prose. Drop templates, tables, refs, comments,
    headings; keep internal-link text and external-link labels."""
    if REDIRECT.match(text.strip()):
        return None, True
    text = re.sub(r'<!--.*?-->', '', text, flags=re.DOTALL)
    text = re.sub(r'<ref[^>]*?/>', '', text)
    text = re.sub(r'<ref[^>]*?>.*?</ref>', '', text, flags=re.DOTALL)
    text = re.sub(r'<gallery[^>]*?>.*?</gallery>', '', text, flags=re.DOTALL)
    # Namespace links must go while the brackets still exist — strip_code
    # would render their titles as prose.
    text = re.sub(r'\[\[(?:Kategorio|Dosiero|File|Image|Kategorio)\s*:[^\]]*\]\]',
                  '', text, flags=re.IGNORECASE)
    text = strip_section_level(text, DROP_SECTIONS)
    try:
        code = wikistring_parse(text)
    except Exception:
        return None, False
    # Remove templates and non-prose tags at node level first: they can span
    # many lines, and line-oriented regexes would slice them open and leave
    # their parameter text behind as prose. Removing a parent invalidates the
    # other handles from the same filter() round, so retry until stable.
    for _ in range(4):
        victims = list(code.filter_templates(recursive=True))
        victims += [t for t in code.filter_tags(recursive=True)
                    if str(t.tag).lower() in ('table', 'ref', 'gallery',
                                              'references', 'nowiki')]
        if not victims:
            break
        for node in victims:
            try:
                code.remove(node)
            except ValueError:
                pass  # already gone with an enclosing node
    # Now that templates/tables are gone, list and indent lines are genuinely
    # list furniture — strip_code would eat only the marker and keep the item
    # text, so drop whole lines while the markers are still visible.
    text = str(code)
    text = re.sub(r'^\s*[|!].*$', '', text, flags=re.MULTILINE)  # table rest
    text = re.sub(r'^\s*[*#:;].*$', '', text, flags=re.MULTILINE)  # lists
    try:
        code = wikistring_parse(text)
    except Exception:
        return None, False
    text = code.strip_code(normalize=True, collapse=False)
    text = re.sub(r'\s+', ' ', text)
    # Orphan wiki punctuation mwparserfromhell couldn't attribute to a node
    # (malformed/unbalanced markup): stray braces and bracket tails.
    text = re.sub(r'\{\{|\}\}', ' ', text)
    text = re.sub(r'\(\s*\)|\[\s*\]', ' ', text)
    # Leading punctuation-only fragment before the first letter (e.g.
    # '-1)]]' from a chewed template): trim if short.
    m = re.match(r'^[\s)\]}.,;:!?\-–—„"\'«0-9]+', text)
    if m and len(m.group()) < 15:
        text = text[m.end():]
    return text.strip(), False


def title_to_name(title):
    # Slashes appear in titles (e.g. 'AC/DC', 'Listo de Zamenhof/…') and
    # would turn into subdirectory paths — flatten to an underscore.
    name = title.replace(' ', '_').replace('/', '_')
    return 'wp-' + name + '.txt'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('command', choices=['stats', 'write'])
    ap.add_argument('dump')
    ap.add_argument('--out', default='RAW')
    ap.add_argument('--stats-tsv')
    ap.add_argument('--min-chars', type=int, default=0)
    ap.add_argument('--max-chars', type=int, default=10 ** 9)
    ap.add_argument('--limit', type=int, default=0, help='cap file count (0=all)')
    args = ap.parse_args()

    if args.command == 'stats':
        out_tsv = args.stats_tsv or 'eowiki-stats.tsv'
        n = 0
        with open(out_tsv, 'w', encoding='utf-8') as fh:
            fh.write('title\tredirect\traw_chars\tclean_chars\n')
            for title, ns, redirect, text in iter_pages(args.dump):
                if ns != '0':
                    continue
                n += 1
                if n % 20000 == 0:
                    print('  ...%d ns0 pages' % n, file=sys.stderr)
                if redirect or REDIRECT.match(text.strip()):
                    fh.write('%s\t1\t%d\t0\n' % (title, len(text)))
                    continue
                clean, is_redir = clean_wikitext(text)
                fh.write('%s\t%d\t%d\t%d\n' % (
                    title, 1 if is_redir else 0, len(text),
                    len(clean or '')))
        print('wrote %s (%d ns0 pages)' % (out_tsv, n))
        return

    # write pass --------------------------------------------------------
    raw_dir = args.out
    existing = {}
    for name in os.listdir(raw_dir):
        if name.endswith('.txt'):
            p = os.path.join(raw_dir, name)
            if os.path.islink(p):
                p = os.path.realpath(p)
            with open(p, 'rb') as fh:
                existing[hashlib.sha256(fh.read()).hexdigest()] = name

    written = dup = skipped = 0
    for title, ns, redirect, text in iter_pages(args.dump):
        if ns != '0' or redirect:
            continue
        clean, is_redir = clean_wikitext(text)
        if is_redir or not clean:
            skipped += 1
            continue
        if not (args.min_chars <= len(clean) <= args.max_chars):
            skipped += 1
            continue
        out_text = clean + '\n'
        h = hashlib.sha256(out_text.encode('utf-8')).hexdigest()
        if h in existing:
            dup += 1
            continue
        name = title_to_name(title)
        if name in existing.values():
            # Same filename, different content (dump revision) — keep the
            # new one; provenance records the dump date.
            pass
        with open(os.path.join(raw_dir, name), 'w', encoding='utf-8') as fh:
            fh.write(out_text)
        existing[h] = name
        written += 1
        if args.limit and written >= args.limit:
            break
    print('written=%d dup=%d skipped=%d' % (written, dup, skipped))


if __name__ == '__main__':
    main()
