#!/usr/bin/env bash
#
# SessionStart shim for beads (bd).
#
# Web/CI sessions run in a fresh, ephemeral container: bd is not installed and
# .beads/embeddeddolt/ (the Dolt database) is gitignored, so neither survives.
# This script makes `bd` available again and hydrates the database from the
# committed .beads/issues.jsonl, then hands off to `bd prime --hook-json`.
#
# Installing bd means building it from source (release tarballs are not
# reachable from every sandbox), which takes minutes -- far longer than a
# session-start hook may block. So a missing bd is installed in the background
# and this session is told to retry; the next session finds it ready.

set -uo pipefail

REPO_ROOT="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
GOBIN_DIR="${GOBIN:-${GOPATH:-$HOME/go}/bin}"
STATE_DIR="${TMPDIR:-/tmp}/beads-bootstrap"
LOCK="$STATE_DIR/install.lock"
LOG="$STATE_DIR/install.log"
INSTALL_URL="https://raw.githubusercontent.com/gastownhall/beads/main/scripts/install.sh"

find_bd() {
    local candidate
    if candidate=$(command -v bd 2>/dev/null); then
        printf '%s\n' "$candidate"
        return 0
    fi
    for candidate in "$GOBIN_DIR/bd" "$HOME/go/bin/bd" /root/go/bin/bd /usr/local/bin/bd; do
        if [ -x "$candidate" ]; then
            printf '%s\n' "$candidate"
            return 0
        fi
    done
    return 1
}

# Emit a SessionStart hook payload. $1 is the context string; it must not
# contain characters that need JSON escaping beyond the \n we write literally.
emit_context() {
    printf '{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"%s"}}\n' "$1"
}

# Put bd on PATH for the agent's own shells, not just this hook.
link_onto_path() {
    local bd_path=$1
    if [ ! -e /usr/local/bin/bd ] && [ -w /usr/local/bin ]; then
        ln -sf "$bd_path" /usr/local/bin/bd 2>/dev/null || true
    fi
}

# Rebuild local state that git does not carry: the Dolt database itself.
hydrate() {
    local bd_path=$1
    if [ ! -d "$REPO_ROOT/.beads/embeddeddolt" ]; then
        BD_NON_INTERACTIVE=1 "$bd_path" -C "$REPO_ROOT" init \
            --init-if-missing --non-interactive --quiet \
            --skip-agents --skip-hooks >/dev/null 2>&1 || return 1
    fi
    if [ -s "$REPO_ROOT/.beads/issues.jsonl" ]; then
        "$bd_path" -C "$REPO_ROOT" import >/dev/null 2>&1 || true
    fi
    "$bd_path" -C "$REPO_ROOT" hooks install >/dev/null 2>&1 || true
}

start_background_install() {
    mkdir -p "$STATE_DIR"
    # Single-flight: if another session already kicked off the build, leave it be.
    mkdir "$LOCK" 2>/dev/null || return 0
    (
        trap 'rmdir "$LOCK" 2>/dev/null' EXIT
        curl -fsSL "$INSTALL_URL" | bash >"$LOG" 2>&1
        if bd_path=$(find_bd); then
            link_onto_path "$bd_path"
            hydrate "$bd_path"
        fi
    ) >/dev/null 2>&1 &
}

if bd_path=$(find_bd); then
    link_onto_path "$bd_path"
    hydrate "$bd_path"
    exec "$bd_path" -C "$REPO_ROOT" prime --hook-json
fi

start_background_install
emit_context "beads (bd) is not installed in this container yet; a background build was started (log: $LOG). Issue tracking for this repo lives in beads, so do not fall back to markdown TODOs. Re-check with 'command -v bd || ls /root/go/bin/bd' in a few minutes; once it appears, run 'bd import' to hydrate the database from .beads/issues.jsonl, then 'bd prime' for workflow context and 'bd ready' for claimable work."
