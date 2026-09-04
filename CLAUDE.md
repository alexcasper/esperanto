# Project Instructions for AI Agents

This file provides instructions and context for AI coding agents working on this project.

<!-- BEGIN BEADS INTEGRATION v:1 profile:minimal hash:6cd5cc61 -->
## Beads Issue Tracker

This project uses **bd (beads)** for issue tracking. Run `bd prime` to see full workflow context and commands.

### Quick Reference

```bash
bd ready              # Find available work
bd show <id>          # View issue details
bd update <id> --claim  # Claim work
bd close <id>         # Complete work
```

### Rules

- Use `bd` for ALL task tracking — do NOT use TodoWrite, TaskCreate, or markdown TODO lists
- Run `bd prime` for detailed command reference and session close protocol
- Use `bd remember` for persistent knowledge — do NOT use MEMORY.md files

**Architecture in one line:** issues live in a local Dolt DB; sync uses `refs/dolt/data` on your git remote; `.beads/issues.jsonl` is a passive export. See https://github.com/gastownhall/beads/blob/main/docs/SYNC_CONCEPTS.md for details and anti-patterns.

## Agent Context Profiles

The managed Beads block is task-tracking guidance, not permission to override repository, user, or orchestrator instructions.

- **Conservative (default)**: Use `bd` for task tracking. Do not run git commits, git pushes, or Dolt remote sync unless explicitly asked. At handoff, report changed files, validation, and suggested next commands.
- **Minimal**: Keep tool instruction files as pointers to `bd prime`; use the same conservative git policy unless active instructions say otherwise.
- **Team-maintainer**: Only when the repository explicitly opts in, agents may close beads, run quality gates, commit, and push as part of session close. A current "do not commit" or "do not push" instruction still wins.

## Session Completion

This protocol applies when ending a Beads implementation workflow. It is subordinate to explicit user, repository, and orchestrator instructions.

1. **File issues for remaining work** - Create beads for anything that needs follow-up
2. **Run quality gates** (if code changed) - Tests, linters, builds
3. **Update issue status** - Close finished work, update in-progress items
4. **Handle git/sync by active profile**:
   ```bash
   # Conservative/minimal/default: report status and proposed commands; wait for approval.
   git status

   # Team-maintainer opt-in only, unless current instructions forbid it:
   git pull --rebase
   git push
   git status
   ```
5. **Hand off** - Summarize changes, validation, issue status, and any blocked sync/commit/push step

**Critical rules:**
- Explicit user or orchestrator instructions override this Beads block.
- Do not commit or push without clear authority from the active profile or the current user request.
- If a required sync or push is blocked, stop and report the exact command and error.
<!-- END BEADS INTEGRATION -->


## Build & Test

There is no application to build. The repository is a data pipeline: sources in
`RAW/` become clean text in `CORPUS/`, which becomes vocabulary in `DICT/` and
prose in `GRAMMAR/`. Everything is Python 3 with no third-party dependencies.

`CORPUS/*.txt` and `DICT/shards/` are derived and gitignored. Rebuilding the
corpus is two commands, in this order — the second must follow the first,
because normalising overwrites the files the repair edits:

```bash
python3 tools/normalize_corpus.py           # RAW/ -> CORPUS/ + CORPUS/MANIFEST.tsv
python3 tools/repair_diacritics.py --apply  # restore diacritics a scan dropped
```

A mining round over the corpus:

```bash
python3 tools/mine_lemmas.py --plan 8                     # see the shard packing
for s in 1 2 3 4 5 6 7 8; do
  python3 tools/mine_lemmas.py --shard $s/8 --ledger      # map
done
python3 tools/review_shard.py --shard 1/8 --list          # a reviewer judges
python3 tools/review_shard.py --shard 1/8 --apply F.json
python3 tools/reconcile_lemmas.py --shards 8 --write-ledger   # reduce
python3 tools/promote_lemmas.py --rebuild                 # -> DICT/entries.jsonl
```

Checks worth running before committing a data change:

