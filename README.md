# Esperanto — hq#171 worksite

Standing-orders worksite for building Esperanto language assets: raw corpus, dictionary, and grammar guide.

## Layout

- `RAW/` — raw Esperanto corpus materials (input texts; see SKL-8m1r.2)
- `DICT/` — JSONL dictionary artifacts (see SKL-8m1r.3)
- `GRAMMAR/` — grammar guide (see SKL-8m1r.4)
- `CORPUS/` — RAW/ normalized for machine reading: Gutenberg and Vikifontaro
  furniture stripped, x-system spellings folded to UTF-8 diacritics. Derived,
  so only `CORPUS/MANIFEST.tsv` is committed; regenerate the text with
  `python3 tools/normalize_corpus.py`. `CORPUS/tatoeba/` holds the
  English–Esperanto parallel pair corpus built from Tatoeba exports
  (`pairs.tsv` 434k pairs, CC-BY-mix, gitignored; `pairs_cc0.tsv` 23 CC0
  pairs, committed); see `CORPUS/tatoeba/README.md`.
- `QUARANTINE/` — sources held out of the corpus for licensing reasons; not
  read by any tool. See `QUARANTINE/README.md`
- `tools/` — corpus tooling shared by the DICT and GRAMMAR passes:
  `normalize_corpus.py` (RAW → CORPUS), `fetch_raw_gutenberg.py` and
  `fetch_raw_vikifontaro.py` (source acquisition, both gated on licence and
  text quality), `score_esperanto_text.py` (how much of a candidate text is
  recognisable Esperanto, for judging OCR before it reaches the corpus),
  `fetch_tatoeba.py` / `build_tatoeba_pairs.py` (Tatoeba export acquisition
  and the en–epo parallel join; idempotent, digest-recorded),
  `fetch_raw_usenet.py` / `extract_usenet_esperanto.py` (soc.culture.
  esperanto archive from archive.org: fetch + Esperanto extraction; output
  is licence-hold — see QUARANTINE/soc.culture.esperanto/)

## Conventions

- One branch per node/agent pair: `j1-lancelot`, `j2-gawain`, `t3-galahad`, `t4-percival`, `r5-tristan`, `j6-bedivere`.
- Tranches/PRs to `main`; work tracked on the GitHub project board and in beads (SKL-8m1r.*).
