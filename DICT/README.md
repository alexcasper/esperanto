# DICT/ — Esperanto JSONL dictionary

Machine-readable Esperanto dictionary, seeded from the **Universala Vortaro**
(UV) of the *Fundamento de Esperanto* (Zamenhof, 1905) — the authoritative,
unchangeable core vocabulary of the language — and extended from Reta Vortaro,
a 1906 English-Esperanto dictionary, and the attested corpus in `CORPUS/`.

- `entries.jsonl` — one JSON object per line, UTF-8, Esperanto alphabetical order
- `english-index.jsonl` — the reverse direction, English headword to Esperanto
- `affix-examples.jsonl` — morpheme-segmented affix demonstrations
- `verdicts.jsonl` — every review judgement made about a corpus candidate
- `DICT/tools/` — the scrape → parse → merge pipeline for the lexicographic
  layers; `tools/` at the repository root holds the corpus pipeline

## Coverage

**27272 entries.** Every count in this section was measured against
`entries.jsonl` as it stands, not carried forward from an earlier pass. The
dictionary has four layers of evidence, and the `source` tag on each line says
which one an entry rests on:

| Layer | `source` | Entries |
|---|---|---|
| Fundamento (Universala Vortaro, 1905) | `Fundamento/UV-1905` | 2911 |
| Reta Vortaro, UV-official roots and derivatives | `ReVo/UV-*` | 5770 |
| Reta Vortaro, non-official | `ReVo` | 6039 |
| Reta Vortaro, Official Additions I–X | `ReVo/OA-1` … `ReVo/OA-10` | 3513 |
| O'Connor & Hayes, English-Esperanto Dictionary (c.1906) | `oconnor-1906` | 4224 |
| Corpus-mined, reviewed by hand | `corpus-mined` | 4815 |

OA breakdown: OA-1 1077 · OA-2 638 · OA-10 574 · OA-8 372 · OA-9 327 ·
OA-3 248 · OA-4 223 · OA-7 23 · OA-6 18 · OA-5 13.

By part of speech: noun 18029 · verb 4138 · adj 4102 · adv 837 · suffix 31 ·
prep 31 · num 29 · pron 24 · interj 14 · particle 12 · ending 9 · prefix 8 ·
conj 7 · art 1.

4110 entries carry `derived: true`, marking a word built by regular affixation
on a root already held — *abonanto*, *agado*, *reĝino*. Settled policy is that
these earn entries, because a reader looking up *reĝino* should find it; the
flag lets a consumer wanting only roots and opaque compounds filter them out.

### What the layers are for

The three lexicographic layers (Fundamento, ReVo, O'Connor) are compiled word
lists: they rest on an editor's authority. The corpus-mined layer rests on
attested usage, and is the only one that carries evidence you can check.

**Fundamento** is the authoritative, unchangeable core: the 1905 Universala
Vortaro as published by the
[Akademio de Esperanto](https://akademio-de-esperanto.org/fundamento/universala_vortaro.html).
Each UV entry carries parallel glosses in French, English, German, Russian
(pre-1918 orthography) and Polish; the pipeline parses all five and keeps
`gloss_en` (primary) and `gloss_fr` (etymological hint). Rebuild:
`sh DICT/tools/scrape_uv.sh`.

**Reta Vortaro (ReVo)** supplies the official additions and the modern
vocabulary the 1905 core cannot contain, from the `revuloj/revo-fonto` XML
(13077 articles → 30648 derivation heads; 11793 with no English translation
skipped, 2666 duplicates of the Fundamento skipped). ReVo's `<ofc>` tags carry
the same officialness data as the Akademio's *Akademia Vortaro*, whose search
endpoint returns raw PHP and could not be scraped. Rebuild:
`python3 DICT/tools/merge_revo.py <revo-fonto>/revo`.

**O'Connor & Hayes** is parsed from `RAW/pg-16967.txt`. These entries carry
**no `attestation` field**, deliberately: a consumer can tell which claim rests
on citations and which on a lexicographer's authority. Nothing here overwrites
a Fundamento or ReVo entry; only words absent from both are added, and each
keeps its `english_headwords`. Two further artefacts come from the same source:

- `english-index.jsonl` — 12497 English headwords to their Esperanto
  equivalents, including 242 phrasal translations (*abaft → posta parto*).
  This is the lookup direction `entries.jsonl` cannot serve.
- `affix-examples.jsonl` — 56 morpheme-segmented affix demonstrations from the
  grammar preface (*bo'patro = father-in-law*), which state the direction the
  other way round and would corrupt the headword list if read as entries.

Caveat: the English glosses are the source's own, and eleven use period terms
(*negro*, *heathen*, *lunatic*, *cripple*). They ship as the source has them,
with the tag marking provenance; whether to modernise them is tracked as a
bead rather than settled here.

**Corpus-mined** entries come from the 299-source corpus in `CORPUS/`: the
internationalisms Esperanto took on after the Fundamento (*kongreso*,
*telefono*, *aeroplano*, *sennaciismo*), lexicalised compounds (*lernolibro*,
*samideano*) and productive derivations. All 4815 carry `attestation` (a
corpus `count` and the number of independent `sources`) and up to three real
`citations`; 3522 are attested in three or more independent sources.

The pipeline is a map-reduce over the corpus, run in rounds:

```
tools/mine_lemmas.py --shard I/N --ledger     # map: candidates, one file per shard
tools/review_shard.py --shard I/N --list      # a reviewer judges them
tools/review_shard.py --shard I/N --apply F   # nine verdicts, closed set
tools/reconcile_lemmas.py --shards N --write-ledger   # reduce: merge, record conflicts
tools/promote_lemmas.py --rebuild             # verdict 'lemma' + a gloss -> entries.jsonl
```

Only the verdict `lemma` reaches the dictionary. Candidates judged
`proper-noun`, `foreign`, `fragment`, `ocr-artifact`, `inflection`, `numeral`,
`nonce` or `uncertain` are excluded by construction, and the judgement is kept
so no later round asks the same question again: `DICT/verdicts.jsonl` holds
7440 of them, including the cases where two reviewers disagreed.

## Schema

Every line is one JSON object. Required keys: `word`, `pos`, `gloss_en`.
Optional keys: `gloss_fr`, `root`, `morphology`, `source`, and on
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
- Esperanto-alphabetical sort order
  (a b c ĉ d e f g ĝ h ĥ i j ĵ k l m n o p r s ŝ t u ŭ v z).
- Headwords are unique with eight known exceptions — *dio, julia, kristo,
  mario, marto, mesio, pasko, pentekosto* — where the ReVo merge produced both
  a common noun and a proper noun under one spelling. They are tracked as a
  bead rather than silently deduplicated, because picking one loses a real
  sense. Any other duplicate is a defect.

## Outstanding

Done since this was first written: the Official Additions I–X are in, by way
of ReVo's `<ofc>` tags rather than the Akademio's broken endpoint, and the
extended vocabulary is in from ReVo and the corpus.

1. **POS review pass.** A minority of UV roots carry a default-noun POS
   despite a verbal or adjectival primary sense — a consequence of the
   inference heuristic above, and a data problem rather than a code one.
2. **`examples` field** drawn from the corpus, so an entry can show usage as
   well as a gloss. The citations on corpus-mined entries are the start of
   this; the lexicographic layers have none.
3. **Baza Radikaro Oficiala (BRO)** groups, for frequency banding.
4. **Cross-links to `GRAMMAR/`**, so an entry for an affix or a grammatical
   word points at the section explaining it.


