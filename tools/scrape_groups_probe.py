#!/usr/bin/env python3
"""Probe what Google Groups serves YOUR ip for soc.culture.esperanto
(pre-2003 recovery, beads esp-r8p — see RAW/usenet/README.md).

Zero dependencies. Run this from the machine that will do the scraping
(residential IP — the repo container is 429-blocked):

    python3 tools/scrape_groups_probe.py

For each of three front-ends it saves the raw response under
gg-probe-artifacts/ and prints what it found. The scraper's brittle
constants (selectors, data shapes) get finalized from these artifacts —
zip the directory and attach it to the PR, or paste the summary back.
"""
import re
import ssl
import sys
import urllib.request

UA = ('Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 '
      'Firefox/128.0')
TARGETS = [
    ('group-page', 'https://groups.google.com/g/soc.culture.esperanto'),
    ('old-ui', 'https://groups.google.com/group/soc.culture.esperanto'),
    ('search-pre2003',
     'https://groups.google.com/g/soc.culture.esperanto/search'
     '?query=before%3A2003-01-01'),
]


def fetch(url):
    ctx = ssl.create_default_context()
    req = urllib.request.Request(url, headers={
        'User-Agent': UA, 'Accept-Language': 'eo,en;q=0.8'})
    with urllib.request.urlopen(req, timeout=45, context=ctx) as resp:
        return resp.status, resp.url, resp.read()


def main():
    import os
    os.makedirs('gg-probe-artifacts', exist_ok=True)
    for name, url in TARGETS:
        try:
            status, final, body = fetch(url)
        except Exception as e:
            print('%-14s ERROR %s' % (name, e))
            continue
        path = 'gg-probe-artifacts/%s.html' % name
        open(path, 'wb').write(body)
        title = re.search(rb'<title[^>]*>(.*?)</title>', body, re.S)
        print('%-14s %s %7dB final=%s' % (name, status, len(body),
                                          final[:60]))
        print('%-14s   title=%s' % ('',
              (title.group(1).decode('utf-8', 'replace').strip()
               if title else '(none)')[:70]))
        print('%-14s   AF_initDataCallback x%d, batchexecute %s, '
              'consent redirect %s' % ('',
              body.count(b'AF_initDataCallback'),
              b'/batchexecute' in body,
              b'consent.google.com' in body))
    print('\nArtifacts in gg-probe-artifacts/ — send them back so the '
          'scraper constants can be finalized.')


if __name__ == '__main__':
    main()
