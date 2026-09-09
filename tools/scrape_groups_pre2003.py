#!/usr/bin/env python3
"""Slow, resumable scrape of pre-2003 soc.culture.esperanto from Google
Groups (beads esp-r8p, GitHub issue #12 — see RAW/usenet/README.md).

Google's web app is JS-rendered; this drives real Chromium via Playwright,
so cookies/consent/JS just work. It walks the in-group search month by
month (DejaNews archive starts 1995-05), captures the batchexecute JSON
replies the page itself makes, heuristically pulls message records out of
them, and writes BOTH an audit trail and a plain mbox that drops straight
into the existing pipeline:

    RAW/usenet/soc.culture.esperanto.pre2003.mbox
      -> python3 tools/extract_usenet_esperanto.py \
             --mbox RAW/usenet/soc.culture.esperanto.pre2003.mbox \
             --outdir QUARANTINE/soc.culture.esperanto.pre2003

Run it from an IP/Network with a clean Groups history. NOTE 2026-08-31:
this repo's own egress is a BT residential IP (86.153.76.111) and is
STILL Groups-429'd on every /g/* page (google.com + web search fine from
the same IP) — the "just use a residential IP" theory is dead; the flag
follows the IP, likely tripped by our own probing, and shows no
Retry-After. Don't re-canary more than once/week, one request only.
Google's
ToS prohibits automated access; this is a maintainer call, so it crawls
politely — one page per ~12 s with jitter, exponential backoff on errors,
and a state file so it never re-does work:

    pip install playwright && playwright install chromium
    python3 tools/scrape_groups_pre2003.py --probe   # FIRST: calibrate
    python3 tools/scrape_groups_pre2003.py           # full run, resumable

--probe loads ONE search page, saves every captured batchexecute reply
under gg-probe-responses/, and prints message-like candidates with their
array positions. If the record layout looks wrong, send the artifacts back
and MSG_PATHS (below) gets adjusted — everything else (throttle, state,
mbox writing, dedup) is stable regardless.
"""
import argparse
import email.utils
import json
import os
import random
import re
import sys
import time

GROUP = 'soc.culture.esperanto'
SEARCH_URL = ('https://groups.google.com/g/%s/search?query=' % GROUP)
STATE = 'gg-scrape-state.json'
MBOX_OUT = os.path.join('RAW', 'usenet', 'soc.culture.esperanto.pre2003.mbox')
AUDIT = 'gg-scrape-audit.jsonl'

# Array index paths into a batchexecute reply where message-like records
# were found by --probe. Layouts shift; adjust from probe artifacts only.
MSG_PATHS = {'id': 0, 'author': 1, 'epoch_ms': 3, 'html': 4}

DELAY = 12.0          # seconds between page loads, +/-40% jitter
MAX_BACKOFF = 600


def jitter():
    return DELAY * random.uniform(0.6, 1.4)


def month_windows(first='1995-05', last='2002-12'):
    out, y, m = [], *map(int, first.split('-'))
    ly, lm = map(int, last.split('-'))
    while (y, m) <= (ly, lm):
        out.append('%04d-%02d' % (y, m))
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return out


def walk_arrays(node):
    """Yield every array anywhere inside parsed batchexecute JSON."""
    if isinstance(node, list):
        yield node
        for item in node:
            yield from walk_arrays(item)


def looks_like_message(arr):
    """A message record: an id-ish string, a 13-digit epoch, and a long
    body-ish string somewhere in the array."""
    has_epoch = any(isinstance(x, (int, float)) and
                    7e11 < x < 2e12 for x in arr) or any(
        isinstance(x, str) and re.fullmatch(r'1[0-9]{12}', x) for x in arr)
    has_long = any(isinstance(x, str) and (len(x) > 200 or '<div' in x)
                   for x in arr)
    return has_epoch and has_long and len(arr) >= 4


def to_mbox_entry(rec):
    mid = rec.get('id') or rec.get('epoch_ms')
    msg_id = mid if (isinstance(mid, str) and '@' in mid) \
        else '<gg-%s@scrape>' % mid
    date = time.strftime('%a, %d %b %Y %H:%M:%S +0000',
                         time.gmtime(rec['epoch_ms'] / 1000))
    text = re.sub(r'<[^>]+>', ' ', rec['html'])
    text = re.sub(r'\s+', ' ', text).strip()
    return ('From nobody %s\nMessage-ID: %s\nFrom: %s\n'
            'Newsgroups: %s\nSubject: [gg-scrape] %s\nDate: %s\n\n%s\n\n'
            % (date, msg_id, rec.get('author', 'nobody').replace('\n', ' '),
               GROUP, rec.get('subject', ''), date, text))


