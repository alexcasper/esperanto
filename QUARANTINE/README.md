# QUARANTINE/ — held out of the corpus

Texts that reached `RAW/` but must not be treated as corpus material. Nothing
here is read by `tools/normalize_corpus.py`, so these files never reach
`CORPUS/`, `DICT/` or `GRAMMAR/`.

Files stay in the repository rather than being deleted so the provenance record
stays honest: `RAW/PROVENANCE.md` recorded each of them as a source once, and a
silent deletion would leave that history unexplained.

## Contents

### `pg-23586.txt` — La liturgio de l' foiro (Elementoj por ekzegezo)

- **Author**: Jorge Camacho (b. 1966)
- **Source**: https://www.gutenberg.org/ebooks/23586
- **Reason**: copyrighted, not public domain. Project Gutenberg's own
  bibliographic record reads *"Copyrighted. Read the copyright notice inside
  this book for details."*, and the file itself carries
  *"kopirajto (c) ĉe la aŭtoro kaj la eldonejo"* (Progresema Esperanto-Forumo,
  1999). Project Gutenberg hosts it with the rightsholder's permission; that
  permission does not extend to redistributing it as part of this corpus.
- **History**: added in RAW batch 1 and recorded there as public domain. The
  error surfaced when `tools/fetch_raw_gutenberg.py` began gating candidates on
  Gutenberg's copyright status; the other nine batch-1 Gutenberg texts verify
  as public domain. Tracked as bead `esp-br4`.

## `soc.culture.esperanto/` — Usenet newsgroup archive (2026-08-30)

- **Author**: the newsgroup's posters, individually (per-poster copyright;
  no collective licence exists or could exist)
- **Source**: Internet Archive item [FULL-USENET-BACKUP-2020-Oct-soc.culture.esperanto.69804.mbox.7z](https://archive.org/details/FULL-USENET-BACKUP-2020-Oct-soc.culture.esperanto.69804.mbox.7z)
  — complete mbox of the group, 69,804 messages (2003–2019 in practice),
  fetched to `RAW/usenet/` by `tools/fetch_raw_usenet.py` (issue #12's
  Google Groups front-end is the same material, scrape-hostile)
- **Reason**: no licence declared on the item, and Usenet posts remain the
  copyright of their authors. Unlike `pg-23586` there is no rightsholder to
  ask. The extracted text is valuable for eyeballing and private research,
  but redistribution as corpus material has no basis, so it is held here:
  `extracted.tsv` (gitignored; 47,513 messages scoring ≥0.70 Esperanto by
  `tools/score_esperanto_text.py`'s UV-vocabulary measure, quotes and
  signatures stripped, x-system folded to UTF-8), `MANIFEST.tsv` (digests
  and counts) — regenerate with `python3 tools/extract_usenet_esperanto.py`.
- **History**: extracted 2026-08-30 by t3 (Galahad), tracked as `esp-r8p`
  for GitHub issue #12. Promotion to `RAW/`+`CORPUS/` needs a maintainer
  ruling; the reasonable paths are asking major posters (the group's
  long-term contributors are identifiable) or using it only as a private
  reference for DICT/GRAMMAR work.

## Adding to this folder

Move the file with `git mv`, strike its line in `RAW/PROVENANCE.md` with the
reason, add a section here, and regenerate `CORPUS/MANIFEST.tsv` by running
`python3 tools/normalize_corpus.py`.
