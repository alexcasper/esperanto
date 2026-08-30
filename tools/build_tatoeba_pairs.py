#!/usr/bin/env python3
"""Build the English-Esperanto parallel sentence-pair dataset from the
Tatoeba exports fetched into RAW/tatoeba/ (GitHub issue #11, beads esp-tato).

Usage: python3 tools/build_tatoeba_pairs.py

Inputs (see RAW/tatoeba/README.md for digests):
  epo_sentences.tsv.bz2        id TAB lang TAB text  — all Esperanto
  eng_sentences.tsv.bz2        same, all English
  epo_sentences_CC0.tsv.bz2    CC0-only subsets; here just licence filters
  eng_sentences_CC0.tsv.bz2
  links.tar.bz2                one member, links.csv: id TAB id, both dirs
  sentences_base.tar.bz2       one member, sentences_base.csv:
                               sentence_id TAB base_id ('\\N' = original)

Outputs (CORPUS/tatoeba/):
  pairs.tsv        epo_id TAB eng_id TAB epo TAB eng TAB base_epo TAB base_eng
                   sorted by (epo_id, eng_id) — every en-epo link, all
                   licences (CC-BY 2.0 FR mix; attribution via Tatoeba)
  pairs_cc0.tsv    same schema, restricted to sentences present in the CC0
                   exports — the licence-clean subset (370 of Tatoeba's
                   ~821k Esperanto sentences are CC0, which is why the full
                   corpus exists at all)
  MANIFEST.tsv     per-input digest/row-count plus both outputs'

The join: a pair (epo sentence, eng sentence) exists for every links.csv row
with one endpoint in each language.  links.csv lists each link in both
directions, so pairs are normalized to (epo_id, eng_id) before dedup; a
sentence id can only belong to one language, so the two branches of that
normalization are mutually exclusive.

base_epo/base_eng come from sentences_base.csv: the id of the sentence each
side was entered as a translation of ('\\N' when the sentence is itself an
original) — i.e. who-translated-whom provenance, not a third text.

Sentences cannot contain tabs or newlines (the exports are themselves TSV),
which is asserted rather than assumed when writing.  As a licence sanity
check, every CC0 export sentence must match the full export's text for the
same id; any drift is an error, since it would move the CC0 subset's
boundary.
"""
import bz2
import hashlib
import io
import os
import sys
import tarfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAWT = os.path.join(ROOT, 'RAW', 'tatoeba')
OUT = os.path.join(ROOT, 'CORPUS', 'tatoeba')

EPO = os.path.join(RAWT, 'epo_sentences.tsv.bz2')
ENG = os.path.join(RAWT, 'eng_sentences.tsv.bz2')
EPO_CC0 = os.path.join(RAWT, 'epo_sentences_CC0.tsv.bz2')
ENG_CC0 = os.path.join(RAWT, 'eng_sentences_CC0.tsv.bz2')
LINKS = os.path.join(RAWT, 'links.tar.bz2')
BASE = os.path.join(RAWT, 'sentences_base.tar.bz2')
PAIRS = os.path.join(OUT, 'pairs.tsv')
PAIRS_CC0 = os.path.join(OUT, 'pairs_cc0.tsv')
MANIFEST = os.path.join(OUT, 'MANIFEST.tsv')


def sha256_of(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b''):
            digest.update(chunk)
    return digest.hexdigest()


def read_sentences(path):
    """id -> text from a Tatoeba per-language export (id TAB lang TAB text ...).

    Full exports are 3-column; CC0 exports carry a trailing date column.
    """
    want_lang = os.path.basename(path).split('_')[0]
    sentences = {}
    with bz2.open(path, 'rt', encoding='utf-8') as fh:
        for line in fh:
            fields = line.rstrip('\n').split('\t')
            if len(fields) < 3:
                raise ValueError('%s: short line %r' % (path, line[:60]))
            sid, lang, text = int(fields[0]), fields[1], fields[2]
            if lang != want_lang:
                raise ValueError('%s: unexpected lang %r' % (path, lang))
            if sid in sentences:
                raise ValueError('%s: duplicate id %d' % (path, sid))
            sentences[sid] = text
    return sentences


def iter_csv_member(tarball, member_name):
    """Yield stripped lines of member_name inside tarball, streaming."""
    with tarfile.open(tarball, 'r:bz2') as tar:
        for member in tar:
            if member.name != member_name:
                continue
            extracted = tar.extractfile(member)
            if extracted is None:
                break
            with io.TextIOWrapper(extracted, encoding='utf-8') as fh:
                for line in fh:
                    yield line.rstrip('\n')
            break
        else:
            # loop ran to completion: the member was never seen
            raise ValueError('%s: no member %r' % (tarball, member_name))


