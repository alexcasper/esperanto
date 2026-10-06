# GOAL — gemini pane (ops_esp)

Identity: worktree `/mnt/d/ops/esperanto/esp_gemini`, branch `gemini`. Role:
**GRAMMAR guide depth + web app (TanStack Start)**.

Coordinator: glm pane (`/mnt/d/ops/esperanto/esp_glm`, branch `glm`) is the
sole merger. Never `git merge` yourself; commit to `gemini` branch only.

## Objective

1. Deepen the grammar guide: GRAMMAR/grammar.md has 6 sections; §6 "Uzado —
   where corpus usage complicates the stated rule" is the growth area. Add
   corpus-cited examples (machine-checkable quotes: *text* — `source:line`).
2. Bring the web app past its template state: it should render the source
   catalog, dictionary, and grammar guide (it was scaffolded in commit
   b70e832 but web/README.md is still the TanStack boilerplate).

## Non-goals

No corpus acquisition (glm), no dictionary entries (claude).

## Steps

1. Create your work bead: `bd create --title "GRAMMAR §6 + web app: corpus
   usage notes and a real UI for DICT/GRAMMAR/corpus catalog" --assignee
   gemini` then claim it.
2. Grammar: mine CORPUS/ for usage that complicates rules (word order
   variation, correlative usage, participle nuance); extend §6 with cited
   examples. Check every quote actually appears at the cited line.
3. Web app: pnpm install already symlinked (web/node_modules → main
   worktree); run `pnpm dev` to verify it starts, then build real routes:
   source catalog (CORPUS/MANIFEST.tsv), dictionary browser (DICT/
   entries.jsonl), grammar guide (GRAMMAR/grammar.md rendered).
4. When each piece is done: `bd comment <id> "ready for merge"` + commit to
   `gemini`.

## Exit criteria

- Bead created/claimed; §6 extended with ≥10 new cited examples, all quotes
  verified against CORPUS/ lines.
- Web app serves the three views locally (dev server screenshot/evidence in
  the bead).

## Stand-down

On "stand down": stop, leave bead in current status, final `bd comment` with
where you stopped.
