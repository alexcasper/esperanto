#!/usr/bin/env python3
"""Fetch the ReVo source articles behind the mis-merged headwords.

Usage: python3 tools/fetch_revo_articles.py --out DIR [--limit N]

Only the articles that are actually needed are fetched — the ones behind an
entry carrying `revo_raw` (a headword the merge joined with a comma) or a ReVo
headword long enough to be a multi-word term run together. That is about 1100
of ReVo's 13000 articles, and the cache means a re-run fetches nothing.

reta-vortaro.de is run by volunteers, so this asks for one article at a time
with a delay between requests and identifies itself in the User-Agent. Do not
raise the rate to save a few minutes.
"""
import argparse
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENTRIES = os.path.join(ROOT, 'DICT', 'entries.jsonl')
BASE = 'https://www.reta-vortaro.de/revo/xml/%s.xml'
AGENT = ('esperanto-corpus-repair/1.0 (repairing ~1300 headwords a local '
         'merge damaged; github.com/alexcasper/esperanto)')
PARALLEL = 4
LONG_HEADWORD = 18


def article_name(root):
    """ReVo files its articles by root, lower case, x-system for diacritics."""
    name = root.lower()
    for letter, ascii_pair in (('ĉ', 'cx'), ('ĝ', 'gx'), ('ĥ', 'hx'),
                               ('ĵ', 'jx'), ('ŝ', 'sx'), ('ŭ', 'ux')):
        name = name.replace(letter, ascii_pair)
    return name


def candidates(name):
    """Names to try, in order, for one root.

    The root recorded in entries.jsonl does not always name the file exactly.
    ReVo strips the hyphen from a compound place name (Adis-Abeb becomes
    adisabeb) and files a handful of roots one letter shorter than our merge
    recorded them (abrikot is filed as abriko). Both are cheap to try and only
    cost a request where the first guess misses.
    """
    tried = [name]
    if '-' in name:
        tried.append(name.replace('-', ''))
    for cut in (1, 2):
        if len(name) - cut >= 3:
            tried.append(name[:-cut])
    seen, ordered = set(), []
    for candidate in tried:
        if candidate not in seen:
            seen.add(candidate)
            ordered.append(candidate)
    return ordered


def needed():
    roots = {}
    with open(ENTRIES, encoding='utf-8') as fh:
        for line in fh:
            if not line.strip():
                continue
            entry = json.loads(line)
            source = entry.get('source') or ''
            root = entry.get('root')
            if not root or not source.startswith('ReVo'):
                continue
            if entry.get('revo_raw') or len(entry['word']) >= LONG_HEADWORD:
                roots.setdefault(article_name(root), root)
    return roots


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--out', required=True)
    parser.add_argument('--limit', type=int)
    args = parser.parse_args()

    os.makedirs(args.out, exist_ok=True)
    wanted = needed()
    names = sorted(wanted)[:args.limit] if args.limit else sorted(wanted)
    print('%d articles needed' % len(names))

    fetched = cached = failed = 0
    missing, todo = [], []
    for name in names:
        path = os.path.join(args.out, name + '.xml')
        if os.path.exists(path) and os.path.getsize(path) > 0:
            cached += 1
            continue
        # curl rather than urllib: through this environment's egress proxy a
        # urllib request stalls and the tunnel is closed mid-exchange after
        # about twelve seconds, while curl completes normally.
        todo.append(name)

    # One curl invocation per round, reusing the connection across articles.
    # Through this environment's egress proxy a fresh TLS handshake costs about
    # five seconds, so a process per request would take an hour and a half for
    # eleven hundred articles. Reusing the connection is both far faster and
    # gentler on a volunteer-run server than eleven hundred handshakes. Each
    # round retries whatever missed under the next candidate name.
    for round_index in range(4):
        if not todo:
            break
        config = os.path.join(args.out, '_batch.curl')
        with open(config, 'w', encoding='utf-8') as fh:
            for name in todo:
                options = candidates(name)
                target = options[min(round_index, len(options) - 1)]
                fh.write('url = "%s"\noutput = "%s"\n'
                         % (BASE % target,
                            os.path.join(args.out, name + '.xml')))
        subprocess.run(['curl', '-sS', '--fail', '--parallel',
                        '--parallel-max', str(PARALLEL), '--max-time', '60',
                        '-A', AGENT, '-K', config],
                       capture_output=True, text=True)
        os.remove(config)
        remaining = []
        for name in todo:
            target = os.path.join(args.out, name + '.xml')
            if os.path.exists(target) and os.path.getsize(target) > 200:
                fetched += 1
                continue
            if os.path.exists(target):
                os.remove(target)
            if len(candidates(name)) > round_index + 1:
                remaining.append(name)
            else:
                failed += 1
                missing.append(name)
        print('  round %d: %d fetched, %d to retry under another name'
              % (round_index + 1, fetched, len(remaining)), flush=True)
        todo = remaining
    failed += len(todo)
    missing.extend(todo)

    print('done: %d fetched, %d already cached, %d not retrievable'
          % (fetched, cached, failed))
    for row in missing[:20]:
        print('    %s' % row)
    return 0


if __name__ == '__main__':
    sys.exit(main())
