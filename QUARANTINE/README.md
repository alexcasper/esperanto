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

## Adding to this folder

Move the file with `git mv`, strike its line in `RAW/PROVENANCE.md` with the
reason, add a section here, and regenerate `CORPUS/MANIFEST.tsv` by running
`python3 tools/normalize_corpus.py`.
