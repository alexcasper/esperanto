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

### Text quality — three archive.org sources (PR #8)

Moved after triage of the 57 `ia-*` sources with
`tools/score_esperanto_text.py`. Each was read before being moved: the score
ranks candidates, it does not classify them, and two of the three were flagged
for the wrong reason by the metric alone.

- **`ia-TranslationOfTheMeaningsOfTheNobleQuranInTheEsperantopdf.txt`** —
  82121 tokens of broken machine translation, not Esperanto:
  *"This scripture est infallible; beacon por des righteous; who kred en
  unseen observ Kontakt Pravers (Salat) el our provisions al them ili don
  charitv!"*. 49.7% of its tokens look Esperanto-ish and 7.2% are English.
  By far the most damaging of the three: it is large, and malformed
  word-forms at that scale would enter DICT as fake lemmas.
- **`ia-KvarvoajKantojPorEsperantistoj.txt`** — a songbook whose scan is
  badly corrupted, and largely English advertising matter rather than song
  text: *"Esj»ranto", "estabbshed", "kS^W*£ spreadof"*.
- **`ia-Pichismo----.....1992-2014.txt`** — 73 words of scanner noise
  (*"p-T10<"*, *"dtouns"*).

**Deliberately NOT moved**, though the metric scored them poorly:

- The 41 `ia-eowiki-*_lingvo` articles are real Esperanto prose. They score
  low because they are short, quote heavily in the language each describes,
  and carry alphabet tables — a run of single letters reads as 46% "single
  character tokens" without a thing being wrong with the text.
- `ia-dlibra.kul.pl.49099.txt` is a genuine bilingual Esperanto-German
  periodical: 70.6% Esperanto against 5.6% German, the German being
  advertising pages.
- `ia-key_to_the_ekzercaro.txt` (English), `ia-traduction_de_lekzercaro.txt`
  (French) and the Downes textbook are coherent texts that simply are not
  Esperanto. They stay in `RAW/` alongside the other English-language
  grammars and are excluded from lemma mining instead.

`RAW/QUALITY.tsv` records the score for every source so the judgement can be
re-checked without repeating the work.

## Adding to this folder

Move the file with `git mv`, strike its line in `RAW/PROVENANCE.md` with the
reason, add a section here, and regenerate `CORPUS/MANIFEST.tsv` by running
`python3 tools/normalize_corpus.py`.