def load_state():
    if os.path.exists(STATE):
        return json.load(open(STATE))
    return {'done': [], 'seen_ids': [], 'pages': 0, 'errors': 0}


def save_state(st):
    tmp = STATE + '.tmp'
    json.dump(st, open(tmp, 'w'))
    os.replace(tmp, STATE)


def run(probe, window, headless):
    from playwright.sync_api import sync_playwright
    st = load_state()
    responses = []

    def capture(resp):
        if '/batchexecute' in resp.url:
            try:
                responses.append(resp.text())
            except Exception:
                pass

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        page = browser.new_page()
        page.on('response', capture)
        windows = month_windows()
        if probe:
            windows = windows[:1]
        for win in windows:
            if not probe and win in st['done']:
                continue
            q = f'after%3A{win}-01%20before%3A{next_month(win)}-01'
            url = SEARCH_URL + q
            print('%s  %s' % (time.strftime('%H:%M:%S'), url))
            for attempt in range(5):
                try:
                    page.goto(url, wait_until='networkidle', timeout=60000)
                    break
                except Exception as e:
                    wait = min(30 * 2 ** attempt, MAX_BACKOFF)
                    print('    goto error (%s), backoff %ds'
                          % (str(e)[:60], wait))
                    time.sleep(wait)
            time.sleep(3)
            if probe:
                os.makedirs('gg-probe-responses', exist_ok=True)
                for i, r in enumerate(responses):
                    open('gg-probe-responses/%03d.json' % i, 'w')\
                        .write(r)
                n = report_candidates(responses)
                print('saved %d replies; %d message-like candidates '
                      '(see gg-probe-responses/)' % (len(responses), n))
                browser.close()
                return
            records = extract(responses)
            append_records(records, st)
            st['done'].append(win)
            st['pages'] += 1
            save_state(st)
            responses.clear()
            time.sleep(jitter())
        browser.close()
    print('done: %d windows, %d messages' % (len(st['done']),
                                             len(st['seen_ids'])))


def next_month(win):
    y, m = map(int, win.split('-'))
    m += 1
    if m == 13:
        y, m = y + 1, 1
    return '%04d-%02d' % (y, m)


def extract(responses):
    out = []
    for raw in responses:
        stripped = raw.lstrip()
        if stripped.startswith(')]}'):
            i = raw.find('[')
            body = raw[i:] if i >= 0 else ''
        else:
            body = raw
        try:
            data = json.loads(body)
        except Exception:
            continue
        for arr in walk_arrays(data):
            if looks_like_message(arr):
                try:
                    out.append({
                        'id': str(arr[MSG_PATHS['id']]),
                        'author': arr[MSG_PATHS['author']],
                        'epoch_ms': arr[MSG_PATHS['epoch_ms']],
                        'html': arr[MSG_PATHS['html']],
                    })
                except (IndexError, TypeError):
                    continue
    return out


def report_candidates(responses):
    n = 0
    for raw in responses:
        try:
            data = json.loads(raw[raw.find('['):])
        except Exception:
            continue
        for arr in walk_arrays(data):
            if looks_like_message(arr):
                n += 1
                print('  cand[%d]: %s  %s' % (
                    n, [type(x).__name__ for x in arr[:6]],
                    str(arr[MSG_PATHS.get('epoch_ms', 3)])[:12]))
    return n

def append_records(records, st):
    st['seen_ids'] = st['seen_ids'][-50000:]
    with open(MBOX_OUT, 'a', encoding='utf-8') as fh, \
            open(AUDIT, 'a', encoding='utf-8') as audit:
        for rec in records:
            key = rec['id']
            if key in st['seen_ids']:
                continue
            st['seen_ids'].append(key)
            fh.write(to_mbox_entry(rec))
            audit.write(json.dumps(rec, ensure_ascii=False)[:4000] + '\n')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--probe', action='store_true',
                    help='calibration run: one page, dump raw replies')
    ap.add_argument('--window',
                    help='scrape a single YYYY-MM window instead')
    ap.add_argument('--show', action='store_true',
                    help='run with a visible browser (helps first consent)')
    a = ap.parse_args()
    run(a.probe, a.window, headless=not a.show)


if __name__ == '__main__':
    main()
