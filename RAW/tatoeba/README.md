# RAW/tatoeba/ — Tatoeba export blobs (GitHub issue #11, beads esp-tato)

Fetch with `python3 tools/fetch_tatoeba.py` (idempotent; verifies recorded
digests and only downloads what is missing). The blobs are NOT committed —
links.tar.bz2 alone is ~150 MB — so this README is the durable record.

Licences: the per-language `*_CC0.tsv.bz2` exports contain only sentences
whose licence is CC0; `links.tar.bz2` is distributed under CC0; the full
per-language `*_sentences.tsv.bz2` exports contain everything and are
CC-BY 2.0 FR (attribution: Tatoeba project + sentence authors — sentence
ids are retained downstream so attribution is possible).
`sentences_base.tar.bz2` maps each sentence to the sentence it was translated
from (`\N` = original), with no text of its own.

Fetched 2026-08-30 by t3 (Galahad). Exports stamped 2026-08-29 by Tatoeba.

- `epo_sentences_CC0.tsv.bz2` — sha256:cb887bb4f0b2 — 9,631 bytes — https://downloads.tatoeba.org/exports/per_language/epo/epo_sentences_CC0.tsv.bz2
- `eng_sentences_CC0.tsv.bz2` — sha256:489556f5ed66 — 1,288,331 bytes — https://downloads.tatoeba.org/exports/per_language/eng/eng_sentences_CC0.tsv.bz2
- `epo_sentences.tsv.bz2` — sha256:096d7b07d995 — 11,516,018 bytes — https://downloads.tatoeba.org/exports/per_language/epo/epo_sentences.tsv.bz2
- `eng_sentences.tsv.bz2` — sha256:d1a7d45ad531 — 24,854,952 bytes — https://downloads.tatoeba.org/exports/per_language/eng/eng_sentences.tsv.bz2
- `sentences_base.tar.bz2` — sha256:0b1b69ee9100 — 63,623,953 bytes — https://downloads.tatoeba.org/exports/sentences_base.tar.bz2
- `links.tar.bz2` — sha256:a06047f98adc — 149,438,756 bytes — https://downloads.tatoeba.org/exports/links.tar.bz2
