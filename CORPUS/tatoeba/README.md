# CORPUS/tatoeba/ — English–Esperanto parallel sentence pairs (GitHub issue #11, beads esp-tato)

`pairs.tsv` — 434,533 sentence pairs, one per line, TSV with header:

| column | meaning |
|---|---|
| `epo_id`, `eng_id` | Tatoeba sentence ids (retained for attribution) |
| `epo`, `eng` | the sentence texts |
| `base_epo`, `base_eng` | id of the sentence each side was entered as a translation of (`\N` = original), from `sentences_base.csv` |

Built by joining every English↔Esperanto link in Tatoeba's `links.csv`
(both directions, normalized and deduped), sorted by `(epo_id, eng_id)`.

`pairs_cc0.tsv` — same schema, restricted to sentences present in the
`*_CC0.tsv.bz2` exports: 23 pairs, CC0, safe for any use.

`MANIFEST.tsv` — sha256 + row counts for all six inputs and both outputs.

## Licence — read before using pairs.tsv

`pairs.tsv` mixes CC0 and CC-BY 2.0 FR sentences (Tatoeba's full exports).
Only 370 of Tatoeba's ~821k Esperanto sentences are CC0 — 0.05% — so the
CC0-only join yields 23 pairs. The full corpus exists because that was
deemed too thin (maintainer call, 2026-08-30); the price is attribution.
CC-BY 2.0 FR requires crediting Tatoeba (https://tatoeba.org) and the
sentence authors — sentence ids are kept in the file precisely so that
per-author attribution is possible via Tatoeba's API or detailed exports.
If your use cannot carry attribution, use `pairs_cc0.tsv`.

The links table itself is CC0; join structure imposes no extra obligation.

## Rebuild

```sh
python3 tools/fetch_tatoeba.py       # ~250 MB into RAW/tatoeba/ (gitignored)
python3 tools/build_tatoeba_pairs.py # ~45 s; writes pairs.tsv, pairs_cc0.tsv, MANIFEST.tsv
```

`pairs.tsv` (42 MB) is gitignored like the rest of derived CORPUS/;
`MANIFEST.tsv` pins its sha256 so a rebuilt copy can be verified.
Inputs are digest-recorded in `RAW/tatoeba/README.md` (exports stamped
2026-08-29). Rebuilds are deterministic: same inputs, same bytes.
