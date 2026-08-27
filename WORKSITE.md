# Worksite ops (hq#171)

- Branch per node/agent pair: j1-lancelot, j2-gawain, t3-galahad, t4-percival, r5-tristan, j6-bedivere.
- Work lands via PRs to main; tracking on the project board + beads SKL-8m1r.*.
- Node clock is truth; dawn/harness stamps run +1h ahead.

## Beads (bd)

- Local tracker for DICT/GRAMMAR work: prefix `esp`, embedded Dolt backend in
  `.beads/embeddeddolt/` (gitignored). `bd ready` for claimable work.
- Dolt sync remote is this repo (`refs/dolt/data`). `bd dolt push` only works
  from a clone with full-ref push rights — Claude web/CI containers get a token
  scoped to `refs/heads/*` and are rejected with HTTP 403.
- So the durable carrier is `.beads/issues.jsonl`, committed and auto-exported
  after writes. A fresh container rebuilds the database with `bd import`.
- `scripts/ensure-beads.sh` is the SessionStart shim: installs `bd` when the
  container lacks it (background build; release tarballs are not reachable
  through the sandbox proxy), hydrates from the JSONL, then runs `bd prime`.
