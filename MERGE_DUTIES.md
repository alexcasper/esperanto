# Merge duties

glm is the sole merger. Panes commit to their own branch (glm/claude/gemini)
and mark readiness via `bd comment <id> "ready for merge"`. glm merges to
main (no fast-forward: `git merge --no-ff <branch>`) after reading the diff —
but note the main worktree is on `j6-bedivere` with 9 unmerged commits; PR
that to origin/main first (or coordinate with the human), then merge sibling
branches on top.

Conflict policy: glm resolves; if a data/JSONL file conflicts, regenerate it
from the pipeline rather than hand-merging lines.
