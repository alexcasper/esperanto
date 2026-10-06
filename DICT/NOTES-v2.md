# DICT v2 — corpus-attested vocabulary beyond the Universala Vortaro (esp-rac)

Gap analysis of the corpus against the dictionary, and the first review batch
it produced. Reproduce every number here with:

```sh
rm -f DICT/shards/shard-*
for i in 1 2 3 4 5 6 7 8; do python3 tools/mine_lemmas.py --shard $i/8 --ledger; done
python3 tools/reconcile_lemmas.py --shards 8
python3 tools/gap_report.py
```

## Baseline (2026-10-06)

- **Dictionary**: 24666 entries across all layers — Fundamento/UV-1905 2911,
  ReVo 6038 + ReVo/UV-* 5764 + ReVo/OA-1…10 3513, O'Connor-1906 4224,
  corpus-mined 2216.
- **Corpus**: 302 normalised sources in `CORPUS/` (143 pg, 79 wsrc, 57 ia,
  23 wsdump). Mined: 273, after the existing exclusions in
  `tools/mine_lemmas.py` (English/French prose about Esperanto, the
  multilingual Fundamento tables, OCR-poor archive.org scans). QUARANTINE/ is
  never read.

## Gap — where 51349 mined lemmas stand

`tools/gap_report.py` sorts every candidate into exactly one bucket
(figures after batch 1 was promoted):

