# GOAL — glm pane (ops_esp)

Identity: worktree `/mnt/d/ops/esperanto/esp_glm`, branch `glm`. Role:
**coordinator + sole merger + corpus acquisition**.

## Objective

1. Claim and execute `esp-4g8` — pull the Esperanto Wikipedia (Vikipedio)
   dump from https://dumps.wikimedia.org/eowiki/ (pages-articles stream) as a
   new RAW/ corpus source. Follow the bead's conventions exactly (naming,
   sha256 dedup, PROVENANCE.md lines, wiki-furniture stripping, quality gate
   via tools/score_esperanto_text.py, CORPUS/MANIFEST.tsv update).
2. Coordinate: watch sibling panes' beads/branches, merge work marked
   "ready for merge" (see MERGE_DUTIES.md).

## Non-goals

No dictionary edits, no grammar edits, no web app work — those belong to the
claude and gemini panes. esp-0ic (LF-arkivo licence request) is the human's
(alex) — never close it.

## Steps

1. `bd update esp-4g8 --claim` then execute it. Gitignored blob data lives in
   the MAIN worktree (/mnt/d/ops/esperanto/RAW/, CORPUS/) — the worktree has
   symlinks for existing blobs; write NEW files in this worktree normally,
   and note in the merge comment that blobs must be copied/symlinked to the
   main worktree at merge time.
2. After esp-4g8: run normalize_corpus.py, update MANIFEST.tsv, commit to
   `glm` branch, `bd close esp-4g8` with evidence.
3. Watch loop: on each wake, `bd list --all`, `git -C ../esp_claude log
   --oneline -3`, `git -C ../esp_gemini log --oneline -3`; merge branches
   marked ready.

## Exit criteria

- esp-4g8 closed: Vikipedio articles in RAW/, PROVENANCE.md updated,
  CORPUS/MANIFEST.tsv regenerated, quality-gate scores recorded in the bead.
- First merge cycle run (any sibling work merged, or a report that none was
  ready).

## Stand-down

Stop on explicit "stand down" from the user. Do not close decision-class
beads or esp-0ic.
