#!/usr/bin/env python3
"""Extract Esperanto message text from the soc.culture.esperanto Usenet
archive (GitHub issue #12, beads esp-r8p).

Usage: python3 tools/extract_usenet_esperanto.py

Input  RAW/usenet/soc.culture.esperanto.mbox  (fetch via tools/fetch_raw_usenet.py;
       digest recorded in RAW/usenet/README.md)
Output QUARANTINE/soc.culture.esperanto/extracted.tsv  — msgid, ISO date,
       author, subject, score, cleaned body text; one kept message per line,
       mbox order; plus MANIFEST.tsv with input/output digests and counts.

The licence question is decided by placement, not omission: Usenet posts are
per-poster copyright and the archive.org item declares nothing, so the
extraction lives under QUARANTINE/ and never reaches CORPUS/ (pg-23586
precedent). The blobs stay in RAW/usenet/ as provenance.

Pipeline per message:
  * split on mbox envelope lines with a strict 'From <sender> <weekday> ...'
    pattern — stdlib mailbox.mbox refuses this archive (non-ASCII bytes in
    unsanitized body 'From ' lines), and the pattern recovered exactly the
    69,804 messages the archive item advertises
  * text/plain part only (multipart walk; HTML-only posts are dropped),
    decoded via declared charset then utf-8, iso-8859-3 (the pre-Unicode
    Esperanto standard), iso-8859-1, cp1252, then errors=replace
  * strip Usenet quoting ('>' lines), signatures (after a '-- ' line),
    uuencode/base64/PGP blocks; flatten to one line
  * x-system folding: when a body carries x-digraphs but essentially no
    diacritics, it is pre-Unicode ascii Esperanto ('jhurnalo' era) and is
    folded to UTF-8 with tools/normalize_corpus.py's mapping — a body that
    already has diacritics is left alone so foreign 'aux'/'eaux' stays
    intact
  * score against the DICT/entries.jsonl vocabulary (tools/
    score_esperanto_text.py): share of tokens recognised as Esperanto.
    Threshold 0.70 was calibrated on the whole group: below 0.3 is English
    chatter and make-money-fast spam, 0.5-0.6 still holds German spam and
    mixed-language threads, and 0.7+ samples as clean Esperanto — the
    vocabulary misses proper nouns, so genuine posts sit below 1.0.
    Bodies with fewer than 10 tokens are unscoreable and dropped.

Deterministic: same mbox bytes -> same extracted.tsv bytes.
"""
import email
import email.utils
import hashlib
import io
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import normalize_corpus as nc
import score_esperanto_text as ses

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MBOX = os.path.join(ROOT, 'RAW', 'usenet', 'soc.culture.esperanto.mbox')
OUTDIR = os.path.join(ROOT, 'QUARANTINE', 'soc.culture.esperanto')
OUT = os.path.join(OUTDIR, 'extracted.tsv')
MANIFEST = os.path.join(OUTDIR, 'MANIFEST.tsv')

MIN_TOKENS = 10
MIN_SCORE = 0.70
XSYSTEM_MIN = 3          # x-digraph hits before a diacritic-free body is folded
DIACRITIC_MAX_RATIO = 0.02
FALLBACKS = ['utf-8', 'iso-8859-3', 'iso-8859-1', 'cp1252']

ENVELOPE = re.compile(
    rb'^From \S{1,64} +(Mon|Tue|Wed|Thu|Fri|Sat|Sun) +'
    rb'((\d{1,2} +(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec))'
    rb'|((Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) +\d{1,2}))'
    rb'.*\d{4}', re.M)
QUOTE = re.compile(r'^\s{0,3}(>|\|)')
SIG = re.compile(r'^-- ?$|^---+$|^_{5,}$')
BLOCK = re.compile(r'^(begin \d|[A-Za-z0-9+/]{60,}={0,2}$|-----BEGIN)')


def sha256_of(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b''):
            digest.update(chunk)
    return digest.hexdigest()


def decode_payload(part):
    payload = part.get_payload(decode=True)
    if payload is None:
        return ''
    for cs in [part.get_content_charset() or 'utf-8'] + FALLBACKS:
        try:
            return payload.decode(cs)
        except (UnicodeDecodeError, LookupError):
            continue
    return payload.decode('utf-8', errors='replace')


def body_of(msg):
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == 'text/plain' \
                    and not part.get_filename():
                return decode_payload(part)
        return ''
    if msg.get_content_type() == 'text/plain':
        return decode_payload(msg)
    return ''


