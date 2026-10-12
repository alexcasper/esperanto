# GOAL — claude pane (ops_esp)

Identity: worktree `/mnt/d/ops/esperanto/esp_claude`, branch `claude`. Role:
**DICT — dictionary pipeline**.

Coordinator: glm pane (`/mnt/d/ops/esperanto/esp_glm`, branch `glm`) is the
sole merger. Never `git merge` yourself; commit to `claude` branch only.

## Objective

Grow the Esperanto dictionary beyond v1 (Universala Vortaro 1905, 2773
root-cited entries — see DICT/README.md). The corpus (CORPUS/, 302 sources)
is the source of truth for what modern/attested vocabulary to add.

## Non-goals

No corpus acquisition (glm), no grammar guide or web app (gemini). No
rewriting the v1 UV pipeline — extend it.

## Steps

1. Create your work bead: `bd create --title "DICT v2: corpus-attested
   vocabulary beyond Universala Vortaro" --assignee claude` then claim it.
2. Survey DICT/README.md + entries.jsonl schema, and the corpus vocabulary
   gap: which frequent corpus words (n-gram counts from CORPUS/) are missing
   from entries.jsonl. Use DICT/tools/ for anything reusable.
3. Add entries in schema-consistent JSONL, keeping Esperanto alphabetical
   order; document source attribution per entry (corpus citation or published
   dictionary source — respect licensing; QUARANTINE/ content is never a
   source).
4. Cross-link new entries to GRAMMAR sections where morphology is involved
   (pattern exists from esp-hdt).
5. When done: `bd comment <id> "ready for merge"` + commit to `claude`.

## Exit criteria

- Bead created/claimed; gap analysis written to DICT/NOTES-v2.md.
- ≥1 batch of new entries merged-ready with per-entry source attribution.

## Stand-down

On "stand down": stop, leave bead in current status, final `bd comment` with
where you stopped.
