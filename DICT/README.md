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

## Coverage

### v1 — Fundamento (Universala Vortaro, 1905)

| Kind | Count |
|---|---|
| Root-cited entries (`abat'`, `zorg'ant'`, …) | 2773 |
| — plain roots | 2523 |
| — compound demonstrations with morphology | 210 |
| — word-building affixes (39: 8 prefixes, 31 suffixes) | 39 |
| Grammatical words (endings, particles, correlatives, pronouns, numerals, prepositions, conjunctions) | 138 |
| **Subtotal** | **2911** |

### v2 — corpus-mined (`source: corpus-mined`)

2216 entries the 1905 core cannot contain, mined from the 141-source corpus in
`CORPUS/` and reviewed by hand across two rounds: the internationalisms
Esperanto took on after the Fundamento (*kongreso*, *telefono*, *aeroplano*,
*sennaciismo*), lexicalised compounds (*lernolibro*, *samideano*) and
productive derivations (*virino*, *malgranda*, *esperantisto*). 2034 are
attested in three or more independent sources (recounted in esp-58p, below).

`derived: true` marks a word built by regular affixation on a root already
held — *abonanto*, *agado*, *aliulo* — and since esp-58p it means exactly
that the entry's `morphology` carries a self-validating affix segmentation
(`prefixes`/`suffixes`); 4468 of the 6556 corpus-mined entries. Settled
policy is that these earn entries, because a reader looking up *reĝino*
should find it; the flag lets a consumer wanting only roots and opaque
compounds filter them out.

**Attestation** (`count`, `sources`) on every corpus-mined entry is a direct
corpus scan of the word's regular inflected forms (`tools/attest_scan.py`,
esp-58p), over the same files the miner reads. It replaced two undercounts:
the pre-v2 layer's `sources` was capped at 5, and the miner drops a form seen
only once in a shard.

Mined by `tools/mine_lemmas.py`, reviewed via `tools/review_shard.py`, merged
by `tools/reconcile_lemmas.py` and written here by `tools/promote_lemmas.py`.
Candidates judged proper nouns, foreign words, fragments or OCR artefacts are
excluded by construction; the full verdict record, including disagreements
between reviewers, is `DICT/verdicts.jsonl`.

**v2 batch 1 (esp-rac, 2026-10-06)** added 487 more entries from the 302-source
corpus, each attested in 18+ independent sources (see `DICT/NOTES-v2.md`).
416 of them carry affix segmentation and `grammar_refs`
to GRAMMAR §2. Gap analysis: `python3 tools/gap_report.py`; review batches:
`DICT/review/*.tsv`, applied by `tools/apply_review.py`. **Batch 2
(esp-xge)** added 489 more (11–36 sources each), **batch 3 (esp-ytn)** 484
(8–11), **batch 4 (esp-e26)** 485 (6–8), **batch 5 (esp-eb7)** 483 (5–6).
**Batch 6 (esp-73s)** added 476, the first from the Vikipedio-scale corpus
under the register-aware bar (esp-nuk): every one attested in 6–8
non-Wikipedia sources, plus up to 1,657 Wikipedia articles. **Batch 7
(esp-weg)** added 478 (5–6 non-Wikipedia sources), with literary citations
first (esp-0mu). **Batch 8 (esp-gwn)** added 485 (5 non-Wikipedia
sources), **batch 9 (esp-3ke)** 473 (5–4).
Corpus-mined total: **6556** (4340 from v2 batches). esp-58p segmented the
2216 earlier entries too: **4468** corpus-mined entries now carry affix
segmentation and `grammar_refs` to §2.

| Kind | Count |
|---|---|
| noun | 1315 |
| adj | 550 |
| adv | 237 |
| verb | 92 |
| num | 11 |
| interj | 8 |
| prep | 3 |
| **Subtotal** | **2216** |

### v3 — O'Connor & Hayes, English-Esperanto Dictionary (c.1906)

5935 entries parsed from `CORPUS/pg-16967.txt`, tagged `source: oconnor-1906`,
of which 2655 are flagged `derived`. This is a different class of evidence from
the corpus-mined layer: an editorially compiled word list rather than attested
usage, so these entries carry **no `attestation` field** — a consumer can tell
which claim rests on citations and which on a lexicographer's authority.
Nothing here overwrites a Fundamento or corpus-mined entry; only words absent
from both are added, and each keeps its `english_headwords`.

Caveat: the English glosses are the source's own. Eleven of them use period
terms (*negro*, *heathen*, *lunatic*, *cripple*, …). Settled policy
(esp-54v, option b): `gloss_en` carries a neutral present-day wording, and
the source's original wording is preserved verbatim in a `dated_gloss` field
on exactly those entries. `english_headwords` and `english-index.jsonl` keep
the source's own terms — they are the lookup direction into the 1906 source,
and their provenance is already tagged by `source: oconnor-1906`. The
mapping lives in `DATED_GLOSSES` in `tools/parse_oconnor.py`.