def clean(body):
    out, in_sig, in_block = [], False, False
    for line in body.splitlines():
        if BLOCK.match(line):
            in_block = True
        elif not line.strip() and in_block:
            in_block = False
        if in_sig or in_block or QUOTE.match(line):
            continue
        if SIG.match(line):
            in_sig = True
            continue
        line = line.strip()
        if len(line) > 1:
            out.append(line)
    return ' '.join(out)


def fold_xsystem(text):
    """Fold ascii x-digraphs to diacritics only for diacritic-free bodies
    that clearly use the x-system (normalize_corpus's mapping, message-scale
    gate — the file-scale XSYS_MIN=100 does not apply to one message)."""
    hits = nc.xsystem_hits(text)
    if hits < XSYSTEM_MIN:
        return text, False
    if len(nc.DIACRITIC.findall(text)) > hits * DIACRITIC_MAX_RATIO:
        return text, False
    return nc.to_utf8_diacritics(text), True


def iso_date(msg):
    try:
        return email.utils.parsedate_to_datetime(
            msg.get('date')).strftime('%Y-%m-%d')
    except Exception:
        return ''


def field(value):
    return re.sub(r'[\t\n\r]+', ' ', str(value or '')).strip()


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--mbox', default=MBOX,
                    help='input mbox (default: RAW/usenet/soc.culture.esperanto.mbox)')
    ap.add_argument('--outdir', default=OUTDIR,
                    help='output dir (default: QUARANTINE/soc.culture.esperanto)')
    args = ap.parse_args()
    if not os.path.exists(args.mbox):
        raise SystemExit('%s missing; run tools/fetch_raw_usenet.py first'
                         % args.mbox)
    os.makedirs(args.outdir, exist_ok=True)
    out = os.path.join(args.outdir, 'extracted.tsv')
    manifest = os.path.join(args.outdir, 'MANIFEST.tsv')

    with open(args.mbox, 'rb') as fh:
        data = fh.read()
    starts = [m.start() for m in ENVELOPE.finditer(data)]

    roots, words = ses.load_vocabulary()
    kept = scored = skipped_short = dropped = folded = 0
    per_year = {}
    tmp = out + '.tmp'
    with open(tmp, 'w', encoding='utf-8', newline='\n') as out:
        out.write('msgid\tdate\tauthor\tsubject\tscore\ttext\n')
        for i, start in enumerate(starts):
            end = starts[i + 1] if i + 1 < len(starts) else len(data)
            msg = email.message_from_bytes(data[start:end])
            body = clean(body_of(msg))
            body, was_folded = fold_xsystem(body)
            tokens = ses.TOKEN.findall(body)
            if len(tokens) < MIN_TOKENS:
                skipped_short += 1
                continue
            scored += 1
            hits = sum(1 for t in tokens if ses.recognised(t, roots, words))
            s = hits / len(tokens)
            if s < MIN_SCORE:
                dropped += 1
                continue
            kept += 1
            folded += was_folded
            year = iso_date(msg)[:4]
            if year:
                per_year[year] = per_year.get(year, 0) + 1
            out.write('%s\t%s\t%s\t%s\t%.3f\t%s\n' % (
                field(msg.get('message-id')), iso_date(msg),
                field(email.utils.parseaddr(msg.get('from'))[0]),
                field(msg.get('subject')), s, field(body)))
    os.replace(tmp, out)

    with open(manifest, 'w', encoding='utf-8', newline='\n') as fh:
        rows = [
            ('file', 'sha256', 'rows', 'note'),
            (os.path.basename(args.mbox), sha256_of(args.mbox)[:12],
             str(len(starts)), 'RAW/usenet input; 69,804 Usenet messages'),
            ('extracted.tsv', sha256_of(out)[:12], str(kept),
             'Esperanto messages: score>=%.2f, >=%d tokens; quote/sig-stripped '
             'text/plain bodies; %d x-system-folded; LICENCE-HOLD: do not '
             'promote to CORPUS without a ruling'
             % (MIN_SCORE, MIN_TOKENS, folded)),
        ]
        for row in rows:
            fh.write('\t'.join(row) + '\n')

    print('messages=%d scored=%d kept=%d dropped_below_%.2f=%d short=%d'
          % (len(starts), scored, kept, MIN_SCORE, dropped, skipped_short))
    print('x-system-folded bodies=%d' % folded)
    print('years kept: %s' % ', '.join(
        '%s:%d' % (y, n) for y, n in sorted(per_year.items())[:5]),
        '...', '%s:%d' % max(per_year.items()))
    print('wrote %s and %s' % (out, manifest))


if __name__ == '__main__':
    main()
