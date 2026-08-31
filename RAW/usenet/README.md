# RAW/usenet/ — soc.culture.esperanto Usenet blobs (GitHub issue #12, beads esp-r8p)

Fetch with `python3 tools/fetch_raw_usenet.py` (idempotent; verifies recorded
digests, downloads and extracts only what is missing). Blobs are NOT
committed — this README is the durable record.

Primary source: Internet Archive item
[FULL-USENET-BACKUP-2020-Oct-soc.culture.esperanto.69804.mbox.7z](https://archive.org/details/FULL-USENET-BACKUP-2020-Oct-soc.culture.esperanto.69804.mbox.7z)
(collection `usenet`) — the complete newsgroup as one mbox, 69,804 messages
through Oct 2020, 27,755,969 bytes as 7z. Issue #12's Google Groups link
surfaces the same group but is JS-rendered and scrape-hostile; the archive
item is the same corpus, whole.

Recorded fallback (not fetched): Giganews snapshot of 2014-07-22, plain
`mbox.gz`, in archive.org item `usenet-soc.culture`
(`soc.culture.esperanto.20140722.mbox.gz`) — no 7z support needed if the
primary ever disappears.

**Licence: none declared.** Usenet posts remain the copyright of their
authors; archive.org asserts no rights and grants none. These blobs are
kept for provenance and research, and the extracted text lives under
`QUARANTINE/soc.culture.esperanto/` — it must not reach `CORPUS/`
(see `QUARANTINE/README.md`; same reasoning as `pg-23586`).

## Pre-2003 posts: investigated, not reachable from here

Both Usenet-spool sources start at 2003 — the FULL-USENET-BACKUP item and
the Giganews snapshot (which is a subset, 3,386 messages, 2003-2013) — so
the group's 1990s history is absent from archive.org entirely. Checked and
ruled out (2026-08-30): utzoo 1981-1991 tapes (group did not exist — it was
created by Yves Bellefeuille, mid-90s, per the group's own lore quoted in
the archive itself); Wayback Machine (~150 incidentally crawled old-UI
message pages — too thin); ftp.funet.fi (dead). The pre-2003 material
exists, if anywhere, only in Google Groups' DejaNews inheritance (1995+),
which the issue's link points at — but Google is rate-limiting this host
(HTTP 429) and scraping it is a ToS decision for a maintainer, not a
default. If that material is ever extracted, feed it through the same
pipeline: same envelope split, same scoring, same QUARANTINE placement.

More avenues probed the same day, all empty: the group's own FAQ threads
(no archive location in the text); marc.info and mail-archive.com (no
esperanto-l); Wayback trees of esperanto.org (the 2004 "Arkivoj" capture
is itself a 404), donh.best.vwh.net, and Edmund Grimley-Evans' site
(personal pages, no group archives); narkive.com (covers 2004+). The
Google 429 persisted all session, including the old-UI redirect.
Follow-up 2026-08-31: egress here is a *residential* BT IP (86.153.76.111)
and every /g/* page still 429s with no Retry-After, while google.com and
web search return 200 from the same IP — i.e. a Groups-specific IP flag
that "residential IP" does not cure; likely armed by our own probing.
Leave this IP alone; run the probe from a different network only. Clue for
a future attempt: much 90s group traffic was two-way gatewayed from the
esperanto-l mailing list (majordomo at esperanto.org in 2003, per
Received headers in this mbox) — a surfacing list archive would recover
overlapping content ToS-cleanly.

Fetched 2026-08-30 by t3 (Galahad).
- `soc.culture.esperanto.69804.mbox.7z` — archive.org FULL-USENET-BACKUP-2020-Oct — sha256:8e8df1ea98a6 — 27,755,969 bytes
- `soc.culture.esperanto.mbox` — extracted; 69,804 Usenet messages — sha256:4cc041bb6ddd — 187,741,489 bytes
