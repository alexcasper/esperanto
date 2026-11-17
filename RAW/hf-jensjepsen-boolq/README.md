<!-- PROVENANCE (ops_esp, 2026-11-10, bead esp-aor): fetched from
https://huggingface.co/datasets/jensjepsen/esperanto-boolq-questions
revision cf3c3a1bd8c7 (2026-07-14). Local file:
data/train-00000-of-00001.parquet (blob gitignored), 1,860,890 B,
sha256-12 e0c0681d6006. Licence per card: MIT. Upstream README follows. -->
---
license: mit
language:
- eo
- en
task_categories:
- translation
- question-answering
size_categories:
- 10K<n<100K
tags:
- esperanto
- boolq
- round-trip
- quality-scored
---

# esperanto-boolq-questions

BoolQ questions (train + validation, **12,697 rows**) translated from
English to Esperanto by
[`jensjepsen/eo-mt-v13-large-bidir`](https://huggingface.co/jensjepsen/eo-mt-v13-large-bidir),
with round-trip quality metadata for filtering.

## Row schema

| field | description |
|---|---|
| `orig_idx` | original BoolQ row index (train first, then validation) |
| `split` | source split (`train` / `validation`) |
| `en_orig` | raw BoolQ question (lowercase, no `?`, as in google/boolq) |
| `en_preproc` | preprocessed input fed to MT: spaCy `en_core_web_lg` recase (first-word cap + PROPN/entity title-case) + `?` appended |
| **`en_eo`** | **Esperanto translation** (`preproc` → EO, greedy decode) |
| `en_eo_en` | EO → EN back-translation (trailing `?` stripped) |
| `chrf` | sacrebleu sentence chrF, `en_eo_en` vs `en_orig` |
| `bleu` | sacrebleu sentence BLEU, `en_eo_en` vs `en_orig` |
| `cos_sim` | LaBSE (`sentence-transformers/LaBSE`) cosine similarity between `en_orig` and `en_eo_en` |

## Quality distribution

| metric | mean | median |
|---|---|---|
| chrF | 66.4 | 66.9 |
| BLEU | 37.1 | 32.0 |
| **cos_sim** | **0.942** | **0.951** |

Round-trip fail-rate (LaBSE cos_sim thresholds):

| threshold | count | rate |
|---|---|---|
| <0.90 | 1,400 | 11.03% |
| <0.85 | 377 | 2.97% |
| <0.80 | 122 | 0.96% |
| <0.75 | 36 | 0.28% |
| <0.70 | 11 | 0.09% |

Recommended filter for downstream use: **`cos_sim >= 0.85`** keeps
~97% of rows and drops the catastrophic tier where semantic meaning
was lost. `cos_sim >= 0.90` (~89% kept) is a stricter alternative for
high-quality-only use.

## Why round-trip

The primary use is quality-scored EO translations of BoolQ questions.
The back-translation isn't there to "double-check" (MT round-trips
often introduce spurious drift), it's there to give a per-row LaBSE
similarity score that flags catastrophically-bad forward translations
without needing EO annotators. `cos_sim` correlates strongly with
"the EO translation is faithful" — 3% of rows fall below 0.85 and
those are mostly pop-culture titles / brand names / idioms that MT
couldn't preserve (see `en_orig` at low `cos_sim`).

## Preprocessing rationale

BoolQ questions are stored as lowercase fragments without terminal
punctuation. Feeding them raw to MT causes two problems:

1. **Named entities miss capitalization**, so `elena`, `hyundai`,
   `instagram` get translated as common nouns.
2. **v12** (`eo-mt-v12-bidir`) had a specific failure mode where
   capitalized-fragment-no-terminal-punct inputs collapsed to
   memorized KDE/GNOME UI labels (`@ info: whatsthis` -> `& Resize`).
   v13 fixed this via OPUS-100 cleanup.

The spaCy recase + `?` suffix restores proper casing on entities
(`Instagram`, `Hyundai`, `John Wick`) and matches the training-data
distribution.

## Reproduce

```python
from datasets import load_dataset
ds = load_dataset("jensjepsen/esperanto-boolq-questions", split="train")

# Keep only high-quality translations
clean = ds.filter(lambda r: r["cos_sim"] >= 0.85)
```

Original BoolQ: `google/boolq`. Translation script:
[roundtrip_boolq_scored.py](https://github.com/jensjepsen/small-esperanto-llm/blob/main/scripts/roundtrip_boolq_scored.py)
