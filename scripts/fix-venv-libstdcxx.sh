#!/usr/bin/env bash
# fix-venv-libstdcxx.sh -- make libstdc++.so.6 resolvable inside .venv on NixOS
#
# NixOS has no global libstdc++ on the dynamic linker's search path, so
# C++-built wheels (greenlet, ...) fail with:
#   ImportError: libstdc++.so.6: cannot open shared object file
#
# This script (idempotent, safe to re-run) does two things:
#   1. Installs a .pth into site-packages that preloads libstdc++ with
#      RTLD_GLOBAL at interpreter startup -- fixes EVERY invocation
#      style, including .venv/bin/python and uv run without activation.
#      (LD_LIBRARY_PATH alone can't do this: the loader reads it before
#      Python starts.)
#   2. Patches bin/activate{,.fish,.csh} to export LD_LIBRARY_PATH on
#      activation and restore it on deactivate (helps child processes).
#
# Re-run after: recreating the venv (`uv venv`, python bump) or a NixOS
# generation change (it picks the newest gcc-*-lib in /nix/store).
#
# Usage: bash scripts/fix-venv-libstdcxx.sh   (override lib dir: LIBDIR=...)
set -euo pipefail

REPO=$(cd "$(dirname "$0")/.." && pwd)
VENV="$REPO/.venv"
[ -f "$VENV/pyvenv.cfg" ] || { echo "ERROR: $VENV is not a venv" >&2; exit 1; }

if [ -n "${LIBDIR:-}" ]; then
    :
