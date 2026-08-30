#!/usr/bin/env python3
"""Fetch the Tatoeba exports needed for the English-Esperanto parallel
corpus into RAW/tatoeba/ (GitHub issue #11, beads esp-tato).

Usage: python3 tools/fetch_tatoeba.py [--dry-run]

  epo_sentences_CC0.tsv.bz2   Esperanto sentences whose licence is CC0
  eng_sentences_CC0.tsv.bz2   ditto, English
  links.tar.bz2               sentence-id -> sentence-id translation links
  epo_sentences.tsv.bz2       all Esperanto sentences (CC0 + CC-BY mix)
  eng_sentences.tsv.bz2       ditto, English
  sentences_base.tar.bz2      sentence_id -> base_id ('translated from'),
                              all sentences, '\\N' for originals

Issue #11 named the first three: the CC0 exports give a licence-clean join,
but only ~370 of Tatoeba's Esperanto sentences are CC0 (0.05% of the
language), so the full per-language exports were added to lift that ceiling —
CORPUS/tatoeba/ then ships pairs.tsv (all licences; Tatoeba's full exports
are CC-BY 2.0 FR, attribution required) next to pairs_cc0.tsv (licence-clean
subset).  sentences_base supplies the base sentence id kept as provenance
columns in both outputs.  The links table itself is distributed under CC0
(https://tatoeba.org/en/exports).

Unlike the other fetchers, downloads go to disk with a temp-file rename:
links.tar.bz2 is ~150 MB (the sandbox proxy is fine with that, in-memory
buffers are not).  Existing files are checksum-verified and skipped, so the
tool is idempotent; a file present with no recorded digest is an error, never
a silent re-download.  RAW/tatoeba/ holds only derived-from-network blobs:
the directory is gitignored wholesale, RAW/tatoeba/README.md records the
digests.
"""
import argparse
import hashlib
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'RAW', 'tatoeba')
README = os.path.join(OUT, 'README.md')

EXPORTS = 'https://downloads.tatoeba.org/exports'
RETRIES = 4
# links.tar.bz2 is ~150 MB; the sentence exports are MB-scale.
TIMEOUT_LARGE = 1800
TIMEOUT_SMALL = 300

FILES = [
    # (remote path, curl timeout)
    ('per_language/epo/epo_sentences_CC0.tsv.bz2', TIMEOUT_SMALL),
    ('per_language/eng/eng_sentences_CC0.tsv.bz2', TIMEOUT_SMALL),
    ('per_language/epo/epo_sentences.tsv.bz2', TIMEOUT_SMALL),
    ('per_language/eng/eng_sentences.tsv.bz2', TIMEOUT_SMALL),
    ('sentences_base.tar.bz2', TIMEOUT_LARGE),
    ('links.tar.bz2', TIMEOUT_LARGE),
]


def sha256_of(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b''):
            digest.update(chunk)
    return digest.hexdigest()


def curl_to_file(url, dest, timeout):
    """Stream url to dest.tmp then rename; retry with backoff. Returns digest."""
    tmp = dest + '.tmp'
    last = ''
    for attempt in range(RETRIES):
        out = subprocess.run(['curl', '-sSL', '-m', str(timeout),
                              '--retry', '3', '-o', tmp, url],
                             capture_output=True)
        if out.returncode == 0 and os.path.getsize(tmp) > 0:
            os.replace(tmp, dest)
            return sha256_of(dest)
        last = out.stderr.decode()[:160] or 'empty response'
        if os.path.exists(tmp):
            os.remove(tmp)
        print('    retry %d/%d %s (%s)' % (attempt + 1, RETRIES, url, last),
              file=sys.stderr)
        time.sleep(2 * (attempt + 1))
    raise IOError('%s: %s' % (url, last))


def read_recorded():
    """filename -> sha256 as recorded in RAW/tatoeba/README.md."""
    recorded = {}
    if not os.path.exists(README):
        return recorded
    with open(README, encoding='utf-8') as fh:
        for line in fh:
            if line.startswith('- `') and 'sha256:' in line:
                name = line.split('`')[1]
                digest = line.split('sha256:')[1].split()[0]
                recorded[name] = digest
    return recorded


def append_readme(rel, digest, size):
    name = os.path.basename(rel)
    entry = ('- `%s` — Tatoeba export — sha256:%s — %s bytes — %s/%s\n'
             % (name, digest[:12], format(size, ','), EXPORTS, rel))
    with open(README, 'a', encoding='utf-8') as fh:
        fh.write(entry)
    return entry.rstrip('\n')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true',
                    help='report what would be fetched, change nothing')
    args = ap.parse_args()

    recorded = read_recorded()
    os.makedirs(OUT, exist_ok=True)

    for rel, timeout in FILES:
        name = os.path.basename(rel)
        dest = os.path.join(OUT, name)
        url = '%s/%s' % (EXPORTS, rel)

        if os.path.exists(dest):
            digest = sha256_of(dest)
            # README records truncated digests (12 hex) per repo convention.
            if recorded.get(name, '').startswith(digest[:12]):
                print('  have %s (sha256:%s) — skip' % (name, digest[:12]))
                continue
            want = recorded.get(name)
            raise SystemExit(
                '%s exists (sha256:%s) but RAW/tatoeba/README.md records %s; '
                'move it aside or fix the README.' %
                (name, digest[:12], want[:12] if want else 'nothing'))

        if args.dry_run:
            print('  would fetch %s -> %s' % (url, dest))
            continue

        print('  fetching %s ... ' % name)
        sys.stdout.flush()
        digest = curl_to_file(url, dest, timeout)
        size = os.path.getsize(dest)
        print('    sha256:%s (%s bytes)' % (digest[:12], format(size, ',')))
        print('    ' + append_readme(rel, digest, size))


if __name__ == '__main__':
    main()
