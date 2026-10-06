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
- **Prepositional prefixes** (*en-*, *kun-*, *trans-*, *sur-*, *pli-*) are not
  in the affix inventory, so *kunportante* still reaches the queue and
  *enpaŝi* stays unsegmented.
- **Next batches**: 3395 lemmas remain queued; batch 2 should take the next
  ~500 (17–10 sources). The *thin* bucket (11055) needs a different bar than
  source count — single-author technical vocabulary is real but unattested
  elsewhere.