Two further artefacts come from the same source:

- `english-index.jsonl` — 12497 English headwords to their Esperanto
  equivalents, including 242 phrasal translations (*abaft → posta parto*).
  This is the lookup direction `entries.jsonl` cannot serve.
- `affix-examples.jsonl` — 56 morpheme-segmented affix demonstrations from
  the grammar preface (*bo'patro = father-in-law*), which state the direction
  the other way round and would corrupt the headword list if read as entries.

**Total: 11062 entries** (2911 Fundamento · 2216 corpus-mined · 5935 O'Connor).

POS distribution: 6555 noun · 2047 adj · 1907 verb · 399 adv · 31 suffix · 30 prep · 24 pron · 23 num · 12 particle · 9 ending · 9 interj · 8 prefix · 7 conj · 1 art.

## Schema

Every line is one JSON object. Required keys: `word`, `pos`, `gloss_en`.
Optional keys: `gloss_fr`, `root`, `morphology`, `source`, `dated_gloss`
(the source's original period wording where `gloss_en` was modernised —
oconnor-1906 only), `grammar_refs` (cross-links to `GRAMMAR/grammar.md`
sections; affixes → §2, correlatives → §3, negative correlatives → §6.2,
`ujo` → §6.1 — regenerated by `python3 tools/link_grammar.py`), and on
corpus-mined entries `attestation` (`count` of occurrences and number of
independent `sources`) and `citations` (up to three real passages, each with
its `source` file and `text`).

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
- No duplicate `word` values — **case-insensitively** (see the
  duplicate-headword rule at the end of this file); Esperanto-alphabetical
  sort order
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

## Coverage (v2) — SKL-8m1r.6 (t3/Galahad)

Merged from **Reta Vortaro (ReVo)** XML source (`revuloj/revo-fonto`, 13,077
articles → 30,648 drv heads; 11,793 without English trd skipped; 2,666 dups
of v1 skipped):

| Source | Entries |
|---|---|
| Fundamento/UV-1905 (v1, authoritative) | 2,911 |
| ReVo roots + derivatives, UV-official (`ofc=*`) | 6,110 |
| ReVo roots + derivatives, non-official | 6,084 |
| ReVo **Official Additions OA1–10** (`ofc=N`) | 3,995 |
| **Total** | **19,100** |

OA breakdown: OA-1 1360 · OA-2 724 · OA-10 595 · OA-8 393 · OA-9 339 ·
OA-3 285 · OA-4 240 · OA-7 23 · OA-6 21 · OA-5 15. (The broken Akademio
`ajakso` endpoint was bypassed entirely — ReVo's `<ofc>` tags carry the same
officialness data.) Rebuild: `python3 tools/merge_revo.py <revo-fonto>/revo`.

### Duplicate-headword rule (esp-lyp)

`word` keys are unique **case-insensitively**. Where the Fundamento UV cites
a word capitalised (the religious and calendar terms `Dio`, `Kristo`,
`Pasko`, `Julia`, `Marto`, `Mesio`, `Pentekosto`) and ReVo supplies the same
word lowercase, **the Fundamento entry wins** — it is the authoritative 1905
core — and the ReVo twin is dropped. `tools/merge_revo.py` now dedupes on
`word.lower()`, so a re-run cannot reintroduce this. One case went the other
way: the v1 `Mario` "nobleman" entry was a misparse of the UV's `nj'`
feminine-diminutive article (no `Mario` exists in the UV); it was replaced by
the restored `nj` suffix entry, and ReVo's real `mario` (the name) stands.
Applied 2026-09-26 as a data fix on `entries.jsonl` (8 duplicate keys
removed, 24673 → 24666 lines).

### Grammar cross-links (esp-hdt)

`tools/link_grammar.py` adds `grammar_refs` to the entries the grammar guide
explains: word-building affixes → §2 (Morfologio), the correlative grid →
§3 (tabelvortoj), negative correlatives → also §6.2 (single negation),
`ujo` → §6.1 (country names). All 45 correlatives are linked. Six cells —
`nenial`, `neniom`, `ties`, `ĉial`, `ĉies`, `ĉiom` — existed in no layer
until esp-f76 filled them with `tools/fill_correlatives.py` (`source:
correlative-grid`): attestation by corpus scan (*ties* 86 sources down to
*ĉial* 8), three hand-picked usage citations from distinct sources each,
pinned by file and line and re-verified against `CORPUS/` on every run. The
miner skips correlatives by design, so this is the only route for them.
Since esp-rac, segmented corpus-mined derivations also link to §2. 3063
entries linked in all. Idempotent; re-run after any entries.jsonl rebuild.

— t3/Galahad · SKL-8m1r.6 · 2026-08-28
