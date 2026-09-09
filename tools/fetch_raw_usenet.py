#!/usr/bin/env python3
"""Fetch the soc.culture.esperanto Usenet archive into RAW/usenet/
(GitHub issue #12, beads esp-r8p).

Issue #12 points at Google Groups' mirror of the newsgroup
(https://groups.google.com/search/conversations?q=soc.culture.esperanto),
but that front-end is JS-rendered and scraping it is hostile; the group is
better obtained whole from the Internet Archive, which hosts a complete
mbox backup as a single 7z:

  item  FULL-USENET-BACKUP-2020-Oct-soc.culture.esperanto.69804.mbox.7z
        (collection 'usenet', 69,804 messages through Oct 2020)
  file  soc.culture.esperanto.(69804).mbox.7z   — 27,755,969 bytes
        https://archive.org/details/FULL-USENET-BACKUP-2020-Oct-soc.culture.esperanto.69804.mbox.7z

A second, smaller snapshot (Giganews, July 2014) exists as plain .mbox.gz in
archive.org item 'usenet-soc.culture' and needs no 7z support; it is recorded
here as the fallback but not fetched.

No licence is declared on either item: Usenet posts remain per-poster
copyright. The blobs therefore land in RAW/ only as provenance-keeping —
extraction output goes to QUARANTINE/soc.culture.esperanto/ and never
reaches CORPUS/ (see that README; pg-23586 precedent).

7z extraction uses py7zr when importable, else the 7z/7zz binary; with
neither, the tool still fetches and digest-records the 7z and says how to
extract by hand. Like fetch_tatoeba.py: idempotent, digest-verified skips,
atomic temp-file rename, no silent re-download. Blobs are gitignored;
RAW/usenet/README.md is the durable record.
"""
import argparse
import hashlib
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'RAW', 'usenet')
README = os.path.join(OUT, 'README.md')

# archive.org item URL: <item>/<file>, parentheses percent-encoded.
ITEM = 'FULL-USENET-BACKUP-2020-Oct-soc.culture.esperanto.69804.mbox.7z'
ARCHIVE_URL = ('https://archive.org/download/%s/'
               'soc.culture.esperanto.%%2869804%%29.mbox.7z' % ITEM)
SEVENZ = os.path.join(OUT, 'soc.culture.esperanto.69804.mbox.7z')
MBOX = os.path.join(OUT, 'soc.culture.esperanto.mbox')

RETRIES = 4
TIMEOUT = 1800
EXPECTED_SIZE = 27755969


def sha256_of(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b''):
            digest.update(chunk)
    return digest.hexdigest()


def read_recorded():
    recorded = {}
    if not os.path.exists(README):
        return recorded
    with open(README, encoding='utf-8') as fh:
        for line in fh:
            if line.startswith('- `') and 'sha256:' in line:
                name = line.split('`')[1]
                recorded[name] = line.split('sha256:')[1].split()[0]
    return recorded


def append_readme(name, digest, size, note):
    entry = ('- `%s` — %s — sha256:%s — %s bytes\n' %
             (name, note, digest[:12], format(size, ',')))
    with open(README, 'a', encoding='utf-8') as fh:
        fh.write(entry)
    return entry.rstrip('\n')


def extract_7z(src, dest):
    """Extract the single mbox member of the archive to dest."""
    tmp = dest + '.tmp'
    try:
        import py7zr  # noqa: cheap probe
        import py7zr as _p
        with _p.SevenZipFile(src) as z:
            names = z.getnames()
            if len(names) != 1:
                raise IOError('expected 1 member, found %d: %s'
                              % (len(names), names[:3]))
            outdir = dest + '.x'
            os.makedirs(outdir, exist_ok=True)
            z.extractall(outdir)
            inner = os.path.join(outdir, names[0])
            os.replace(inner, tmp)
            os.rmdir(outdir)
    except ImportError:
        for binary in ('7zz', '7z'):
            try:
                out = subprocess.run([binary, 'x', '-so', src],
                                     capture_output=True)
            except FileNotFoundError:
                continue
            if out.returncode == 0 and out.stdout:
                with open(tmp, 'wb') as fh:
                    fh.write(out.stdout)
                os.replace(tmp, dest)
                return
        raise SystemExit('no 7z support under this python: pip install py7zr '
                         '(or install 7-zip), then rerun; the archive is at '
                         '%s' % src)
    os.replace(tmp, dest)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true',
                    help='report what would happen, change nothing')
    args = ap.parse_args()

    recorded = read_recorded()
    os.makedirs(OUT, exist_ok=True)

    if os.path.exists(SEVENZ):
        digest = sha256_of(SEVENZ)
        if recorded.get('soc.culture.esperanto.69804.mbox.7z', '').startswith(
                digest[:12]):
            print('  have archive (sha256:%s) — skip fetch' % digest[:12])
        else:
            raise SystemExit('%s exists but its digest is not recorded in '
                             'RAW/usenet/README.md; move it aside or fix the '
                             'README.' % SEVENZ)
    elif args.dry_run:
        print('  would fetch %s' % ARCHIVE_URL)
    else:
        print('  fetching %s ... ' % os.path.basename(SEVENZ))
        sys.stdout.flush()
        tmp = SEVENZ + '.tmp'
        last = ''
        for attempt in range(RETRIES):
            out = subprocess.run(['curl', '-sSL', '-m', str(TIMEOUT),
                                  '--retry', '3', '-o', tmp, ARCHIVE_URL],
                                 capture_output=True)
            if out.returncode == 0 and os.path.getsize(tmp) == EXPECTED_SIZE:
                os.replace(tmp, SEVENZ)
                digest = sha256_of(SEVENZ)
                print('    sha256:%s' % digest[:12])
                print('    ' + append_readme('soc.culture.esperanto.69804.mbox.7z',
                                             digest, EXPECTED_SIZE,
                                             'archive.org FULL-USENET-BACKUP-2020-Oct'))
                break
            last = out.stderr.decode()[:160] or (
                'size %s != %s' % (os.path.getsize(tmp)
                                   if os.path.exists(tmp) else '?',
                                   EXPECTED_SIZE))
            if os.path.exists(tmp):
                os.remove(tmp)
            print('    retry %d/%d (%s)' % (attempt + 1, RETRIES, last),
                  file=sys.stderr)
            time.sleep(2 * (attempt + 1))
        else:
            raise SystemExit('download failed: %s' % last)

    if os.path.exists(MBOX):
        digest = sha256_of(MBOX)
        if recorded.get('soc.culture.esperanto.mbox', '').startswith(
                digest[:12]):
            print('  have mbox (sha256:%s) — skip extract' % digest[:12])
            return
        raise SystemExit('%s exists but its digest is not recorded in '
                         'RAW/usenet/README.md; move it aside or fix the '
                         'README.' % MBOX)
    if args.dry_run:
        print('  would extract %s -> %s' % (SEVENZ, MBOX))
        return
    print('  extracting 7z -> mbox ...')
    extract_7z(SEVENZ, MBOX)
    digest = sha256_of(MBOX)
    print('    ' + append_readme('soc.culture.esperanto.mbox', digest,
                                 os.path.getsize(MBOX),
                                 'extracted; 69,804 Usenet messages'))


if __name__ == '__main__':
    main()
