#!/usr/bin/env python3
"""Verify that every citation in GRAMMAR/grammar.md matches lines in CORPUS/."""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORPUS = os.path.join(ROOT, "CORPUS")
GRAMMAR = os.path.join(ROOT, "GRAMMAR", "grammar.md")

def check_citations():
    with open(GRAMMAR, encoding="utf-8") as f:
        text = f.read()

    # Pattern: *quoted text* — `source:line`
    cites = re.findall(r"\*([^*]+)\*\s*—\s*`([^`:]+):(\d+)`", text)
    print(f"Found {len(cites)} citations in {GRAMMAR}\n")
    errors = 0

    for quote, src, lineno in cites:
        src_file = src if src.endswith(".txt") else f"{src}.txt"
        path = os.path.join(CORPUS, src_file)
        if not os.path.exists(path):
            print(f"FAIL [FILE NOT FOUND]: {src_file}")
            errors += 1
            continue

        with open(path, encoding="utf-8") as sf:
            lines = [l.rstrip("\r\n") for l in sf]

        lno = int(lineno)
        if lno < 1 or lno > len(lines):
            print(f"FAIL [LINE OUT OF RANGE]: {src}:{lineno} (file has {len(lines)} lines)")
            errors += 1
            continue

        actual_line = lines[lno - 1]
        clean_q = " ".join(quote.split())
        clean_l = " ".join(actual_line.split())

        # Check if the quote is in the line (or within 2-line window for wrapped quotes)
        window = " ".join(" ".join(lines[i].split()) for i in range(max(0, lno - 2), min(len(lines), lno + 2)))

        if clean_q.lower() in clean_l.lower():
            print(f"PASS: {src}:{lineno} -> {clean_q}")
        elif clean_q.lower() in window.lower():
            print(f"PASS (multi-line): {src}:{lineno} -> {clean_q}")
        else:
            print(f"FAIL [MISMATCH]: {src}:{lineno}\n  expected in line: {clean_q}\n  actual line:     {clean_l}\n  context window:  {window}")
            errors += 1

    print(f"\nResult: {len(cites) - errors}/{len(cites)} passed, {errors} errors.")
    return 0 if errors == 0 else 1

if __name__ == "__main__":
    sys.exit(check_citations())