```bash
python3 tools/score_esperanto_text.py CORPUS/some-file.txt   # is it Esperanto?
python3 tools/promote_lemmas.py --rebuild --dry-run          # what would change
python3 -c "import json;[json.loads(l) for l in open('DICT/entries.jsonl')]"
```

Every tool takes `--dry-run` or prints a report before writing where the
operation is destructive. Use it: a bad `--apply` has cost this project real
work more than once.

## Architecture Overview

Four directories, in dependency order. Each one is derived from the one before
it, and nothing reaches back.

- **`RAW/`** — sources as fetched, one file per work, never hand-edited.
  `PROVENANCE.md` records every one with its origin, date, licence basis and
  hash; `QUALITY.tsv` records its Esperanto-recognisability score. Fetched by
  `tools/fetch_raw_gutenberg.py` (Project Gutenberg) and
  `tools/fetch_raw_vikifontaro.py` (the eo.wikisource XML dump, `Paĝo:`
  namespace, proofread pages only).
- **`CORPUS/`** — body text only: front and back matter stripped, ASCII
  spelling systems undone, mis-encodings repaired. Derived, so gitignored;
  `MANIFEST.tsv` is committed and records what was done to each source.
- **`DICT/`** — the dictionary. `entries.jsonl` is the product;
  `verdicts.jsonl` is the record of every review judgement, which is what
  makes a mining round re-runnable without re-asking a reviewer anything.
- **`GRAMMAR/`** — prose reference, every claim carried by a corpus citation
  in the form `*quote* — source:line`.
- **`QUARANTINE/`** — sources held out with the reason written down. Files stay
  in the repository rather than being deleted, so the provenance record stays
  honest.

`tools/esperanto.py` is the shared morphology: `load_vocabulary`, `analyse`,
`peel_affixes`, `citation_form`, `is_compound`, `participle_infinitive`. Every
other tool answers its question against that one module, so a morphology fix
lands everywhere at once — and breaks everywhere at once, which is why the
docstrings there record what each rule was wrong about before.

## Conventions & Patterns

**Measure, don't assume.** Every threshold and exclusion in these tools was
set by measuring the corpus, and the docstring says what the measurement was.
When you change one, re-measure and update the number. Several of them were
wrong in both directions before someone checked.

**Never widen a rule without auditing what it now admits.** The loosened
compound rule accepted 7198 new words; the highest-frequency ones turned out
to be proper names (`Vinicii` as `vin` + `icii`, 910 occurrences). A dry run
plus a random sample plus a look at the top of the frequency list catches this;
nothing else does.

**A vocabulary check is not a safety net once the dictionary is large.** With
27k entries the morphology can build almost anything, so "the result is a
word" stopped being evidence. One repair pass proposed 21580 changes on that
basis, turning `Petronius` into `Petronĵus` and the English `our` into `ĉur`.
Gate on a closed list, a file proven damaged, or a form the dictionary
actually lists.

**Fix the extractor, not the text.** Where a defect traces to a source, go and
read that source's own markup before patching the output. `ezaro` for `cezaro`
looked like a scan error for 113 occurrences; the wikitext said
`{{SIC|c|C}}ezaro` and the bug was ours.

**Corpus data is derived; review work is not.** `CORPUS/` and `DICT/shards/`
can be regenerated at will. `DICT/verdicts.jsonl` cannot — it is human
judgement, and re-mining must restore it rather than discard it. Keying shard
records on anything that a morphology change can move has silently cost 917
approved lemmas once already.

**Quarantine with `git mv`, never `rm`.** And strike the line in
`RAW/PROVENANCE.md` with the reason.

**File a bead rather than fixing quietly out of scope.** Eight duplicate
headwords, eleven dated glosses and a Latin-binomial defect are open beads
precisely because deciding them is not a code change.

**Parallel reviewers share one scratchpad.** Put the shard number in every
filename you hand an agent, and tell it the directory is shared. Three of
eight agents lost work to a name collision in one round.
