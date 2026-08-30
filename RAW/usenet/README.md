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

Fetched 2026-08-30 by t3 (Galahad).
- `soc.culture.esperanto.69804.mbox.7z` — archive.org FULL-USENET-BACKUP-2020-Oct — sha256:8e8df1ea98a6 — 27,755,969 bytes
- `soc.culture.esperanto.mbox` — extracted; 69,804 Usenet messages — sha256:4cc041bb6ddd — 187,741,489 bytes