| Bucket | Lemmas | Meaning |
|---|---:|---|
| in-dict | 11670 | citation form already an entry in some layer |
| reviewed | 611 | verdict in `verdicts.jsonl` but not a dictionary entry (names, foreign, fragments, …) |
| closed-class | 17544 | miner kinds `known` (inflected forms of entries), `name`, `fragment` |
| no-ending | 2660 | no open-class ending: English *that/which*, URL pieces |
| english | 338 | every surface form an English word (O'Connor headwords + function words) |
| participle | 4076 | -anta/-inta/-ita/-ante… on a verb we hold — inflection, not a headword |
| thin | 11055 | under the evidence bar: < 3 sources or < 5 occurrences |
| **queue** | **3395** | real gap: 861 new stems/compounds, 2534 derivations |

So the corpus supports roughly **3.4k further headwords** at a 3-source bar
(3.9k before batch 1), against 24.7k held. The queue's source breadth:
714 lemmas in 10+ sources, 2681 in 3–9.

What the gap is made of, from reading the top of the queue:

- **Productive derivation** dominates (75%): aspectual *ek-* (*ekridi*,
  *ekbrili*), *-iĝ-/-ig-* voice pairs (*rompiĝi*, *venigi*), *-ad-*
  continuatives (*kuradi*, *kriado*), diminutives/augmentatives, *-ul-*
  persons. ReVo lists the roots but not these everyday derivatives.
- **Prepositional and adverbial compounds** the affix model does not peel:
  *enpaŝi*, *kuniri*, *transsalti*, *suprenrigardi*, *pliboniĝi*,
  *surgenue*, *lastafoje*.
- **Root compounds**: *homamaso*, *batalkampo*, *poŝtmarko*, *sunbrilo*,
  *vivrimedo*, *mezepoka*.
- **A modern layer** from the eowiki sources: *komento*, *uzkondiĉo*,
  *paĝkomenco*.

## Batch 1 — 500 reviewed, 487 promoted

The top 500 of the queue by source breadth (≥ 18 sources each) was read
with its citations and judged in `DICT/review/v2-batch1-{a,b}.tsv`
(`lemma ⇥ verdict ⇥ gloss ⇥ note`), applied to the ledger by
`tools/apply_review.py`, and promoted by `tools/promote_lemmas.py`.

- **487 lemma** → new entries: 245 verb, 178 noun, 40 adj, 24 adv; 434 flagged
  `derived`. Attestation: every entry is in ≥ 18 independent sources
  (median 26, max 96), with up to three corpus citations. Source tag
  `corpus-mined`, as for the earlier layer; the ledger's `reviewed_in`
  names the batch.
- **13 rejected**: proper nouns (*altona*, *antonio*, *goethe*, *jakobo*),
  English (*take*, *pleasure*, *thi* = *this*), German (*strasse*), a site
  name (*wikipedia*), OCR (*uni* for *unu*), fragments (*dro* from D-ro,
  *kompani*, see below), and one uncertain periodical footer (*laŭvaloro*).
- **Morphology**: 416 of the 487 carry a real affix segmentation
  (`prefixes` / `stem` / `suffixes`, glossed as the UV layer glosses them);
  the remaining 71 are compounds or prepositional prefixes and keep plain
  stem + ending, as UV entries do when segmentation does not self-validate.
- **Grammar links**: the 416 segmented entries carry `grammar_refs` to
  GRAMMAR §2 (affix inventory), and those with a participle suffix
  (*kaptito*, *tradukinto*) also to the §2 participles row.

Nothing in the existing 24666 entries changed (verified line-by-line).

## Pipeline fixes made on the way

1. **Attestation breadth was capped at 5.** `sources` was counted from the
   picked citations (max 5), so `attestation.sources` could never exceed 5.
   The miner now records every file a lemma occurs in and the reducer unions
   them. Batch-1 entries carry the true count. The 2216 earlier
   corpus-mined entries still carry capped counts — see follow-ups.
2. **Ledger notes grew geometrically.** `mine_lemmas --ledger` restored a
   note into all 8 shards and `reconcile_lemmas` joined all 8 copies, every
   cycle; the *lo* note had ~200 copies and the ledger was 8.4 MB. Notes
   are now de-duplicated on reduce and on apply; ledger is 0.7 MB with no
   verdict changed.
3. **`-il-` (instrument) was missing** from `esperanto.SUFFIX`, so every
   *-ilo* word on a known root (*apogilo*) was mis-filed as unknown.
4. **Segmentation needs a clean root stock.** `load_vocabulary()` roots are
   unusable for it: O'Connor and corpus-mined entries record the whole word
   stem as `root`, and the UV build over-splits some roots (*ripet* →
   *rip+et*). `esperanto.root_stock()` ranks only authoritative radikoj
   (UV root and stem, then ReVo UV-official, OA, other ReVo, plus
   closed-class words of 3+ letters), and `esperanto.segment()` prefers
   fewest affixes, then fewest prefixes, then the better-ranked root — which
   is what turns *reĝino* into *reĝ+in* rather than *re+ĝin* ('re-gin') and
   *filineto* into *fil+in+et* rather than *fi+lin+et*. One reviewer
   override (`NO_SPLIT`: *ekspiri* is not *ek+spiri*).

## esp-4qi — prepositional prefixes in the affix model

`esperanto.PREP_PREFIX` (al, antaŭ, apud, ĉe, ĉirkaŭ, de, ekster, en, inter,
kontraŭ, kun, post, preter, pri, sen, sub, super, sur, tra, trans, pli,
supren, malsupren) now joins `PREFIX` in `peel_affixes` and `segment`.
Measured on the same dictionary, old vs new model:

| Bucket | before | after |
|---|---:|---:|
| queue | 3289 (843 unknown) | 3255 (548 unknown) |
| participle | 4047 | 4192 |
| thin | 10959 | 10419 |
| closed-class (names) | 5587 | 6414 |

- 1367 lemmas moved unknown → derived (*kunlabori*, *subiro*, *sencela*).
- 34 queued participle forms (*kunportante*, *enŝlosita*, *surportanta*)
  are now recognised as inflections and leave the queue; 42 real words join
  it (*kunlaboro*, *antaŭtagmeze*, *suboficiro*, *kunteksto*).
- Side effect caught: always-capitalised names parsed as *al-/de-* words
  (*Alonzo*, *Demosteno*, *Priamo*). The name rule (never lower-case) now
  applies to derived kinds too, and is decided in the reducer from summed
  casing across shards rather than by whichever shard was read first. Cost:
  a few always-capitalised derivations (*italiano*, *londonano*,
  *urbestrejo*) now bucket as names — demonyms want a dedicated pass.
- Segmentation of the batch-1 entries that were stem-only would now resolve
  *en+paŝ*, *kun+ir*, *sen+cel*, *ne+pri+skrib+ebl*, *trans+skrib+int*;
  `segment()` also refuses to split a stem that is itself a radiko
  (*demand-* is not *de+mand-*) and refuses an affix as root after a
  preposition (*eniĝi* is not *en + iĝ-*). Existing entries are not
  rewritten here — that is the esp-58p re-promotion.

## Batch 2 (esp-xge) — 500 reviewed, 489 promoted

Next 500 of the post-esp-4qi queue (36–11 sources) in
`DICT/review/v2-batch2-{a,b}.tsv`.

- **489 lemma** → new entries (209 noun, 197 verb, 60 adj, 23 adv; 454
  `derived`), attested in 11–36 sources (median 14).
- **11 rejected**: English (*name*, *knowledge*, *accessible*), French book
  titles (*vocabulaire*, *commentaire*, *grammaire*, *internationale*),
  *alle*, Maltese *strada* in an address, *povinti* (participle misfiled as a
  verb), and *treti* left `uncertain` (*tretis subpiede* — not in any
  reference layer).
- **888 of the 976** v2 entries (batches 1+2) now carry affix segmentation
  and `grammar_refs` to GRAMMAR §2.

**Segmentation tie-break revised.** Batch 2 exposed that "fewest prefixes"
was as arbitrary as its opposite: it produced *rel* ('rail') + *eg* for
*relegi*, *rest+ar+iĝ* for *restariĝi*, and *nek+on+at+ul* for
*nekonatulo*; flipping it produced *for+teg* ('cover') for *fortege*.
`segment()` now breaks ties by: fewest affixes → fewest *rare* prefixes
(fi-, bo-, eks-, mis-, pra-) → root authority → **root productivity**
(entries built on the root, any layer). Conjunctions and particles are out
of the root stock. Two explicit reviewer overrides remain
(`SPLIT_OVERRIDE`: *restarigi/restariĝi* = *re+star+…*; `NO_SPLIT`:
*ekspiri*, *ŝovinismo*). `promote_lemmas --resegment v2-` re-applied the
segmenter to the v2 entries only: 48 changed, morphology and grammar_refs
only — 43 newly segmented by esp-4qi's prepositional prefixes (*en+paŝ*,
*sen+cel*, *ne+pri+skrib+ebl*), 5 corrected (*diskonigi* = *dis+kon+ig*, not
*disk+on+ig*; *relegi*; *restarigi/restariĝi*; *nekonatulo*; *malebligi*),
*ŝovinismo* unsplit.

