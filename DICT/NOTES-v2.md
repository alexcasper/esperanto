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

## Batch 3 (esp-ytn) — 500 reviewed, 484 promoted

`DICT/review/v2-batch3-{a,b}.tsv`, sources 11–8 (median 9).

- **484 lemma** (201 noun, 176 verb, 82 adj, 24 adv, 1 interj — *oho*).
- **16 rejected**: English/French/German (*online*, *google*, *gave*,
  *hitherto*, *footnote*, *actio*, *dictionnaire*, *bei*, *wo*), OCR
  (*iiia*, *oo*, *gia* for *ĝia*), *lanti* (author name), *absorbita*
  (participle), and two `uncertain`: *rizervi* (variant spelling in one
  repeated copyright line) and *realporti* (unclear compound).

**Segmentation rules added** after reading all 484 splits:

- numerals are never segmented (*dekoka* is *dek+ok*, not *de+kok*);
- a stem that is a compound of two radikoj (directly or via linking *-o-*)
  is left unsplit when the affix reading needs a rare prefix or *-op-*
  (*bonorde* = *bon+ord*, not *bo+nord*; *montopinto*, not *mont+op+int*).
  Participles do not trigger it — short roots make false compounds of
  them (*verkanto* is *verk+ant*, not *ver+kant*);
- *ig*/*iĝ* are never roots (*neforigebla*);
- overrides: `SPLIT_OVERRIDE` *sentemeco* = *sent+em+ec*; `NO_SPLIT`
  *familiara/familiare*, *vizaĵo* (roots missing from the stock).

`--resegment v2-` changed exactly those 8 entries. Root productivity turned
out to be a weak signal — ReVo records few derivatives per root (*sent-*: 2
entries) — so the explicit rules above carry more weight than the
tie-break.

Totals after batch 3: **1460** v2 entries, **1289** segmented and linked to
GRAMMAR §2; dictionary **26126**; queue **2129** (415 new stems/compounds,
1714 derivations).

## Batch 4 (esp-e26) — 500 reviewed, 485 promoted

`DICT/review/v2-batch4-{a,b}.tsv`, sources 8–6.

- **485 lemma** (216 noun, 163 verb, 83 adj, 22 adv, 1 interj — *haha*).
- **15 rejected**: names (*pierre*, *genova*, *evo*, *victoria*, *aba*),
  English/German/French (*came*, *seine*, *ohne*, *auxiliaire*, *kai*), OCR
  (*uzkondjĉo*, *ga* mojibake, *ei* fragment), and two `uncertain`
  (*opulo*; *leto*, whose only citation is truncated).
- **Segmentation**: of 485 splits, ~470 read correctly. The misses were all
  loanword roots absent from the stock whose tails look like affixes
  (*bari+er*, *de+monstr*, *dil+et+ant*, *pir+at*, *rut+in*,
  *kam+ar+ad+ec*), plus *for+um* for *forumo*. Rule tightened: an affix
  morpheme may serve as root only after *mal-*/*ne-* (*malebla*) or bare
  (*arego*); the rest are `NO_SPLIT` / `SPLIT_OVERRIDE` entries.
  `--resegment v2-` changed exactly those 9.

Totals after batch 4: **1945** v2 entries, **1665** segmented and linked;
dictionary **26611**; queue **1595**, all at 3–6 sources (109 at 6, 403 at
5, 524 at 4, 559 at 3).

**The loanword-root gap** is the remaining systematic weakness: the stock
holds only UV and ReVo radikoj, so a corpus loanword missing from both
(*bariero*, *pirato*, *rutino*) can be mis-split if its ending resembles an
affix. Batch 5+ reviewers should read the split list as carefully as the
glosses; a structural fix would add promoted unsplit nouns as roots of
last resort.

## esp-2sh — roots of last resort from reviewed entries