else
    LIB=$(ls -t /nix/store/*-gcc-*-lib/lib/libstdc++.so.6 2>/dev/null | head -n1)
    [ -n "$LIB" ] || { echo "ERROR: no /nix/store/*-gcc-*-lib/lib/libstdc++.so.6 found" >&2; exit 1; }
    LIBDIR=$(dirname "$LIB")
fi
[ -e "$LIBDIR/libstdc++.so.6" ] || { echo "ERROR: $LIBDIR/libstdc++.so.6 missing" >&2; exit 1; }
echo "Using libstdc++ from: $LIBDIR"

SITE=$("$VENV/bin/python" -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])')

"$VENV/bin/python" - "$LIBDIR" "$SITE" <<'PYEOF'
import os
import sys

libdir, site = sys.argv[1], sys.argv[2]
BIN = os.path.abspath(os.path.join(site, "..", "..", "..", "bin"))

# ---- 1. site-packages .pth (the actual fix; works without activation) ----
MODULE = '''"""NixOS: make libstdc++.so.6 resolvable for compiled wheels in this venv.

Installed by scripts/fix-venv-libstdcxx.sh (do not edit by hand; re-run
that script instead). LD_LIBRARY_PATH is read by the loader at process
start, so setting it from inside Python is too late for the current
process. Instead:

1. dlopen libstdc++ with RTLD_GLOBAL -- later dlopen() of wheels like
   greenlet then satisfies DT_NEEDED "libstdc++.so.6" by SONAME match.
2. Prepend the lib dir to os.environ["LD_LIBRARY_PATH"] so subprocesses
   inherit it.

This module must never raise: interpreter startup depends on it.
"""
import ctypes
import glob
import os

_PINNED = %(libdir)r + "/libstdc++.so.6"


def _candidate():
    if os.path.exists(_PINNED):
        return _PINNED
    # Pinned path vanished (NixOS upgrade + GC): fall back to the most
    # recently built gcc lib still in the store.
    try:
        cands = glob.glob("/nix/store/*-gcc-*-lib/lib/libstdc++.so.6")
        return max(cands, key=os.path.getmtime) if cands else None
    except OSError:
        return None


def _apply():
    lib = _candidate()
    if not lib:
        found = ctypes.util.find_library("stdc++")
        if found:
            try:
                ctypes.CDLL(found, mode=ctypes.RTLD_GLOBAL)
            except OSError:
                pass
        return
    try:
        ctypes.CDLL(lib, mode=ctypes.RTLD_GLOBAL)
    except OSError:
        pass
    d = os.path.dirname(lib)
    cur = os.environ.get("LD_LIBRARY_PATH", "")
    if d not in cur.split(":"):
        os.environ["LD_LIBRARY_PATH"] = d + (":" + cur if cur else "")


try:
    _apply()
except Exception:
    pass
''' % {"libdir": libdir}

with open(os.path.join(site, "_nixos_libstdcpp.py"), "w") as f:
    f.write(MODULE)
with open(os.path.join(site, "nixos_libstdcpp.pth"), "w") as f:
    f.write("import _nixos_libstdcpp\n")

# ---- 2. activate scripts: export on activate, restore on deactivate ----
# Line-based on purpose: no regex spanning lines (an earlier regex
# version ate everything to EOF and truncated the scripts).

MARK_BEGIN = "# >>> nixos-libstdc++"
MARK_END = "# <<< nixos-libstdc++"


def strip_marked(lines):
    out, skipping = [], False
    for ln in lines:
        s = ln.lstrip()
        if skipping:
            if s.startswith(MARK_END):
                skipping = False
            continue
        if s.startswith(MARK_BEGIN):
            # also drop the blank line that precedes our appended blocks
            if out and out[-1].strip() == "":
                out.pop()
            skipping = True
            continue
        out.append(ln)
    return out


def reindent(template, indent):
    return [(indent + t[4:]) if t.startswith("    ") else t for t in template]


def insert_after_closed_block(lines, needle, closer, block):
    """Insert block after the first `needle` line's enclosing block,
    closed by a line whose lstrip() == closer. Returns None on miss."""
    start = None
    for i, ln in enumerate(lines):
        if needle in ln:
            start = i
            break
    if start is None:
        return None
    for j in range(start, len(lines)):
        if lines[j].strip() == closer:
            indent = lines[j][: len(lines[j]) - len(lines[j].lstrip())]
            return lines[: j + 1] + reindent(block, indent) + lines[j + 1:]
    return None


BASH_RESTORE = [l + "\n" for l in """    # >>> nixos-libstdc++-restore >>>
    if ! [ -z "${_OLD_VIRTUAL_LD_LIBRARY_PATH+_}" ] ; then
        LD_LIBRARY_PATH="$_OLD_VIRTUAL_LD_LIBRARY_PATH"
        export LD_LIBRARY_PATH
        unset _OLD_VIRTUAL_LD_LIBRARY_PATH
    fi
    if ! [ -z "${_OLD_VIRTUAL_LD_LIBRARY_PATH_UNSET+_}" ] ; then
        unset LD_LIBRARY_PATH
        unset _OLD_VIRTUAL_LD_LIBRARY_PATH_UNSET
    fi
    # <<< nixos-libstdc++-restore <<<
""".splitlines()]

BASH_ACTIVATE = """\

# >>> nixos-libstdc++ >>>
# NixOS has no global libstdc++ on the loader path, so compiled wheels
# (greenlet etc.) fail to import. Added by scripts/fix-venv-libstdcxx.sh
# -- re-run it after recreating the venv. `deactivate` restores the
# previous value. The site-packages .pth covers non-activated runs.
if ! [ -z "${LD_LIBRARY_PATH+_}" ] ; then
    _OLD_VIRTUAL_LD_LIBRARY_PATH="$LD_LIBRARY_PATH"
    unset _OLD_VIRTUAL_LD_LIBRARY_PATH_UNSET
else
    unset _OLD_VIRTUAL_LD_LIBRARY_PATH
    _OLD_VIRTUAL_LD_LIBRARY_PATH_UNSET=1
fi
export LD_LIBRARY_PATH="%(libdir)s${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
# <<< nixos-libstdc++ <<<
""" % {"libdir": libdir}

FISH_RESTORE = [l + "\n" for l in """    # >>> nixos-libstdc++-restore >>>
    if set -q _OLD_VIRTUAL_LD_LIBRARY_PATH
        set -gx LD_LIBRARY_PATH $_OLD_VIRTUAL_LD_LIBRARY_PATH
        set -e _OLD_VIRTUAL_LD_LIBRARY_PATH
    end
    if set -q _OLD_VIRTUAL_LD_LIBRARY_PATH_UNSET
        set -e LD_LIBRARY_PATH
        set -e _OLD_VIRTUAL_LD_LIBRARY_PATH_UNSET
    end
    # <<< nixos-libstdc++-restore <<<
""".splitlines()]

FISH_ACTIVATE = """\

# >>> nixos-libstdc++ >>>
# NixOS has no global libstdc++ on the loader path, so compiled wheels
# (greenlet etc.) fail to import. Added by scripts/fix-venv-libstdcxx.sh
# -- re-run it after recreating the venv. `deactivate` restores the
# previous value. The site-packages .pth covers non-activated runs.
if set -q LD_LIBRARY_PATH
    set -gx _OLD_VIRTUAL_LD_LIBRARY_PATH $LD_LIBRARY_PATH
    set -e _OLD_VIRTUAL_LD_LIBRARY_PATH_UNSET
else
    set -e _OLD_VIRTUAL_LD_LIBRARY_PATH
    set _OLD_VIRTUAL_LD_LIBRARY_PATH_UNSET 1
end
set -gx LD_LIBRARY_PATH %(libdir)s $LD_LIBRARY_PATH
# <<< nixos-libstdc++ <<<
""" % {"libdir": libdir}

CSH_ALIAS_TESTS = (
    'test $?_OLD_VIRTUAL_LD_LIBRARY_PATH != 0 && '
    'setenv LD_LIBRARY_PATH "$_OLD_VIRTUAL_LD_LIBRARY_PATH:q" && '
    'unset _OLD_VIRTUAL_LD_LIBRARY_PATH; '
    'test $?_OLD_VIRTUAL_LD_LIBRARY_PATH_UNSET != 0 && '
    'unsetenv LD_LIBRARY_PATH && unset _OLD_VIRTUAL_LD_LIBRARY_PATH_UNSET; '
)

CSH_ACTIVATE = """
# >>> nixos-libstdc++ >>>
# NixOS has no global libstdc++ on the loader path, so compiled wheels
# (greenlet etc.) fail to import. Added by scripts/fix-venv-libstdcxx.sh
# -- re-run it after recreating the venv. `deactivate` restores the
# previous value. The site-packages .pth covers non-activated runs.
if ($?LD_LIBRARY_PATH) then
    set _OLD_VIRTUAL_LD_LIBRARY_PATH="$LD_LIBRARY_PATH:q"
else
    set _OLD_VIRTUAL_LD_LIBRARY_PATH_UNSET=1
endif
if ($?_OLD_VIRTUAL_LD_LIBRARY_PATH_UNSET) then
    setenv LD_LIBRARY_PATH "%(libdir)s"
else
    setenv LD_LIBRARY_PATH "%(libdir)s:$LD_LIBRARY_PATH:q"
endif
# <<< nixos-libstdc++ <<<
""" % {"libdir": libdir}


def read_lines(path):
    with open(path) as f:
        return f.readlines()


def write_lines(path, lines):
    with open(path, "w") as f:
        f.write("".join(lines))


# ---- bash/zsh/ksh ----
p = os.path.join(BIN, "activate")
lines = strip_marked(read_lines(p))
lines = insert_after_closed_block(
    lines, "_OLD_VIRTUAL_PYTHONHOME", "fi", BASH_RESTORE)
if lines is None:
    print(f"  {p}: anchor not found, skipped")
else:
    write_lines(p, lines + [BASH_ACTIVATE])
    print(f"  {p}: patched")

# ---- fish ----
p = os.path.join(BIN, "activate.fish")
lines = strip_marked(read_lines(p))
lines = insert_after_closed_block(
    lines, "_OLD_VIRTUAL_PYTHONHOME", "end", FISH_RESTORE)
if lines is None:
    print(f"  {p}: anchor not found, skipped")
else:
    write_lines(p, lines + [FISH_ACTIVATE])
    print(f"  {p}: patched")

# ---- csh ----
p = os.path.join(BIN, "activate.csh")
lines = strip_marked(read_lines(p))
out, alias_done, path_done = [], False, False
for ln in lines:
    if ln.startswith("alias deactivate"):
        if "_OLD_VIRTUAL_LD_LIBRARY_PATH" in ln:
            alias_done = True  # already hooked by a previous run
        else:
            ln = ln.replace("unsetenv VIRTUAL_ENV;", CSH_ALIAS_TESTS + "unsetenv VIRTUAL_ENV;", 1)
            alias_done = True
    if ln.startswith('setenv PATH "$VIRTUAL_ENV') and not path_done:
        ln = ln.rstrip("\n") + "\n" + CSH_ACTIVATE
        path_done = True
    out.append(ln)
if alias_done and path_done:
    write_lines(p, out)
    print(f"  {p}: patched")
else:
    print(f"  {p}: anchors not found (alias={alias_done}, path={path_done}), skipped")
PYEOF

# ---------------------------------------------------------------- verify --
echo "-- verify --"
bash -n "$VENV/bin/activate" && echo "activate: bash syntax OK"
"$VENV/bin/python" - <<'PYEOF'
import os
print("LD_LIBRARY_PATH (in-process):", os.environ.get("LD_LIBRARY_PATH", "<unset>"))
try:
    import greenlet
    print("greenlet import:", greenlet.__version__)
except ImportError as e:
    print("greenlet not installed or failed:", e)
PYEOF
echo "Done."
