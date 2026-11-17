# EVAL/ — evaluation datasets

Benchmark/eval datasets for the esp multilingual evaluation lane. Unlike RAW/
(small committed provenance only) and CORPUS/ (gitignored blobs), datasets that
are small and cleanly licensed are committed here in full; large ones follow the
RAW blob convention instead.

## esperantobench/ (2026-11-10, bead esp-hae)

- `EsperantoBench.json` (sha256-12 `77cbace8d5ce`, 651 items) — trentmkelly/
  EsperantoBench on Hugging Face, revision `749f358e0b08` (2025-06-28) —
  **CC0-1.0** — https://huggingface.co/datasets/trentmkelly/EsperantoBench
- 651 four-answer multiple-choice questions testing Esperanto vocabulary and
  grammar knowledge. NOTE: questions are written in ENGLISH about Esperanto
  (derived from Ivy Kellerman Reed, "A Complete Grammar of Esperanto");
  the `correct_answer` field is `a`–`d`, per-item `chapter_id`/`kmeans_cluster`
  give topic structure.
- Fields: question_text, answer_a..answer_d, correct_answer, chapter_id,
  kmeans_cluster.