`esperanto.root_stock(mined_roots=True, no_split=NO_SPLIT)` (used by
`promote_lemmas`) adds, at rank 4, the stem of every corpus-mined entry that
is stored unsplit **and** either has no affix reading at all or is a reviewer
`NO_SPLIT`. 988 stems join: loanwords (*fjord-*, *monark-*, *socialism-*,
*barier-*, *pirat-*, *rutin-*) and opaque compounds (*grenkamp-*,
*skribtabl-*). Transparent derivations stored unsplit by the earliest layer
are deliberately excluded — *virin-* would otherwise turn *virineto* into
*virin+et*. Effect: 0 existing v2 entries change; future derivations split
on the loanword (*barierego* = *barier+eg*, *forumano* = *forum+an*,
*monarkino* = *monark+in*), where before they would have needed overrides.

## Batch 5 (esp-eb7) — 500 reviewed, 483 promoted

`DICT/review/v2-batch5-{a,b}.tsv`, sources 6–5 — the first batch promoted
with esp-2sh's roots of last resort.

- **483 lemma** (217 noun, 142 verb, 89 adj, 34 adv, 1 interj — *hola*).
- **17 rejected**: bilingual front matter and English/French/German
  (*texte*, *wrote*, *directio*, *active*, *desiroi*, *ihre*, *notre*,
  *neue*, *allgemeine*, *histoire*, *mise*, *ethnologue*), fragments (*sti*,
  *fo*), names (*algeria*, *ŝo* for Shaw), and *tino* `uncertain`.
  Rejection rate 3.4% vs 2.2–3.2% in batches 1–4, as expected at thinner
  evidence.
- **Segmentation**: 4 misreadings out of 483. Two were numeral compounds read
  through the fractional *-on-* (*dumonata* as *dum+on+at* for *du+monat*;
  *unutoneco* as *unut+on+ec*). New rule: a split that uses *-on-* on a stem
  that is numeral + radiko (+ suffixes) is left unsplit. It is scoped to
  *-on-* because short numerals otherwise eat real roots (*dub+ind* is not
  *du+bind*, *mild+ec* not *mil+dec*). *platano* and *ŝovinista* are
  `NO_SPLIT`. `--resegment v2-` changed exactly those 4.

Totals after batch 5: **2428** v2 entries, **2061** segmented and linked;
dictionary **27094**; queue **1088** (13 at 5 sources, 518 at 4, 557 at 3).

## esp-58p — the earlier corpus-mined layer, refreshed losslessly

The 2216 pre-v2 entries are refreshed in place, never rebuilt:

- **Attestation by corpus scan** (`tools/attest_scan.py`, `promote_lemmas
  --refresh-attestation`): occurrences and distinct sources of each word's
  regular inflected forms, over the miner's own file list — independent of
  miner keys, which is what orphaned the ledger verdicts (below). Applied to
  **all** 4644 corpus-mined entries for one method: validated on the v2
  entries first, where it agrees with the miner within ±1 source for 1308 of
  2428 and otherwise runs *higher* — the miner drops a form seen once in a
  shard (`--min-count 2` is per shard), so its counts understate breadth.
  30 counts fell, each by one source: forms outside the regular paradigm
  (elided *amaset'*) that the miner had credited. Entries attested in 3+
  sources: 4020 → 4462; in 6+: 2051 → 4235. Top: *malgranda*, 219 sources.
- **Segmentation** (`--resegment shard-`; legacy ledger batches are named
  `shard-*-of-8`): 942 legacy entries split; all 942 read, 28 wrong (3%) —
  almost all Latinate loanwords with affix-looking edges (*al+bum*,
  *for+tun*, *pri+or*, *re+vu*, *sen+at*, *pi+an*, *de+fi+cit*), plus
  *ĉiujare* and *nevino* (*nev+in*, not *ne+vin*). 26 joined `NO_SPLIT`
  (where they also become roots of last resort, so *pianisto* = *pian+ist*,
  *senatano* = *senat+an* now split correctly), one `SPLIT_OVERRIDE`.
  916 entries got morphology and `grammar_refs`; no v2 split changed.
- **`derived` redefined** (`--rederive`): true exactly when `morphology` has
  a self-validating affix segmentation. The old test (peel affixes against
  every root in the file) had drifted once ReVo's roots arrived: it flagged
  *bariero*, *pirato* as derived and missed derivations on roots it lacked.
  520 flags changed (393 legacy, 127 v2); derived = segmented = 2977.
- **`--rebuild` is now lossless**: entries whose verdict no longer attaches
  to a mined key are kept as they were (dry run: 4028 rebuilt + 616 kept =
  4644, none dropped). It was not run — the refresh flags do the job without
  re-drawing citations.

Only `attestation`, `morphology`, `derived` and `grammar_refs` changed, only
on corpus-mined entries; glosses and citations untouched; nothing added or
lost.

## esp-r14 — the miner's per-shard noise floor

`mine_lemmas.py` dropped any lemma seen once within a shard (`--min-count 2`
per shard), so a word occurring once in each of several shards lost those
sources, and the 3-source bar under-admitted. The per-shard default is now 1;
the floor moved to the corpus-wide total (`reconcile_lemmas.py --min-count`,
default 2; reviewed lemmas are always kept, so no verdict is orphaned by it).

Validation against the independent scan (`tools/attest_scan.py`) on the
queued lemmas: miner and scan agree exactly on sources for **2931 of 3083
(95%)**, up from 228 (7%) before the fix. Effect on the 302-source corpus:
queue **1088 → 3083** (1981 newly admitted, mostly derivations seen once
per shard: *kunludanto*, *plumujo*, *bogepatro*, *fulmobato*); thin
10079 → 13735 as more singletons are now visible at all. Some German/French
tokens also clear the bar (*beide*, *chose*, *wisse*) — the `english` filter
covers English only, so reviewers reject these by hand. Shards 102 → 154 MB,
candidates 58 → 73 MB (both gitignored).

**Batch 6 waits on the Vikipedio corpus** (glm `f44b4f5`, 42,595 per-article
`wp-*` sources: 302 → 42,897). At that scale source counts and the 3-source
bar change meaning, so the queue must be re-mined first; batch 6 on the
302-source queue would rank on numbers about to be replaced.

## Vikipedio scale rehearsal (read-only, 2026-10-07)

Run in a scratch root against `esp_glm/CORPUS` (42,897 sources incl. 42,595
`wp-*` articles) with this branch's tools and DICT files; nothing written to
either worktree.

| Step | Time | Peak RSS | Output |
|---|---:|---:|---:|
| mine, 8 shards (5.4k files each) | 67 s | 0.47 GB / worker | shards 1.2 GB |
| reconcile | 34 s | **5.1 GB** | candidates 704 MB |

354,260 candidate lemmas; **queue 47,279** (vs 3,083 on 302 sources) —
1,482 at 100+ sources, 27,338 at 3–9. 81% (38,490) of queued lemmas are
cited only from `wp-*` sources; only 8,789 have even one non-Wikipedia
citation (a lower bound — citations are capped at 5).

What this means for batch 6:

- **The 3-source bar no longer means anything** once 42k single-article
  sources exist; a word in three stub articles clears it. The bar needs a
  register-aware rule (follow-up bead).
- **The top of the queue is real modern vocabulary the dictionary lacks**:
  *populacio*, *habitato*, *taksonomio*, *ekosistemo*, *retejo*,
  *referendumo*, *flughaveno*, *subspecio*, *kunteksto*. High value.
- **New noise classes**: names that do occur lower-case in Wikipedia
  reference lists (*anna*, *otto*, *della*), so the never-lower-case name
  rule misses them; participles of verbs not yet in the dictionary
  (*establita* beside *establi*) pass the participle filter.
- **Reconcile memory (5.1 GB)** is the scaling limit: it holds every merged
  record in memory. Fine on dawn, but worth streaming before the corpus grows
  again.

## esp-nuk — register-aware evidence bar (Vikipedio scale)

With 42,595 of 42,899 sources being single `wp-*` articles, `gap_report.py`
now splits each candidate's sources by register and queues it in the first
tier it meets (all tiers also need >= 5 occurrences):

| Tier | Rule | Queued |
|---|---|---:|
| broad | >= 3 non-Wikipedia sources (the pre-Vikipedio bar, same meaning) | 4,839 |
| mixed | 1–2 non-Wikipedia + >= 10 wp articles | 3,870 |
| wp-only | no other source, >= 50 wp articles | 1,530 |

Queue **47,279 → 10,239**, ordered by tier, then non-Wikipedia sources, then
wp articles. Queue citations prefer non-Wikipedia lines. New buckets:

- **foreign** (1,984): a letter outside the alphabet (q w x y) or a short
  Romance/German function-word list (*della*, *beide*, *chose*).
- **participle** now also catches participles of verbs that are themselves
  candidates (*establita* beside *establi*): +862.
- **capitalised** (3,254): under a quarter of occurrences lower-case
  (`reconcile_lemmas.py` now keeps the summed `lower` count). Catches names
  that wiki reference lists lower-case now and then (*anna* 0.7%, *otto*
  0.2%) — but also country/place names (*afganio*, *arabio*), which ReVo
  holds as headwords. They are held out of the queue, not rejected, pending
  a names policy.

Left to reviewers: Latin *-ctio* forms (*editio*, *translatio*) — a `-tio`
rule would hit *demokratio*, *dinastio*, *patio*; English tokens with an
Esperanto-looking inflection (*make*/*maken*). Reconcile's 5.1 GB peak is
filed separately.

## Ledger keys orphaned by promotion (input to esp-58p)

Once a corpus-mined entry is promoted its `root` (the whole word stem) is in
the vocabulary, so its inflected forms fold under the stem (*rompiĝis* →
*rompiĝ*) and the ledger verdict keyed *rompiĝi* no longer attaches: 78 of
2708 lemma verdicts were unmatched after batch 1, 192 of 3197 after batch 2. All but *eliru* (now filed
as *eliri*) and the stopword *ks* are already in the dictionary, so nothing
is lost today — but `promote_lemmas --rebuild` would silently drop all of
them. Resolved in esp-58p: `--rebuild` now keeps such entries, and the
refresh path avoids miner keys altogether.

## Known limitations / follow-ups

- **Earlier corpus-mined layer**: done in esp-58p (above).
- **Root/citation key collision** in the miner: a token analysed as a known
  root (*kompanioj* → root *kompani*) and an unknown token whose citation
  form is the same string (*kompanos* → *kompani*) share one record. Rare;
  *kompani* was rejected rather than promoted under a wrong headword.
- **UV POS heuristic**: *povi* is filed as the adjective *pova* (UV root
  *pov'*); the participle filter has to check roots, not words, because of it.
- **Prepositional prefixes**: done in esp-4qi (above).
- **Next batches**: after esp-r14 the 302-source queue holds 3083; it will be
  re-mined once the Vikipedio corpus reaches this branch (see esp-r14 above). The *thin* bucket (11055) needs a different bar than
  source count — single-author technical vocabulary is real but unattested
  elsewhere.

## Queue rebuild 2026-10-07 (glm pane, post-Vikipedio merge)

Re-mined with the wp- (Vikipedio 20261001, 42,595 articles) sources included
— the gap queue was previously built from the 302-source pre-wp corpus, so
esp-4g8's corpus never reached the candidate miner.

- Corpus now 42,868 normalised sources in CORPUS/ (302 literary + 42,566 wp).
- Mined lemmas: 354,264 (candidates.jsonl).
- Gap queue (>=3 sources, >=5 occurrences, all gap_report buckets applied):
  **47,283 candidates** — 33,583 at >=6 sources, 6,877 at 5, 4,040 at 4,
  2,783 at 3. Was 3,395 pre-wp: the Vikipedio corpus multiplies the
  attestable modern vocabulary by ~14x.
- Top of queue is exactly the expected profile (populacio, habitato,
  taksonomio, arkitekturo, demokratio…) — encyclopedic modern Esperanto
  missing from UV/ReVo/O'Connor layers.
- esp-r14's singleton fix is included in this run (per-shard singletons
  kept, corpus-wide noise floor instead).
- esp-73s (batch 6, "~500 of gap queue (5-4 sources)") was scoped against
  the old queue; recommend re-scoping batches by source bands off this
  queue instead.
