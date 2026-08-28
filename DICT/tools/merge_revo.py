#!/usr/bin/env python3
"""DICT v2: merge Reta Vortaro (ReVo) XML roots into entries.jsonl (SKL-8m1r.6).

Source: revuloj/revo-fonto sparse clone (revo/*.xml, 13k+ articles).
Per-article <kap> carries <ofc> ('*' = Fundamento UV, '1'..'10' = Official
Addition N) and <rad>root</rad>/o|/i|/a|/e. English/French glosses come from
<trd lng="en">/<trd lng="fr"> anywhere in the article (first hit).

Merge rule: v1 UV entries are authoritative; a ReVo root whose citation word
already exists is skipped (dedup by word). Output keeps Esperanto sort order.

Usage: python3 tools/merge_revo.py /path/to/revo-fonto/revo [--dry]
"""
import html.entities
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ALPHA = "abcĉdefgĝhĥijĵklmnoprsŝtuŭvz"
RANK = {c: i for i, c in enumerate(ALPHA)}
POS = {"o": "noun", "i": "verb", "a": "adj", "e": "adv"}

EXT = {"leftquot": "“", "rightquot": "”", "amacron": "ā", "lstroke": "ł",
       "eogonek": "ę", "emacron": "ē", "imacron": "ī", "omacron": "ō",
       "umacron": "ū", "aogonek": "ą", "uogonek": "ų", "yod": "י",
       "vav": "ו", "resh": "ר", "lamed": "ל", "he": "ה", "alef": "א",
       "sogonek": "s̨", "iogonek": "į"}

ENT_RE = re.compile(r"&([A-Za-z0-9_]+);")

def unent(s: str) -> str:
    def sub(m):
        name = m.group(1)
        if name in ("amp", "lt", "gt", "quot", "apos"):
            return m.group(0)
        if name in EXT:
            return EXT[name]
        h = html.entities.html5.get(name + ";", html.entities.html5.get(name))
        if h is not None:
            return h
        return "" if "_" in name else name  # c_ib; → drop, bib tags → bare name
    return ENT_RE.sub(sub, s)

def txt(el) -> str:
    return unent("".join(el.itertext())).strip() if el is not None else ""

def parse_article(path: Path):
    raw = path.read_text(encoding="utf-8", errors="replace")
    raw = re.sub(r"<!DOCTYPE[^>]*>", "", raw, count=1)
    raw = unent(raw)
    try:
        root = ET.fromstring(raw)
    except ET.ParseError:
        return []
    art = root.find("art")
    if art is None:
        return []
    kap0 = art.find("kap")
    if kap0 is None or kap0.find("rad") is None:
        return []
    rad = txt(kap0.find("rad"))
    if not rad or "/" in rad or len(rad) < 2:
        return []
    ofc = txt(kap0.find("ofc"))

    def drv_word(kap) -> str:
        parts = [kap.text or ""]
        for ch in kap:
            if ch.tag == "tld":
                parts.append(rad)
                parts.append(ch.tail or "")
            elif ch.tag in ("fnt", "ofc"):
                continue
            else:
                parts.append(unent("".join(ch.itertext())) + (ch.tail or ""))
        w = re.sub(r"\s+", "", "".join(parts))
        w = w.replace("/", "")
        return w.lower()

    out = []
    for drv in art.findall("drv"):
        kap = drv.find("kap")
        if kap is None:
            continue
        word = drv_word(kap)
        if not word or word == rad:
            continue
        en = fr = ""
        for trd in drv.iter("trd"):
            lng = trd.get("lng")
            if lng == "en" and not en:
                en = txt(trd)
            elif lng == "fr" and not fr:
                fr = txt(trd)
            if en and fr:
                break
        tail = word[-1] if word[-1:] in POS else "o"
        out.append({"word": word, "rad": rad, "tail": tail, "ofc": ofc,
                    "gloss_en": en, "gloss_fr": fr})
    return out

def sortkey(w):
    return [RANK.get(c, 99) for c in w.lower()]

def main():
    revo_dir = Path(sys.argv[1])
    dry = "--dry" in sys.argv
    out_path = Path(__file__).resolve().parent.parent / "entries.jsonl"
    entries = [json.loads(l) for l in out_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    have = {e["word"] for e in entries}
    seen = set()
    stats = {"articles": 0, "parsed": 0, "skip_dup": 0, "skip_noen": 0,
             "added": 0, "oa": {}}
    for f in sorted(revo_dir.glob("*.xml")):
        stats["articles"] += 1
        for a in parse_article(f):
            stats["parsed"] += 1
            if a["word"] in have or a["word"] in seen:
                stats["skip_dup"] += 1
                continue
            seen.add(a["word"])
            if not a["gloss_en"]:
                stats["skip_noen"] += 1
                continue
            src = "ReVo"
            if a["ofc"].isdigit() and len(a["ofc"]) <= 2:
                src = f"ReVo/OA-{a['ofc']}"
                stats["oa"][a["ofc"]] = stats["oa"].get(a["ofc"], 0) + 1
            elif a["ofc"] == "*":
                src = "ReVo/UV-*"
            e = {"word": a["word"], "pos": POS.get(a["tail"], "noun"),
                 "gloss_en": a["gloss_en"], "root": a["rad"], "source": src}
            if a["gloss_fr"]:
                e["gloss_fr"] = a["gloss_fr"]
            entries.append(e)
            stats["added"] += 1
    entries.sort(key=lambda e: sortkey(e["word"]))
    words = [e["word"] for e in entries]
    assert len(words) == len(set(words)), "duplicate words after merge"
    if not dry:
        with out_path.open("w", encoding="utf-8") as fh:
            for e in entries:
                fh.write(json.dumps(e, ensure_ascii=False) + "\n")
    print(json.dumps(stats))
    print(f"TOTAL={len(entries)} (+{stats['added']})")

if __name__ == "__main__":
    main()