Queue after batch 2: **2677** (494 new stems/compounds, 2183 derivations);
only 178 remain in 10+ sources, so batch 3 reaches into the 5–9-source band.

## Ledger keys orphaned by promotion (input to esp-58p)

Once a corpus-mined entry is promoted its `root` (the whole word stem) is in
the vocabulary, so its inflected forms fold under the stem (*rompiĝis* →
*rompiĝ*) and the ledger verdict keyed *rompiĝi* no longer attaches: 78 of
2708 lemma verdicts were unmatched after batch 1, 192 of 3197 after batch 2. All but *eliru* (now filed
as *eliri*) and the stopword *ks* are already in the dictionary, so nothing
is lost today — but `promote_lemmas --rebuild` would silently drop all of
them. esp-58p must resolve this before any rebuild.

## Known limitations / follow-ups

- **Earlier corpus-mined layer**: re-promoting it with `--rebuild` would fix
  its capped `attestation.sources` and give it segmentation, but is not
  lossless today (3 entries — *ĉiuspeca*, *rekompenso*, *senpetala* — are no
  longer mined under the same key, and 222 `derived` flags flip because the
  vocabulary now includes ReVo). Needs a deliberate pass, not a side effect.
- **Root/citation key collision** in the miner: a token analysed as a known
  root (*kompanioj* → root *kompani*) and an unknown token whose citation
  form is the same string (*kompanos* → *kompani*) share one record. Rare;
  *kompani* was rejected rather than promoted under a wrong headword.
- **UV POS heuristic**: *povi* is filed as the adjective *pova* (UV root
  *pov'*); the participle filter has to check roots, not words, because of it.
- **Prepositional prefixes**: done in esp-4qi (above).
- **Next batches**: 2677 lemmas remain queued after batch 2; batch 3 takes
  the 10–6-source band. The *thin* bucket (11055) needs a different bar than
  source count — single-author technical vocabulary is real but unattested
  elsewhere.
