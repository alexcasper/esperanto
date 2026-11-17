<!-- PROVENANCE (ops_esp, 2026-11-10, bead esp-aor): fetched from
https://huggingface.co/datasets/jensjepsen/esperanto-mt-parallel-v13
revision ef0f2fb9bb75 (2026-07-13). Local files: data/*.parquet, 8 shards,
2,131,183,423 B total, sha256-12 per shard:
train-00000 274f25abbc97 · train-00001 9b0683fa9a74 · train-00002 db45fa4bb1c2 ·
train-00003 1a27e3fc3faa · train-00004 be535349dbcd · train-00005 8e6a7cf14635 ·
train-00006 3529a6c6b33e · train-00007 c02f84a74db5.
Verified on load (pyarrow): 628,167 rows in shard 0; schema en/eo/src
(5,025,333 rows total per card); sources include ccmatrix. Licence per card:
MIT. Upstream README follows. -->
---
license: mit
language:
- en
- eo
task_categories:
- translation
---

# esperanto-mt-parallel v13

EN<->EO parallel training corpus. 5,025,333 rows after dedup.

## What changed vs v12 (`jensjepsen/esperanto-mt-parallel`)

- Dropped `Helsinki-NLP/opus-100` en-eo train split (144,549 rows).
  It is an aggregated multilingual blob that bundles KDE4/GNOME/Ubuntu
  `.po` localization pairs without `src` labels. In v12 this caused a
  systematic MT failure mode: capitalized-fragment-no-terminal-punct
  inputs collapsed to memorized UI labels
  (e.g. "@ info: whatsthis" -> "& Resize",
   "Name" -> "A tool to store a new image").
- Added individual OPUS pulls to replace the clean parts of opus-100:
  - `opus:qed` - 10,656 rows (educational subtitles, OPUS-QED v2.0a)
  - `opus:global_voices` - 3,172 rows (news, OPUS-GlobalVoices v2018q4)
- Refreshed OpenSubtitles to OPUS v2024 (was v5b-era pull, ~30k rows).
  New: `opus:opensubtitles` at 83,550 rows.

Net: ~-87k rows overall vs v12, but the dropped ~145k were mostly
KDE junk plus duplicated OpenSubtitles content, and the added ~97k is
clean.

## Source distribution

| src prefix | rows |
|---|---|
| ccmatrix | 1,944,726 |
| xlent | 1,204,545 |
| tatoeba | 426,558 |
| mmlu | 424,303 |
| finetranslations | 335,241 |
| wikimatrix | 294,142 |
| triviaqa | 108,777 |
| opus:opensubtitles | 83,550 |
| bible-uedin | 61,274 |
| piqa | 47,084 |
| sciq | 45,759 |
| wikimedia | 21,180 |
| ted2020 | 10,656 |
| opus:qed | 10,656 |
| opus:global_voices | 3,172 |
| copa | 2,224 |
| opus-books | 1,497 |

Row schema: `{en, eo, src}`.