def main():
    inputs = {name: os.path.join(RAWT, name) for name in
              ('epo_sentences.tsv.bz2', 'eng_sentences.tsv.bz2',
               'epo_sentences_CC0.tsv.bz2', 'eng_sentences_CC0.tsv.bz2',
               'links.tar.bz2', 'sentences_base.tar.bz2')}
    for path in inputs.values():
        if not os.path.exists(path):
            raise SystemExit('%s missing; run tools/fetch_tatoeba.py first'
                             % path)
    os.makedirs(OUT, exist_ok=True)

    epo = read_sentences(EPO)
    eng = read_sentences(ENG)
    epo_cc0 = read_sentences(EPO_CC0)
    eng_cc0 = read_sentences(ENG_CC0)
    print('  sentences: epo=%d (cc0=%d) eng=%d (cc0=%d)'
          % (len(epo), len(epo_cc0), len(eng), len(eng_cc0)))

    # CC0 export texts must agree with the full export: the CC0 subset's
    # boundary depends on it.
    for label, cc0, full in (('epo', epo_cc0, epo), ('eng', eng_cc0, eng)):
        for sid, text in cc0.items():
            if full.get(sid) != text:
                raise SystemExit('%s CC0 id %d disagrees with full export'
                                 % (label, sid))
    epo_cc0_ids = frozenset(epo_cc0)
    eng_cc0_ids = frozenset(eng_cc0)

    pairs = set()
    total_links = 0
    for row in iter_csv_member(LINKS, 'links.csv'):
        fields = row.split('\t')
        if len(fields) != 2:
            raise ValueError('%s: bad link row %r' % (LINKS, row[:60]))
        total_links += 1
        a, b = int(fields[0]), int(fields[1])
        if a in epo and b in eng:
            pairs.add((a, b))
        elif a in eng and b in epo:
            pairs.add((b, a))
    print('  links scanned=%d -> %d en-epo pairs' % (total_links, len(pairs)))

    # base ids only for sentences that actually appear in a pair
    wanted = set()
    for epo_id, eng_id in pairs:
        wanted.add(epo_id)
        wanted.add(eng_id)
    base = {}
    for row in iter_csv_member(BASE, 'sentences_base.csv'):
        fields = row.split('\t')
        if len(fields) != 2:
            raise ValueError('%s: bad base row %r' % (BASE, row[:60]))
        sid = int(fields[0])
        if sid in wanted:
            base[sid] = fields[1]
    missing = wanted - set(base)
    if missing:
        raise SystemExit('sentences_base lacks %d pair-member ids, e.g. %s'
                         % (len(missing), sorted(missing)[:5]))
    originals = sum(1 for sid in wanted if base[sid] == '\\N')
    print('  base provenance: %d of %d member sentences are originals'
          % (originals, len(wanted)))

    def write_pairs(path, selected, note):
        ordered = sorted(selected)
        tmp = path + '.tmp'
        with open(tmp, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write('epo_id\teng_id\tepo\teng\tbase_epo\tbase_eng\n')
            for epo_id, eng_id in ordered:
                texts = (epo[epo_id], eng[eng_id])
                for text in texts:
                    if '\t' in text or '\n' in text:
                        raise ValueError('tab/newline in %d/%d: %r'
                                         % (epo_id, eng_id, text))
                fh.write('%d\t%d\t%s\t%s\t%s\t%s\n'
                         % (epo_id, eng_id, texts[0], texts[1],
                            base[epo_id], base[eng_id]))
        os.replace(tmp, path)
        print('  wrote %s (%d pairs, %s)' % (path, len(ordered), note))
        return len(ordered)

    n_all = write_pairs(PAIRS, pairs, 'all licences')
    n_cc0 = write_pairs(
        PAIRS_CC0,
        (p for p in pairs if p[0] in epo_cc0_ids and p[1] in eng_cc0_ids),
        'CC0 only')

    manifest = [('file', 'sha256', 'rows', 'note')]
    manifest.append(('epo_sentences.tsv.bz2', sha256_of(EPO)[:12], str(len(epo)),
                     'Tatoeba Esperanto sentences, all licences (CC-BY 2.0 FR mix)'))
    manifest.append(('eng_sentences.tsv.bz2', sha256_of(ENG)[:12], str(len(eng)),
                     'Tatoeba English sentences, all licences (CC-BY 2.0 FR mix)'))
    manifest.append(('epo_sentences_CC0.tsv.bz2', sha256_of(EPO_CC0)[:12],
                     str(len(epo_cc0)), 'CC0-only Esperanto subset (licence filter)'))
    manifest.append(('eng_sentences_CC0.tsv.bz2', sha256_of(ENG_CC0)[:12],
                     str(len(eng_cc0)), 'CC0-only English subset (licence filter)'))
    manifest.append(('links.tar.bz2', sha256_of(LINKS)[:12], str(total_links),
                     'all-language translation links, both directions (CC0)'))
    manifest.append(('sentences_base.tar.bz2', sha256_of(BASE)[:12],
                     str(len(base)), 'base-id provenance kept for pair members'))
    manifest.append(('pairs.tsv', sha256_of(PAIRS)[:12], str(n_all),
                     'en-epo pairs via links; sorted by (epo_id, eng_id)'))
    manifest.append(('pairs_cc0.tsv', sha256_of(PAIRS_CC0)[:12], str(n_cc0),
                     'subset with both sides in the CC0 exports'))
    with open(MANIFEST, 'w', encoding='utf-8', newline='\n') as fh:
        for row in manifest:
            fh.write('\t'.join(row) + '\n')
    print('  wrote %s' % MANIFEST)


if __name__ == '__main__':
    main()
