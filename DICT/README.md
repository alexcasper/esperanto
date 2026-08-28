# DICT/ — Esperanto JSONL dictionary

Machine-readable Esperanto dictionary, seeded from the **Universala Vortaro**
(UV) of the *Fundamento de Esperanto* (Zamenhof, 1905) — the authoritative,
unchangeable core vocabulary of the language.

- `entries.jsonl` — one JSON object per line, UTF-8, Esperanto alphabetical order
- `tools/` — the full scrape → parse → build pipeline (reproducible)

## Source

- **Document**: *Universala Vortaro de la Lingvo Internacia Esperanto*,
  Fundamento de Esperanto, 1905 edition as published by the
  [Akademio de Esperanto](https://akademio-de-esperanto.org/fundamento/universala_vortaro.html).
- Each UV entry carries parallel glosses in French, English, German, Russian
  (pre-1918 orthography), and Polish; the pipeline parses all five, the
  dictionary keeps `gloss_en` (primary) and `gloss_fr` (etymological hint).
- Rebuild: `sh tools/scrape_uv.sh` (fetches, parses, rebuilds `entries.jsonl`).

## Coverage (v1)

| Kind | Count |
|---|---|
| Root-cited entries (`abat'`, `zorg'ant'`, …) | 2773 |
| — plain roots | 2523 |
| — compound demonstrations with morphology | 210 |
| — word-building affixes (39: 8 prefixes, 31 suffixes) | 39 |
| Grammatical words (endings, particles, correlatives, pronouns, numerals, prepositions, conjunctions) | 138 |
| **Total** | **2911** |

POS distribution: 1830 noun · 556 verb · 351 adj · 42 adv · 31 suffix ·
27 prep · 24 pron · 12 particle · 12 num · 9 ending · 8 prefix · 7 conj ·
1 art · 1 interj.

## Schema

Every line is one JSON object. Required keys: `word`, `pos`, `gloss_en`.
Optional keys: `gloss_fr`, `root`, `morphology`, `source`.

```json
{"word":"abelo","pos":"noun","gloss_en":"bee","gloss_fr":"abeille","root":"abel","morphology":{"stem":"abel","ending":"o"},"source":"Fundamento/UV-1905"}
{"word":"zorganto","pos":"noun","gloss_en":"tutor","gloss_fr":"tuteur","root":"zorgant","morphology":{"stem":"zorg","suffixes":[{"m":"ant","gloss":"active participle (being)"}],"ending":"o"},"source":"Fundamento/UV-1905"}
{"word":"vidi","pos":"verb","gloss_en":"see","gloss_fr":"voir","root":"vid","morphology":{"stem":"vid","ending":"i"},"source":"Fundamento/UV-1905"}
{"word":"la","pos":"art","gloss_en":"the","gloss_fr":"l’, la article défini (le, la, les","source":"Fundamento/UV-1905"}
```

- `word` — citation form. Roots are cited with the ending matching their
  inferred POS (`-o` noun, `-i` verb, `-a` adjective); grammatical words and
  numerals stand as-is; affixes are bare morphemes with `pos` `prefix`/`suffix`.
- `pos` — one of: noun, verb, adj, adv, pron, prep, conj, num, art, particle,
  interj, ending, prefix, suffix.
- `morphology` — segmentation into `prefixes` / `stem` / `suffixes` / `ending`
  with per-morpheme glosses. Segmentation is emitted only when every stripped
  affix remainder is itself a UV root (self-validating), otherwise just
  `stem` + `ending`.
- `source` — provenance tag (`Fundamento/UV-1905` for all current lines).

### POS inference (documented heuristic)

Roots in the UV are cited POS-neutrally (bare root + apostrophe), so POS is
inferred from the parallel glosses: English `to …` → verb; French infinitive
(-er/-ir/-oir/-re) agreeing with a German infinitive (-en) → verb; English
adjectival suffixes (-ous/-ful/-ish/-able/-ible/…) or French -eux/-able/-ible
with adjectival English → adj; a curated override list covers classic
adjectives whose glosses hide their category (bel-, bon-, grand-, san-, …);
default noun. Known limitation: a minority of roots may carry a default-noun
POS despite verbal/adjectival primary sense; fixing is a data-review pass,
tracked for v2 (see roadmap).

## Validation

- Every line parses as JSON (`python3 -m json.tool` per line / jq).
- No duplicate `word` values; Esperanto-alphabetical sort order
  (a b c ĉ d e f g ĝ h ĥ i j ĵ k l m n o p r s ŝ t u ŭ v z).

## Roadmap (v2+)

1. **Official Additions (Oficialaj Aldonoj I–X)** — the Akademio's
   *Akademia Vortaro* search is AJAX-only and its `ajakso` endpoint currently
   returns raw PHP source (misconfigured), so the ~1k added official roots
   could not be scraped cleanly this pass. Alternative source: Reta Vortaro
   (ReVo) XML dumps or the printed OA lists.
2. **Baza Radikaro Oficiala (BRO)** groups for frequency banding.
3. **Extended vocabulary** (~16k+ incl. non-official words) via ReVo/PIV-open
   lists and RAW/ corpus extraction (SKL-8m1r.2 corpus work).
4. POS review pass + `examples` field once RAW/ corpus has texts.

— t4/Percival · SKL-8m1r.3 · hq#171 · 2026-08-28
