#!/usr/bin/env python3
"""Mine corpus attestations and literary citations for dictionary entries.

Scans the literary and historical corpus in CORPUS/ to compute:
  - attestation: {"count": total_occurrences, "sources": independent_source_count}
  - citations: up to 3 high-quality literary sentences illustrating the word in context,
    prioritizing classical Gutenberg and Wikisource literature (pg-*.txt, wsdump-*.txt).

Usage:
  python3 tools/mine_concordance.py [--dry-run] [--min-sources 1]
"""
import argparse
import glob
import json
import os
import re
import sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORPUS = os.path.join(ROOT, 'CORPUS')
ENTRIES = os.path.join(ROOT, 'DICT', 'entries.jsonl')

sys.path.insert(0, os.path.join(ROOT, 'tools'))
import mine_lemmas

EXCLUDE = set(mine_lemmas.ENGLISH_HEAVY) | set(mine_lemmas.MULTILINGUAL) | set(mine_lemmas.OCR_POOR)

TOKEN_RE = re.compile(r"[a-zA-ZĉĝĥĵŝŭĈĜĤĴŜŬ']+")

def build_form_index(entries):
    """Map lowercased surface forms to the list of entry indices they represent."""
    form_to_indices = defaultdict(list)
    for idx, e in enumerate(entries):
        w = e['word'].lower()
        pos = e.get('pos')
        forms = [w]
        if w.endswith('o') and pos == 'noun':
            stem = w[:-1]
            forms.extend([stem + 'on', stem + 'oj', stem + 'ojn'])
        elif w.endswith('a') and pos == 'adj':
            stem = w[:-1]
            forms.extend([stem + 'an', stem + 'aj', stem + 'ajn'])
        elif w.endswith('i') and pos == 'verb':
            stem = w[:-1]
            forms.extend([stem + 'as', stem + 'is', stem + 'os', stem + 'us', stem + 'u',
                          stem + 'ante', stem + 'inte', stem + 'onte',
                          stem + 'ata', stem + 'ita', stem + 'ota',
                          stem + 'anta', stem + 'inta', stem + 'onta'])
        elif w.endswith('e') and pos == 'adv':
            stem = w[:-1]
            forms.extend([stem + 'en'])
        
        for f in forms:
            form_to_indices[f].append(idx)
    return form_to_indices

def score_source_priority(fname):
    """Prioritize high-quality edited texts (Gutenberg, Wikisource) over raw scans."""
    if fname.startswith('pg-'):
        return 0  # Project Gutenberg (highest proofread quality)
    if fname.startswith('wsdump-') or fname.startswith('wsrc-'):
        return 1  # Wikisource library
    if fname.startswith('ia-'):
        return 2  # Internet Archive / Usenet
    if fname.startswith('wp-'):
        return 3  # Vikipedio (encyclopedic, modern)
    return 2  # Other sources

def mine(entries, min_sources=1):
    form_to_indices = build_form_index(entries)

    # Collect corpus files sorted by quality priority
    all_files = glob.glob(os.path.join(CORPUS, '*.txt'))
    corpus_files = [f for f in all_files if os.path.basename(f) not in EXCLUDE]
    corpus_files.sort(key=lambda f: (score_source_priority(os.path.basename(f)), f))

    entry_counts = defaultdict(int)
    entry_sources_lit = defaultdict(set)
    entry_sources_wiki = defaultdict(set)
    # entry_citations: idx -> list of (priority, source, lineno, text)
    entry_citations = defaultdict(list)

    print(f"Scanning {len(corpus_files)} corpus files for {len(entries)} dictionary entries...")

    for fpath in corpus_files:
        fname = os.path.basename(fpath)
        prio = score_source_priority(fname)
        is_wiki = fname.startswith('wp-')
        with open(fpath, encoding='utf-8') as fh:
            for lineno, line in enumerate(fh, 1):
                line_str = line.strip()
                if not line_str:
                    continue

                matched_indices = set()
                for m in TOKEN_RE.finditer(line):
                    t = m.group().lower()
                    if t in form_to_indices:
                        for idx in form_to_indices[t]:
                            entry_counts[idx] += 1
                            if is_wiki:
                                entry_sources_wiki[idx].add(fname)
                            else:
                                entry_sources_lit[idx].add(fname)
                            matched_indices.add(idx)

                # Collect clean citation snippet
                if 35 <= len(line_str) <= 180 and matched_indices:
                    clean_snippet = ' '.join(line_str.split())
                    for idx in matched_indices:
                        cites = entry_citations[idx]
                        if len(cites) < 5 and not any(c['source'] == fname for c in cites):
                            cites.append({
                                'source': fname,
                                'text': clean_snippet,
                                '_prio': prio
                            })

    # Enrich entries
    enriched_count = 0
    cites_added = 0

    for idx, e in enumerate(entries):
        cnt = entry_counts[idx]
        lit_srcs = len(entry_sources_lit[idx])
        wiki_srcs = len(entry_sources_wiki[idx])
        total_srcs = lit_srcs + wiki_srcs

        # Update attestation with register breakdown
        if cnt > 0:
            e['attestation'] = {
                'count': cnt,
                'sources': total_srcs,
                'sources_lit': lit_srcs,
                'sources_wiki': wiki_srcs,
            }
            enriched_count += 1

        # Add citations if none present
        if not e.get('citations') and entry_citations[idx]:
            # Sort by priority and take up to 3
            sorted_cites = sorted(entry_citations[idx], key=lambda c: c.get('_prio', 99))
            picked = [{'source': c['source'], 'text': c['text']} for c in sorted_cites[:3]]
            if picked:
                e['citations'] = picked
                cites_added += 1
        elif e.get('citations'):
            # Strip any internal fields
            for c in e['citations']:
                c.pop('_prio', None)

    print(f"Results: {enriched_count} entries updated with attestations, {cites_added} new entries given citations.")
    total_with_cites = sum(1 for e in entries if e.get('citations'))
    print(f"Total entries with citations: {total_with_cites} / {len(entries)} ({total_with_cites/len(entries)*100:.1f}%)")
    return entries

def main():
    doc_first = (__doc__ or '').splitlines()[0]
    parser = argparse.ArgumentParser(description=doc_first)
    parser.add_argument('--dry-run', action='store_true', help='Scan and print stats without writing')
    parser.add_argument('--min-sources', type=int, default=1, help='Minimum sources to attach citation')
    args = parser.parse_args()

    entries = [json.loads(l) for l in open(ENTRIES, encoding='utf-8') if l.strip()]
    enriched = mine(entries, min_sources=args.min_sources)

    if args.dry_run:
        print("Dry run completed; no files written.")
        return 0

    tmp = ENTRIES + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as fh:
        for entry in enriched:
            fh.write(json.dumps(entry, ensure_ascii=False) + '\n')
    os.replace(tmp, ENTRIES)
    print(f"Wrote updated dictionary to {ENTRIES}")
    return 0

if __name__ == '__main__':
    sys.exit(main())
