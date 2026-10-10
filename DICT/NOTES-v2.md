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

## Batch 6 (esp-73s) — 500 reviewed, 476 promoted

`DICT/review/v2-batch6-{a,b}.tsv`: the top 500 of the esp-nuk queue, all in
the **broad** tier (6–8 non-Wikipedia sources, 0–1,657 wp articles; median
attestation 30 sources by scan). The first batch ranked on the Vikipedio
corpus.

- **476 lemma** (227 noun, 151 verb, 78 adj, 20 adv). Mostly derivations of
  held roots (*kunludanto*, *plumujo*, *senfenestra*, *fulmobato*) and
  modern vocabulary the old layers lacked (*kriterio*, *ministerio*,
  *lifto*, *docento*, *kaoso*, *komploto*, *nordorienta*).
- **24 rejected** (4.8%): 19 foreign — English Latinate nouns split at a
  line break or before *-n* (*translatio*, *editio*, *conclusio*, *sectio*,
  *intentio*, *soo*←soon, *make*, *she*, *else*), French *traductio*, Ido
  *esi*, Spanish *una*, *amigi*←amigos, *mea*; names *diĵona*, *dene* (Ivy
  Dene); *eo* `ocr-artifact` (OCR of *ĉe*, and URL language codes); *orgi*
  `fragment` (key collision, *orgio* held); *montrigi* `uncertain` (wp use
  reads as a typo for *montriĝi*). Higher than batch 5's 3.4% because the
  q/w/x/y filter cannot see English words spelt with Esperanto letters.
- **Segmentation**: 5 of 379 splits wrong (1.3%) — *ludoni* read as
  *lud+on* (compound *lu+doni*), *ĝisatendi* as *ĝis+at+end* (*ĝis-* not
  modelled), *favorito*, *bramano* (loanwords) → `NO_SPLIT`; *reformisto*
  → override *reform+ist* (not *re+form+ist*). `--resegment v2-` changed
  exactly those 5.
- **Citations**: 79 of the 476 are cited only from `wp-*` lines although
  each has 6+ non-Wikipedia sources — promote picks citations from the
  miner record without esp-nuk's register preference (follow-up bead).

Totals after batch 6: **2904** v2 entries; corpus-mined **5120**, 3352
segmented and linked to §2; dictionary **27576**; queue **9739** (broad
4339, mixed 3870, wp-only 1530).

## esp-0mu — literary citations first; one attestation shape

- **Citations**: `reconcile_lemmas.pick_citations` now orders non-Wikipedia
  sources first (round-robin alone filled its five slots with `wp-*` lines
  once 42.6k article sources existed), and `promote_lemmas.choose_citations`
  takes non-Wikipedia lines first, Wikipedia only for slots literature
  cannot fill. New `--recite BATCH_PREFIX` re-draws citations, changing an
  entry only when it gains literary lines. `--recite v2-batch6`: 386 of 476
  entries changed (citations only); the 79 cited solely from Wikipedia are
  now all literary — all 476 batch-6 entries carry three literary
  citations. Batches 1–5 came from the pre-Vikipedio corpus: 0 changes.
- **Attestation**: `tools/attest_scan.py` now returns `sources_lit` /
  `sources_wiki` beside `count`/`sources`, the same split the web lane's
  `mine_concordance.py` writes (a6f69ec). Spot check on 7 entries: identical
  on 6, *malgranda* within 4 of 10,665 sources. Both writers of
  `attestation` now produce the same shape and, to that margin, the same
  numbers.

## Batch 7 (esp-weg) — 500 reviewed, 478 promoted

`DICT/review/v2-batch7-{a,b}.tsv`: queue positions 1–500 after batch 6,
broad tier (5–6 non-Wikipedia sources). The first batch promoted with
esp-0mu's literary-first citations.

- **491 lemma**, **478 promoted** (254 noun, 136 verb, 66 adj, 22 adv):
  derivations (*almozpetanto*, *kunloĝado*, *sinregado*, *devosento*) and
  modern vocabulary (*kunteksto*, *arkitekturo*, *demokratio*, *aviadilo*,
  *mekanismo*, *planlingvo*, *skribsistemo*, *kirurgo*). 475 of 478 cite
  only literary sources; all carry `sources_lit`/`sources_wiki`.
- **9 rejected** (1.8%): foreign *natio*, *schreibe*, *possessio*,
  *apprendre*, *andere*; OCR *vizago* (vizaĝo), *ae*, *oe* (ĉe); *kambi*
  `fragment` (key collision, *kambio* held).
- **13 accepted but not promoted, by design**: *misuzo*, *oferto*,
  *admiradi*, *sensone*, *surstrate*, *mekanike*, *reorganizo*, *plendado*,
  *divenadi*, *insultadi*, *interŝanĝadi*, *malbonfarti*, *superforti* —
  each another ending on a stem batch 6 promoted (*misuzi*, *oferti*,
  *admirado*…). Re-mined, their forms fold into the held entry (one entry
  per stem). They reached the queue because it was built from candidates
  mined *before* batch 6 promoted (esp-0mu re-ran only reconcile). Lesson:
  re-mine after every promotion before ranking the next batch.
- **Segmentation**: 10 of 369 splits wrong (2.7%) — loanwords *amuleto*
  (am+ul+et), *humida* (hum+id), *mekanismo* (mek+an+ism), *deklini*
  (de+klin) and the compound *salminejo* → `NO_SPLIT`; overrides
  *fiakristo* (fiakr+ist), *revanto* (rev+ant), *reformemulo*
  (reform+em+ul), *trabaro* (trab+ar), *prizorganto* (pri+zorg+ant).
  *deklin-* as root of last resort then also fixed batch-1's *dekliniĝi*
  (de+klin+iĝ → deklin+iĝ), the one existing entry changed.

Totals after batch 7: **3382** v2 entries; corpus-mined **5598**, 3716
segmented and linked; dictionary **28054**; queue **9166** (broad 3799,
mixed 3842, wp-only 1525).

## Batch 8 (esp-gwn) — 500 reviewed, 485 promoted

`DICT/review/v2-batch8-{a,b}.tsv`: queue positions 1–500 after a fresh
re-mine (the batch-7 lesson): the re-mine alone dropped the queue 9166 →
9087 as batch-7 stems absorbed their sibling endings before review, and
this time every accepted lemma was promoted.

- **485 lemma** (231 noun, 153 verb, 76 adj, 24 adv, 1 interj —
  *hahaha*): mostly derivations (*kuncivitano*, *bogepatro*, *urbestrejo*,
  *fingropinto*, *poŝtranĉilo*) plus a few loans (*fotelo*, *dogo*,
  *melaso*, *rezedo*, *numido*, *oero*). All 485 cite literary sources only.
- **15 rejected** (3.0%): 11 foreign (German *ganze*, *gesehe*; French
  *toute*, *mauvai*; English *bega*, *eleve*, *recognise*, *postage*, and
  grammar-lesson Latinisms *distributio*, *repetitio*, *augmentative*);
  OCR *regardi* (rigardi); *propa* `fragment` (an invented form in a
  metalinguistic list); *baptanino*, *tempofine* `uncertain`.
- **Segmentation**: 5 of 401 splits wrong (1.2%) — compounds *aliamaniere*,
  *nunjara*, *multejara* → `NO_SPLIT`; overrides *nesentema* (ne+sent+em,
  not ne+sen+tem) and *ideto* (ide+et).
- `--recite v2-` re-drew one batch-7 entry (*hindeŭropa*) that the re-mine
  gave a literary line.

Totals after batch 8: **3867** v2 entries; corpus-mined **6083**, 4114
segmented and linked; dictionary **28539**; queue **8587** (broad 3264,
mixed 3808, wp-only 1515).

## Batch 9 (esp-3ke) — 500 reviewed, 473 promoted

`DICT/review/v2-batch9-{a,b}.tsv`, re-mined first: the end of the 5-source
band (5+0 wp) and the top of the 4-source band, where Wikipedia breadth
returns (*arkitekto* 4+1136, *retejo* 4+973, *ĝenro*, *platformo*,
*eksperto*, *licenco*, *spontana*).

- **473 lemma** (256 noun, 109 verb, 85 adj, 23 adv) — all promoted.
  463 cite literary sources only; *retejo* (website) only Wikipedia, its
  four non-Wikipedia occurrences missing from the miner's citation sample.
- **27 rejected** (5.4%): 20 foreign — German (*erste*, *esse*, *heute*,
  *finde*, *mache*, *kleine*, *ende*), Italian/Spanish (*lezioni*, *bella*,
  *lengua*, *italiano* from a dictionary title), French *nationale*,
  English (*pleasurable*, *advisable*, *desirable*, *learnable*,
  *circulatio*, *archive*) and a reformed-Esperanto poem (*familje*,
  *homoze*); OCR *cielo*, *antai*; inflections *duonfermante* (-ante),
  *devinti* (devintus); `fragment` *despli*, *plimalpli* (*des pli*,
  *pli malpli* run together — promote's ending-based POS would have filed
  them as verbs); name *dara*. Rejections rise again at 4–5 sources, where
  bilingual grammar lessons supply most of the noise.
- **Segmentation**: 8 of 361 wrong (2.2%) — loanwords *eksperto*
  (ek+spert), *filipina*, *legiono*, *sardino*, *sibilo*, *solidara* and
  the numeral compound *dekunujara* (de+kun+uj+ar) → `NO_SPLIT`;
  *reformado* → reform+ad.

Totals after batch 9: **4340** v2 entries; corpus-mined **6556**, 4468
segmented and linked; dictionary **29012**; queue **8042** (broad 2733,
mixed 3795, wp-only 1514).

## Batch 10 (esp-htt) — 500 reviewed, 474 promoted

`DICT/review/v2-batch10-{a,b}.tsv`, re-mined first; broad tier at 4
non-Wikipedia sources (4+14 down to 4+2 wp).

- **474 lemma** (225 noun, 144 verb, 76 adj, 29 adv) — all promoted; 472
  cite literary sources only, none Wikipedia-only. Derivations dominate
  (*staciestro*, *sakfajfilo*, *fenestrokadro*, *respondkupono*,
  *luphundo*), with loans *menaĝerio*, *droŝko*, *skudo*, *ideografio*.
- **26 rejected** (5.2%): 22 foreign — German (*komme*, *lasse*, *einige*,
  *gebe*, *besondere*, *meiste*, *folge*, *sehe*), French (*foi*,
  *langage*, *bourse*, *solutio*), English (*thee*, *comprehensive*,
  *constructio*, *applicatio*, *documentatio*, *inclusive*, *guidance*),
  Polish *jede*, *matka*, Ido *linguo*; name *genevo*; `uncertain`
  *neanto*, *buno*, *neigi*.
- **Segmentation**: 5 of 376 wrong (1.3%) — compounds *aliafoje*,
  *vojerari* → `NO_SPLIT`; overrides *trabeto* (trab+et), *trafigi*
  (traf+ig), *malsuprengrimpi* (malsupren+grimp).
- `--recite v2-` gave batch-9's *pluvivi* a literary citation.

Totals after batch 10: **4814** v2 entries; corpus-mined **7030**, 4842
segmented and linked; dictionary **29486**; queue **7470** (broad 2207,
mixed 3761, wp-only 1502).

## Batch 11 (esp-n4i) — 500 reviewed, 484 promoted

`DICT/review/v2-batch11-{a,b}.tsv`, re-mined first (after syncing glm's
merge of batches 8–10): the tail of the 4-source band and the top of the
3-source band, where Wikipedia breadth returns (*surbaze* 3+2364,
*publikaĵo*, *vegetaĵaro*, *urbocentro*, *monarkio*, *hemisfero*,
*rasismo*, *radiostacio*).

- **484 lemma** (222 noun, 162 verb, 74 adj, 26 adv) — all promoted; 463
  literary-only, *partikulare* Wikipedia-only.
- **16 rejected** (3.2%): 9 foreign (*satisfactio*, *superbe*, *maitre*,
  *nehme*, *describe*, *schaffe*, Latin *combinatoria*, *magna*, *facto*);
  OCR/typo *ŝango*, *ŝangi* (ŝanĝ-), *riĉajo* (riĉaĵo); inflection
  *taksinti* (taksintus); `uncertain` *kvartolo*, *ekvidigi*, *sektone*.
- **Segmentation**: 7 of 383 wrong (1.8%) — loanwords *dispozicio*
  (dis+pozici), *fonemo* (fon+em), *karitato*, *sanitara*, *violeto* and
  *ĉef-* compounds *ĉefaltaro*, *ĉefloko* (read as ĉe+…) → `NO_SPLIT`.

Totals after batch 11: **5298** v2 entries; corpus-mined **7514**, 5218
segmented and linked; dictionary **29970**; queue **6937** (broad 1689,
mixed 3747, wp-only 1501).

## Batch 12 (esp-kw1) — 500 reviewed, 475 promoted

`DICT/review/v2-batch12-{a,b}.tsv`, re-mined first (after fast-forwarding
to glm's batch-11 merge): the 3-source band, 3+85 down to 3+12 wp.

- **475 lemma** (256 noun, 98 verb, 100 adj, 21 adv) — all promoted; 451
  literary-only, *dialektaro* Wikipedia-only.
- **25 rejected** (5.0%): 14 foreign — German *drei*, *gege(n)*,
  *morge(n)*, *unsere*; French *terre*, *guerre*, *reine*; Italian *capo*,
  *internazionale*; Latin *camera*, *omnia*; Polish *ulica*; Occidental
  *lingue*; English *relatio*. Names *Demas*, *Magenta*, *Koso*. OCR *tui*
  (tiu), *kontra* (kontraŭ), *larga* (larĝa), *loa*. `uncertain` *inici*,
  *diva*, *alero*, *illa*.
- **Segmentation**: 6 of 359 wrong (1.7%) — roots *dekoro*, *kampadi*,
  *dissolviĝo* and compound *turpinto* (tur+pint) → `NO_SPLIT`; overrides
  *patronado* (patron+ad), *reformema* (reform+em). The new `kampad` root
  re-split the older *kampadejo* (kamp+ad+ej → kampad+ej); `--recite`
  gave batch-11's *kompano* a literary citation.

Totals after batch 12: **5773** v2 entries; corpus-mined **7989**, 5573
segmented and linked; dictionary **30445**; queue **6383** (broad 1173,
mixed 3715, wp-only 1495).

## Batch 13 (esp-598) — 500 reviewed, 473 promoted

`DICT/review/v2-batch13-{a,b}.tsv`, re-mined first (after fast-forwarding
to glm's batch-12 merge): the 3-source band with low Wikipedia backing
(3+12 down to 3+4 wp).

- **473 lemma** (247 noun, 106 verb, 86 adj, 34 adv) — all promoted; 456
  literary-only, 0 Wikipedia-only.
- **27 rejected** (5.4%): 22 foreign — French *raiso(n)*, *aura(it)*,
  *heure*, *vierge*, *masse*, *vivre*, *ainsi*, *autre*, *commerciale*;
  German *konnte*, *stehe(n)*, *gegang(en)*, *sollte*, *verschiedene*,
  *derselbe*; English *became*, *communicatio(n)*, *available*,
  *introductio(n)*, *chori*; Polish *jego*; Russian *vremja*. Names *Parla*,
  *Tiberias*. Fragment *dela*. `uncertain` *patio*, *diotima*.
- **Segmentation**: 5 of 370 wrong (1.4%) — roots *flakono*, *kanoto*,
  *maltano*, *ulano* and compound *propradecide* (propr+a+decid+e) →
  `NO_SPLIT`. Override *aliĝadi* (aliĝ+ad, not al+iĝad after *iĝadi* became
  a root). `--recite` gave literary citations to earlier *aprobado*,
  *misfortuno*, *varbiĝi*, *viktimiĝi*.

Totals after batch 13: **6246** v2 entries; corpus-mined **8462**, 5938
segmented and linked; dictionary **30918**; queue **5839** (broad 668,
mixed 3683, wp-only 1488).

## Batch 14 (esp-31c) — 500 reviewed, 477 promoted

`DICT/review/v2-batch14-{a,b}.tsv`, re-mined first (after fast-forwarding
to glm's batch-13 merge): the 3-source band at its thinnest Wikipedia
backing (3+4 down to 3+1 wp). Nearly all literary vocabulary
(*incensilo*, *heleboro*, *brokato*, *talaro*, *nargileo*, *poplito*).

- **477 lemma** (209 noun, 152 verb, 92 adj, 24 adv) — all promoted; 474
  literary-only, 0 Wikipedia-only.
- **23 rejected** (4.6%): 17 foreign — German *spreche(n)*, *erhalte(n)*,
  *verstehe*, *gerade*, *bringe(n)*, *davo(n)*, *ziehe*, *dagege(n)*,
  *trage(n)*, *hoffe*; French *propo(sées)*, *française*, *ouvrage*,
  *voici*; English *applause*, *organisatio(n)*; Italian *(in) petto*.
  OCR *ruga* (ruĝa), *voco* (vicoj), *llia* (lia). Names *Oje*, *Iliono*.
  Fragment *ĵe*.
- **Segmentation**: 7 of 367 wrong (1.9%) — roots *brokato*, *kvirito*,
  *poplito*, *rutula* → `NO_SPLIT`; overrides *kunsentema*, *malsentema*
  (sent+em, not sen+tem) and *pliiĝadi* (pliiĝ+ad). `--recite` gave
  literary citations to batch-13's *favorega*, *ĝeniĝi*, *kolektinto*.

Totals after batch 14: **6723** v2 entries; corpus-mined **8939**, 6301
segmented and linked; dictionary **31395**; queue **5325** (broad 165,
mixed 3673, wp-only 1487). The broad tier is nearly exhausted: batch 15
finishes it and opens the mixed tier, where evidence is 1–2 literary
sources backed by ≥10 Wikipedia articles.

## Batch 15 (esp-l2q) — 500 reviewed, 487 promoted; broad tier exhausted

`DICT/review/v2-batch15-{a,b}.tsv`, re-mined first. Items 1–165 closed the
broad tier (3+1 down to 3+0 wp: *skvalo*, *laŭbeto*, *bastŝuo*,
*gagatnigra*); items 166–500 opened the **mixed tier** (2 literary sources
+ ≥43 wp), a sharp register change to modern and encyclopaedic vocabulary
(*distribuado* 2+1618, *teknologio*, *koncilio*, *komputila*, *arkeologio*,
*semajnfino*, *antisemitismo*, *sciencfikcia*, *ŝtatsekretario*).

- **487 lemma** (269 noun, 104 verb, 87 adj, 27 adv) — all promoted.
  Citations follow the register: 158 literary-only, 326 mixed
  literary+Wikipedia, 3 Wikipedia-only (*alinomi*, *sasanida*, *svahila* —
  their literary lines are the bare headword in lists).
- **13 rejected** (2.6%, lowest yet): 10 foreign (*mistake(n)*, *unable*,
  *durchau(s)*, *empfehle(n)*, *gesproche(n)*, *letzte(n)*, *(in)
  preparazione*, Spanish *como*, Latin *(nec plus) ultra*, French *gri(s)*);
  name *Ideografiko*; fragment *(La)tina*; inflection *konsiderati*
  (konsideratas).
- **Segmentation**: 14 of 320 wrong (4.4%, highest yet — loanwords cluster
  in the mixed tier): `NO_SPLIT` *artikulo*, *deporti*, *fragila*,
  *kapelano*, *lazareto*, *primara*, *referi*, *silikato*, *stratego*,
  *trompeto*; overrides *ekestri*, *finestiĝi* (fin+est+iĝ), *patroneco*,
  *patronino* (patron-). Expect this rate to hold through the mixed tier.

Totals after batch 15: **7210** v2 entries; corpus-mined **9426**, 6611
segmented and linked; dictionary **31882**; queue **4816** (broad 0, mixed
3329, wp-only 1487).

## Batch 16 (esp-1du) — 500 reviewed, 472 promoted

`DICT/review/v2-batch16-{a,b}.tsv`, re-mined first: mixed tier, 2 literary
sources + 43 down to 15 wp (*emberizo*, *militismo*, *akumulatoro*,
*skafaldo*, *superkontinento*, *veterinaro*, *heĝiro*, *harmoniumo*).

- **472 lemma** (260 noun, 80 verb, 110 adj, 22 adv) — all promoted. With
  only 2 literary sources, every entry now carries 2 literary + 1 Wikipedia
  citation (468), or Wikipedia only where the literary lines are bare
  list headwords (*superkontinento*, *mezpersa*, *hindarja*, *baŝkira*).
- **28 rejected** (5.6%): 19 foreign — Latin *linguae*, *Graeca*, *nobis*,
  *ergo*, *urbi et orbi*, *amicos*, *aureus*, *cinerea*, *rosea*; French
  *donne*, *lettre*, *centrale*, *mille*, *danse*; German *blaue*,
  *musikalische*, *grosse*; Italian *gli*; Polish *dla*. Names *Dido*,
  *Malaga*. OCR *tua* (tujan), *antaue*, *daurigi*. Inflection *parolati*
  (parolatas). `uncertain` *nono*, *hosti* (forms are of *hostio*),
  *kurulo*.
- **Segmentation**: 12 of 324 wrong (3.7%) — `NO_SPLIT` *bromido*,
  *deformi*, *dividendo*, *harmoniumo*, *kabino*, *metila*, *pietato*,
  *primadono*, *reportero*, *sternumo*, *veterinaro*; override *sensema*
  (sens+em, not sen+sem).

Totals after batch 16: **7682** v2 entries; corpus-mined **9898**, 6924
segmented and linked; dictionary **32354**; queue **4257** (mixed 2785,
wp-only 1472).

## Batch 17 (esp-13o) — 500 reviewed, 470 promoted

`DICT/review/v2-batch17-{a,b}.tsv`, re-mined first: the end of the 2-source
band (2+15 down to 2+10 wp) and the top of the **1-source band** (1 literary
+ 2122 down to 129 wp), where the vocabulary is overwhelmingly modern
(*reproduktado*, *setlejo*, *cifereca*, *interreta*, *retpaĝo*,
*referendumo*, *kosmoŝipo*, *infanĝardeno*, *dezajni*).

- **470 lemma** (279 noun, 81 verb, 91 adj, 19 adv) — all promoted; 456
  mixed literary+Wikipedia citations, 14 Wikipedia-only (their one literary
  source is a bare headword line).
- **30 rejected** (6.0%): 20 foreign — French *mariage*, *compte*,
  *dimanche*, *chien*, *spéciale*, *carte*, *touche*; German *glaube*,
  *hatte*, *stelle*, *herausgegeben*, *Prosa*, *dritten*, *liegen*; Latin
  *(camera) obscura*, *(deus ex) machina*; Italian *corpo*; English
  *division*; Russian *Novosti*; Slavic *slovo*. Names *Priamo*, *Gentano*.
  OCR *ankora*, *efa* (mis-encoded ĉefa), *ajo*, *asti* (estas). Fragment
  *ŭo*. `uncertain` *ruro*, *arĥi*, *riso*.
- **Segmentation**: 17 of 337 wrong (5.0%) — `NO_SPLIT` *altatona*,
  *demisii*, *eskadrono*, *kelaro*, *platino*, *popare*, *referato*,
  *referendumo*, *sekundara*, *semida*, *sidera*, *stadiono*, *statisto*,
  *ulemo*; overrides *alpisto* (alp+ist), *fanatismo* (fanat+ism), *senida*
  (sen+id). `--recite` gave literary citations to 8 batch-16 entries.

Totals after batch 17: **8152** v2 entries; corpus-mined **10368**, 7247
segmented and linked; dictionary **32824**; queue **3721** (mixed 2259,
wp-only 1462).

## Batch 18 (esp-1if) — 500 reviewed, 484 promoted

`DICT/review/v2-batch18-{a,b}.tsv`, re-mined first: 1-source band, 1
literary + 129 down to 39 wp. Modern and technical vocabulary throughout
(*kopirajto*, *televidilo*, *retpaĝaro*, *motorciklo*, *bushaltejo*,
*datumaro*, *elŝutebla*, *nubskrapulo*, *kolĥozo*).

- **484 lemma** (308 noun, 47 verb, 114 adj, 15 adv) — all promoted; 467
  mixed citations, 17 Wikipedia-only.
- **16 rejected** (3.2%): 14 foreign — Latin *in mundo*, *Sancti*,
  *Orientalis*, *pereat mundus*, *de bello*, *vitae*, *Ecclesiae*,
  *nostra*, *alpha*; French *recherche*; German *frei*; Spanish *noche*;
  Portuguese *rua*; italicised Italian *maestro*. Inflection *bezonati*;
  `uncertain` *anoŭdo*.
- **Segmentation**: 19 of 289 wrong (6.6%, highest yet) — false *re-*/*al-*
  prefixes dominate: `NO_SPLIT` *agendo*, *agrara*, *alemano*,
  *intersekco*, *irito*, *meteorito*, *paserino*, *reallernejo*,
  *restrikta*, *sulfato*, *sulfido*, *volatila*; overrides *alkemiisto*,
  *pubereco*, *reformanto*, *reformisma*, *regenerado*, *rekuperado*,
  *reorganizado*. The root *reform-* has now needed six overrides
  (reformado, reformemulo, reformisto, reformema, reformanto, reformisma):
  the root stock lacks it — filed as a follow-up.

Totals after batch 18: **8636** v2 entries; corpus-mined **10852**, 7524
segmented and linked; dictionary **33308**; queue **3181** (mixed 1746,
wp-only 1435).

## Batch 19 (esp-4h3) — 500 reviewed, 472 promoted

`DICT/review/v2-batch19-{a,b}.tsv`, re-mined first: one late broad-tier
arrival (*orientaziano*), then the 1-source band at 1 literary + 38 down to
22 wp (*olimpiado*, *inkunablo*, *haŭbizo*, *mustaĉo*, *zloto*,
*esperantido*, *superdozo*, *piedpilkado*).

- **472 lemma** (285 noun, 53 verb, 117 adj, 17 adv) — all promoted; 464
  mixed citations, 1 literary-only, 7 Wikipedia-only.
- **28 rejected** (5.6%): 20 foreign — Latin species epithets dominate
  (*communis*, *domesticus*, *americanus*, *medica*, *lutea*, *cristatus*,
  *palustris*, *europaea*, *dulce*, *aurea*); German *Griechische*,
  *singen*; French *femme*; Spanish *todas*; Italian *Divina*, *allegro*;
  Ido *loi*; Swahili *fisi*; Czech *červený*; *partito*. Names *Padova*,
  *Santi*. OCR *posteŭlo*, *reao*, *viko*, *ima*. `uncertain` *mikspota*,
  *inico*.
- **Segmentation**: 6 of 274 wrong (2.2%, down from 6.6%) — `NO_SPLIT`
  *disdegni*, *olimpiado*, *reverso*, *tornado*; overrides *perletere*
  (per+leter), *transportisto* (transport+ist). `--recite` gave literary
  citations to 5 batch-18 entries.

Totals after batch 19: **9108** v2 entries; corpus-mined **11324**, 7794
segmented and linked; dictionary **33780**; queue **2646** (mixed 1232,
wp-only 1414).

## Batch 20 (esp-s5u) — 500 reviewed, 457 promoted

`DICT/review/v2-batch20-{a,b}.tsv`, re-mined first: 1-source band at 1
literary + 22 down to 15 wp. Literary vocabulary dominates again
(*poreterne*, *prodaĵo*, *febleco*, *kreitaro*, *rumoro*, *tabelvorto*,
*lavmaŝino*, *tiranosaŭro*, *gaŭĉo*).

- **457 lemma** (282 noun, 58 verb, 104 adj, 13 adv) — all promoted; 453
  mixed citations, 4 Wikipedia-only.
- **43 rejected** (8.6%, highest yet): 33 foreign — Latin binomial
  epithets dominate (*sativa*, *officinalis*, *chinensis*, *nobilis*,
  *edulis*, *nucifera*, *mirabilis*, *merula*, *spinosa*, *domestica*,
  *africanus*, *Castanea*, *europaeus*, *europea*) plus Latin *coeli*,
  *nomine*, *nostris*, *veritas*, *cella*; French *celle*, *fille*,
  *militaire*, *Humaine*; Italian *Nuovo*, *cosa*, *sotto voce*,
  *Comedia*; German *neuesten*, *katholische*; Spanish *caballo*; Slavic
  *cena*; Polish fragment; English title *Inferno*. Names *Proteo*,
  *Marzo*, *Soma*, *Tanagro*. OCR *foino*, *preskai*, *jia*. `uncertain`
  *lidi*, *noĉita*, *okopo*.
- **Segmentation**: 10 of 271 wrong (3.7%) — `NO_SPLIT` *albumino*,
  *alveolaro*, *huligano*, *monisma*, *pentano*, *trapisto*, *violino*;
  overrides *eksplorado*, *nomadeca*, *senpereco*. Resegmentation also
  improved *antaŭeniĝi* (antaŭ+ENIĜ → ANTAŬEN+iĝ). `--recite` gave
  literary citations to 4 batch-19 entries.

Totals after batch 20: **9565** v2 entries; corpus-mined **11781**, 8058
segmented and linked; dictionary **34237**; queue **2125** (mixed 726,
wp-only 1399).

## Batch 21 (esp-1g0) — 500 reviewed, 461 promoted

`DICT/review/v2-batch21-{a,b}.tsv`, re-mined first: 1-source band at 1
literary + 15 down to 11 wp. Everyday and literary vocabulary
(*piĵamo*, *patkuko*, *sunokulvitro*, *krucvortenigmo*, *vestokompleto*,
*orangutano*, *papiamento*, *halukso*, *hufumo*).

- **461 lemma** (271 noun, 72 verb, 105 adj, 13 adv) — all promoted; all
  461 carry mixed (literary + Wikipedia) citations.
- **39 rejected** (7.8%): 25 foreign — Latin epithets (*cinereus*,
  *dioica*, *Persica*, *auritus*, *martius*, *rutilus*, *Gorilla*) plus
  Latin *hodie*, *licentia poetica*, *e classe*; Spanish *amigo*,
  *Fiesta*, *antiguo*; Italian *dell'*, *a giorno*, *senza*, *Guida*;
  German *akademischen*, *viele*; French *bleu*; Czech *ulice*; Polish
  *miasto*, *mene*; Hindi *chai*; Arabic *haji*. 8 names (*Penelopo*,
  *Malene*, *Herakleo*, *Labelo*, *Panini*, *Dore*, *Frigo*,
  *Barbatus*). OCR *anke*, *tala*, *illi*. `uncertain` *rozeta*,
  *malposte*, *okopa*.
- **Segmentation**: 10 of 302 wrong (3.3%) — `NO_SPLIT` *amaranto*,
  *elando*, *kolino*, *parketo*, *pleŭrito*, *sensora*, *sensoro*;
  overrides *korbatado* (korbat+ad), *malemigi* (mal+em+ig), *ĉefino*
  (ĉef+in). `--recite` gave literary citations to 2 batch-20 entries.

Totals after batch 21: **10026** v2 entries; corpus-mined **12242**, 8353
segmented and linked; dictionary **34698**; queue **1623** (mixed 225,
wp-only 1398).

## Batch 22 (esp-n1x) — 500 reviewed, 474 promoted; mixed tier exhausted

`DICT/review/v2-batch22-{a,b}.tsv`, re-mined first. Items 1–223 closed the
mixed tier (1 literary + 11..10 wp, plus one late 2+52 arrival,
*lingvolernado*); items 224–500 opened the **wp-only tier** (0 literary,
2920 down to 155 wp). The wp-only head is modern encyclopaedic
vocabulary — biology (*populacio*, *habitato*, *subspecio*, *taksono*,
*klado*, *nestumi*, *elnestiĝi*), administration (*komarko*,
*arondismento*, *subŝtato*), and modern life (*flughaveno*, *videoludo*,
*poŝtelefono*, *aplikaĵo*, *biodiverseco*, *tutmondiĝo*). Wikipedia
neologisms *setli*/*setliĝi*/*setlanto* and *survivi* are accepted as
attested usage.

- **474 lemma** (316 noun, 45 verb, 98 adj, 15 adv) — all promoted; 199
  mixed citations, 275 Wikipedia-only (the wp tier by definition).
- **26 rejected** (5.2%): 17 foreign — Latin epithets (*terrestris*,
  *campestris*, *tremula*, *capreolus*, *cuniculus*, *onca*, *cursus*,
  *Caja*, *in corpore*), German (*Religionen*, *englische*, *gebildete*,
  *graue*, *menschlichen*), French *espace*, *Sauvage*; Spanish *cuna*.
  4 inflections — passive *-itis* forms (*submetitas*, *malkonstruitis*,
  *nomumitis*, *starigitis*), a Wikipedia register habit. Name *Hache*.
  OCR *aia*, *labe*, *mondoo*, *ambai*.
- **Segmentation**: 20 of 282 wrong (7.1%, highest yet) — wp vocabulary
  is loan-heavy. `NO_SPLIT` *efemerido*, *ekosistemo*, *ekozono*,
  *elama*, *fibolo*, *humanitara*, *kalendo*, *klorato*, *logoteto*,
  *retablo*, *romantisma*, *romantismo*, *survivi*, *taksono*,
  *transportreto*, *uzino*, *vertiĝo*; overrides *fortransporti*
  (for+transport), *habilitiĝi*, *rekuperiĝi* (the *rekuper-* root again;
  see esp-b3y). `--recite` gave literary citations to 2 batch-21 entries.

Totals after batch 22: **10500** v2 entries; corpus-mined **12716**, 8618
segmented and linked; dictionary **35172**; queue **1119** (all wp-only).

## Batch 23 (esp-rz5) — 500 reviewed, 487 promoted

`DICT/review/v2-batch23-{a,b}.tsv`, re-mined first: wp-only tier, 0
literary + 155 down to 74 wp. Encyclopaedic register throughout:
ornithology (*vadbirdo*, *flugilpinto*, *kovoperiodo*, *idozorgado*,
*turfalko*, *petrelo*), music (*konĉerto*, *moteto*, *klaviceno*,
*bibopo*, *saksofonisto*), politics and society (*secesio*, *junto*,
*privatigo*, *balotrajto*, *neprofitcela*), and modern technology
(*komputiko*, *ĝisdatigo*, *animeo*, *kronvirusa*).

- **487 lemma** (316 noun, 47 verb, 116 adj, 8 adv) — all promoted, all
  with Wikipedia-only citations.
- **13 rejected** (2.6%, lowest of the v2 run): 8 inflections — the
  Wikipedia passive *-itas*/*-itis* habit (*menciitas*, *malkonstruitis*,
  *detruitis*, *entombigitis*, *forigitis*, *uzitas*, *instalitis*,
  *situantas*); names *Guerra*, *Americana*, *Anio*; Latin *contra*; typo
  *eoste*.
- **Segmentation**: 9 of 262 wrong (3.4%) — `NO_SPLIT` *duonarida*,
  *forceja*, *kampanilo*, *maskoto*, *moteto*, *ordino*, *substrato*,
  *superintendanto*; override *subaro* (sub+ar). `--recite` gave literary
  citations to 5 earlier entries.

Totals after batch 23: **10987** v2 entries; corpus-mined **13203**, 8872
segmented and linked; dictionary **35659**; queue **582** (all wp-only).

## Batch 24 (esp-a7p) — 564 reviewed, 540 promoted; queue exhausted

`DICT/review/v2-batch24-{a,b}.tsv` (282 each), re-mined first: one late
mixed arrival (*morfino*, 2+39) then the rest of the wp-only tier (0
literary, 82 down to 50 wp). Science and culture vocabulary
(*termodinamiko*, *triglicerido*, *imunsistemo*, *eoceno*, *perestrojko*,
*kantaŭtoro*, *rulseĝo*, *serĉilo*, *komikso*, *ŝario*).

- **540 lemma** (352 noun, 43 verb, 137 adj, 8 adv) — all promoted; 539
  Wikipedia-only citations, 1 mixed.
- **24 rejected** (4.3%): 10 foreign — Spanish (*viejo*, *El Tiempo*,
  *la muerte*, *hombre*), Italian (*per Musica*, *di Cappella*), Latin
  (*Ex Causa*, *australis*, *occidentalis*), German *Heiligen*; 10
  passive *-itas*/*-itis* inflections; names *Navara*, *Goeta*, *Gotaa*,
  *Morava*.
- **Segmentation**: 16 of 271 wrong (5.9%) — `NO_SPLIT` *alkazaro*,
  *antero*, *boreala*, *centropo*, *entento*, *interfero*, *kastrumo*,
  *kortuma*, *morfino*, *palatina*, *primaso*, *pufino*, *stipulo*,
  *trogono*; overrides *devoteco* (devot+ec), *diseriĝi* (dis+er+iĝ).

Totals after batch 24: **11527** v2 entries; corpus-mined **13743**, 9129
segmented and linked; dictionary **36199**; queue **0** at the esp-nuk
thresholds (broad >= 3 other, mixed 1–2 other + >= 10 wp, wp-only >= 50
wp, all >= 5 occurrences).

### Next tier (probed, not yet applied)

`gap_report.py` threshold probes against the batch-24 ledger:

| thresholds | new queue |
|---|---|
| `--min-sources 2` (broad = 2 other sources) | 1670 broad |
| `--mixed-wp 5` (1 other + 5..9 wp) | 2296 mixed |
| `--wp-only 25` (25..49 wp) | 1997 wp-only |
| `--mixed-wp 5 --wp-only 25` | 4293 |

The literary-first order is: 2-source broad (1670) → mixed at 5 wp (2296)
→ wp-only at 25 (1997). Filed as follow-up beads.

## Batch 25 (esp-i9h) — phase 2 opens: broad tier lowered to 2 sources

`tools/gap_report.py --min-sources` default **3 → 2**: the broad tier now
takes any lemma with two non-Wikipedia sources (1675 queued after the
re-mine; 1671 broad). `DICT/review/v2-batch25-{a,b}.tsv` covers items
1–500: 2 literary + 24 down to 5 wp. Literary register returns —
*pilafo*, *odoraĉo*, *dentobroso*, *kanonkuglo*, *gardhundo*,
*fenestrobreto*, *marĉandado*, *kokosnukso*, *vaporboato*, *ŝeolo*;
plus Soviet-era language names (*komia*, *udmurta*, *erzja*, *evenka*,
*inguŝa*) from a nationality list.

- **465 lemma** (263 noun, 100 verb, 87 adj, 15 adv) — all promoted; 463
  mixed citations, 2 literary-only. Verbs are back at 21% (Wikipedia
  tiers ran ~10%).
- **35 rejected** (7%): 27 foreign — multilingual word lists and
  quotations in French (*neige*, *oui*, *maison*, *depuis*, *peine*,
  *neveu*, *Ancien*, *arbre*, *reconnaissance*, *comprendre*), German
  (*sieben*, *deren*, *eigenen*, *neben*, *bleiben*, *brauchen*,
  *rechten*), Polish (*kto*, *moja*), Latin (*terra incognita*, *mihi*,
  *arvensis*, *a posteriori*, *civis*), English (*devotion*, *selection*,
  *cuisine*); names *Karara*, *Fileo*; OCR *nla*, *proti*; fragment
  interjection *ĥo*; `uncertain` *ibo*, *ostero*, *mando*.
- **Segmentation**: 8 of 347 wrong (2.3%, literary vocabulary splits
  cleanly) — `NO_SPLIT` *agregato*, *gracila*, *kabilo*, *limono*,
  *senila*; overrides *brokantisto*, *geido* (ge+id), *pietisto*.

Totals after batch 25: **11992** v2 entries; corpus-mined **14208**, 9471
segmented and linked; dictionary **36664**; queue **1175** (broad 1171).

## Batch 26 (esp-6iu) — 500 reviewed, 468 promoted

`DICT/review/v2-batch26-{a,b}.tsv`, re-mined first: 2-source broad tier,
2 literary + 5 down to 3 wp. Everyday literary vocabulary (*boatejo*,
*diliĝenco*, *pelerino*, *bilardejo*, *kahelforno*, *cigaredujo*,
*vekilo*, *ŝlosilaro*, *avĉjo*, *knabinjo*, *kokeriki*, *miaŭado*).

- **468 lemma** (274 noun, 99 verb, 77 adj, 18 adv) — all promoted; 455
  mixed citations, 13 literary-only.
- **32 rejected** (6.4%): 20 foreign — German word-list entries
  (*setzen*, *mehrere*, *dabei*, *offen*, *schlafen*, *dazu*, *schicken*,
  *fahren*, *kennen*, *geschrieben*), French (*pomme*, *jamais*,
  *annuaire*, *mesure*), English (*usage*, *proportion*), Latin (*vae*,
  *ignis*), Italian *addio*, Norwegian *norske*; names *Amona*, *Suza*,
  *Luigi*; 6 OCR (*fmi*, *nagi*, *divi*, *moneto* for montetoj, *deja*,
  *trati*); fragment *labo-*; `uncertain` *ĵo*, *agao*.
- **Segmentation**: 9 of 350 wrong (2.6%) — `NO_SPLIT` *deligito*,
  *desaponti*, *ĝojatendi*, *kuloto*, *pelerino*, *revizo*; overrides
  *patronaro* (patron+ar), *plikonatiĝi* (pli+kon+at+iĝ),
  *prizorgantino* (pri+zorg+ant+in). `--recite` gave literary citations
  to 15 batch-25 entries.

Totals after batch 26: **12460** v2 entries; corpus-mined **14676**, 9815
segmented and linked; dictionary **37132**; queue **671** (broad 667).

## Batch 27 (esp-a2u) — 667 reviewed, 617 promoted; 2-source tier exhausted

`DICT/review/v2-batch27-{a,b,c}.tsv` (223/222/222), re-mined first: the
whole remaining 2-source broad tier (2 literary + 3 down to 0 wp) plus 4
late arrivals. The most literary batch of the run: **380 of 617 entries
cite only literature** (0 wp). Homeric epithets (*bovookula*,
*rapidapieda*, *kuproarmita*), domestic and period vocabulary
(*dormoĉapo*, *naztuketo*, *portseĝo*, *fumpotĉapelo*, *etaĝero*,
*diliĝenco*-era *kaleŝego*), prosody (*iambo*, *troĥeo*).

- **617 lemma** (369 noun, 126 verb, 100 adj, 22 adv) — all promoted;
  380 literary-only, 234 mixed, 3 Wikipedia-only.
- **50 rejected** (7.5%): 31 foreign (German word-list and letter-model
  verbs — *bauen*, *erschienen*, *fangen*, *gegeben*, *vergessen*,
  *folgende*, *nennen*, *zeigen*, *herzlichen*…; French *traduire*,
  *aucune*, *parce*, *suivre*; English *creation*, *innovation*,
  *resolution*, *tense*, *of the*; Polish *gdzie*; Latin *nulli*; Italian
  *si muove*; Arabic *marhaba*); 10 OCR (*autoro*, *efi*, *tumi*,
  *lajaro*, *iingvo*, *lnternacia*, *rekonti*, *circonstanco*, *esli*,
  *vovo*); 4 inflections (*preferintus*, three Homeric participle
  epithets); names *Donja*, *Havra*; fragments *ulo*, *ineto*;
  `uncertain` *neno*.
- **Segmentation**: 8 of 425 wrong (1.9%) — `NO_SPLIT` *amontilado*,
  *etaĝero*, *folianto*, *limeto*, *rubino*, *samumo*; overrides
  *seninda* (sen+ind), *ĉekano* (ĉek+an). `--recite` gave literary
  citations to 26 batch-26 entries.

Totals after batch 27: **13077** v2 entries; corpus-mined **15293**,
10234 segmented and linked; dictionary **37749**; queue **0** again —
next is esp-jpn (mixed at 5 wp, wp-only at 25).

## Loan-root stock (esp-b3y)

The segmenter's root stock knows a radiko only when some layer supplies it
as `root` or `_mined_roots` recovers it from a standalone entry. Neither
works for loanwords whose bare form itself reads as an affix split:
*reformo* parses as re+form-o, *transporti* as trans+port-i, *patrono* as
patr+on-o, so the real root never enters the stock and every derivative
needed a `SPLIT_OVERRIDE` — 26 of the 60 overrides served just 15 roots.

`promote_lemmas.LOAN_ROOTS` now adds those 15 roots (alkemi, brokant,
devot, eksplor, fanat, fiakr, habilit, nomad, patron, piet, puber, reform,
regener, rekuper, transport) to the stock at rank 4 (mined-root rank).
All 26 overrides reproduced exactly without them and were removed (60 →
34). `--resegment v2-` + `shard-` corrected 7 pre-v2 entries the overrides
never reached: *reformo*, *transporti*, *transporto* (re+FORM / trans+PORT
→ unsplit root) and *transportebla*, *-igi*, *-iĝi*, *-ilo*
(trans+PORT+x → TRANSPORT+x). Segmented corpus-mined: 10234 → 10231;
nothing else changed; dry runs 0. Future derivatives of these roots split
correctly with no override. Add a root here once it has needed ~3
overrides (the same rule as in the skill).

## Phase 2b, batch 28 (esp-jpn) — mixed@5 / wp-only@25; 500 reviewed, 454 promoted

`gap_report.py` defaults lowered: `--mixed-wp` 10 → 5, `--wp-only` 50 → 25
(the broad tier at 2 literary sources was exhausted by batch 27). After
re-mining against the batch-27 dictionary the queue held **3581**: mixed
1615, wp-only 1966 (the probe's 2296 mixed shrank as batch 26–27 stems
absorbed siblings). Batch 28 took the top 500: 1 literary source + 9 down
to 7 wp articles.

- **454 lemma** (275 noun, 91 adj, 65 verb, 23 adv) — all promoted; 452
  mixed citations, 2 Wikipedia-only (*odia*, *sorana*: the literary hit is
  absent from the miner sample).
- **46 rejected** (9.2%, the band's expected 3–9% upper end): 32 foreign
  — Latin binomial epithets (*pratensis*, *noctua*, *arabica*,
  *giganteus*, *officinale*, *camelus*, *fluviatilis*, *avellana*,
  *Melia*), multilingual word lists (*chimie*, *blau*, *ziemia*, *dva*),
  Czech *divadlo*/*strana*/*časopis*, Spanish *relación*, Italian *Duce*,
  *i miei*, German *Reisende*, *dunkle*, Latin *modus vivendi*, *nomina*,
  *notitia*; 4 fragments (*alMi*, *alLi*, *alLiaj* run-together pronoun
  capitals in Bahá'í texts; *Sno.*); 3 OCR (*malla*, *kja*, *dauro*); 3
  names (*Jamato*, *Baŝo*, *Partujo*); 3 `uncertain` (*pajo*, *timbo*,
  *tila*); 1 inflection (*volintus*).
- **Segmentation**: 18 of 292 wrong (6.2%, loan-heavy band as forecast) —
  `NO_SPLIT` *alamano*, *aĥila*, *fonetismo*, *legumo*, *licenciato*,
  *peritoneito*, *prikazo*, *serpentino*, *sorana*, *supino*, *temerara*,
  *trilitera*, *turbulo*; overrides *alpinisto* (alpin+ist), *elfino*
  (elf+in), *religo* (re+lig), *taŭridano* (taŭrid+an), *ekretiriĝi*
  (ek+retir+iĝ). The esp-b3y loan roots needed no override this batch.
  `--recite` gave literary citations to 4 batch-27 entries.

Totals after batch 28: **13531** v2 entries; corpus-mined **15747**,
10510 segmented and linked; dictionary **38203**; queue **3081** (mixed
1115, wp-only 1966).

## Batch 29 (esp-3bg) — 500 reviewed, 437 promoted

`DICT/review/v2-batch29-{a,b}.tsv`, re-mined first: mixed tier 1 literary
source + 7 down to 6 wp (plus one 2+10 late arrival, *militservado*).

- **437 lemma** (265 noun, 93 adj, 66 verb, 13 adv) — all promoted; all
  437 carry mixed literary+wp citations.
- **63 rejected** (12.6%, above the band's 3–9%): 52 foreign — the
  multilingual word-list source (`vojo route, voie | way | Weg | дорога`)
  now dominates the 1-literary band: French *voie*, *affaire*, *seconde*,
  *ordinaire*, *samedi*, *parmi*, *poche*, *droite*, *taille*, German
  *siehe*, *einzige*, *heutigen*, *ihnen*, *Thema*, Polish *panna*,
  *ludzie*, *nauka*; Latin binomials (*glandarius*, *murinus*, *carica*,
  *oleracea*, *caballus*, *migratorius*) and tags (*amor fati*, *diem
  perdidi*, *remedia amoris*); Italian *troppo*, *molto*, *viaggio*,
  *clemenza*; Spanish/Portuguese *coche*, *dinero*, *guia*. 5 `uncertain`
  (*vao*, *safo*, *klimo*, *hermo*, *siano*), 3 inflections (*fariĝintus*,
  *akirintus*, *celebratas*), 2 fragments (*mem'*, dialect *kjo*), name
  *Jasa*.
- **Segmentation**: 15 of 287 wrong (5.2%) — `NO_SPLIT` *aŭtoriteco*,
  *debila*, *delico*, *ekstraordinara*, *elementara*, *fermato*,
  *membronumero*, *mondono*, *nenifarado*, *primora*, *tarantulo*,
  *termonteto*; overrides *moneraro* (moner+ar), *pranevino*
  (pra+nev+in), *remaĉulo* (re+maĉ+ul). `--recite` gave literary
  citations to 23 batch-28 entries (incl. *sorana*).

Totals after batch 29: **13968** v2 entries; corpus-mined **16184**,
10785 segmented and linked; dictionary **38640**; queue **2574** (mixed
613, wp-only 1961).

## Batch 30 (esp-9i4) — 613 reviewed, 552 promoted; mixed tier exhausted

`DICT/review/v2-batch30-{a,b,c}.tsv` (205/204/204), re-mined first: the
whole remaining mixed tier, 1 literary source + 6 down to 5 wp.

- **552 lemma** (328 noun, 121 adj, 74 verb, 29 adv) — all promoted; 550
  mixed citations, 2 literary-only.
- **61 rejected** (10.0%): 36 foreign (word-list columns *sterben*,
  *suchen*, *semaine*, *borgen*, *lounge*; Latin binomials and tags
  *Pinus pinea*, *Trutta fario*, *Theobroma cacao*, *fiat justitia*, *in
  habitu*; German *Komitee*, *Methode*, *Spanische*, *schade*; Japanese
  *kumi*; Portuguese *jornada*), 7 OCR (*malkrovi*, *maĝo*←manĝo,
  *manĝaĝo*←manĝaĵo, *aii*, *oia*, *ifri*, *kvazai*), 7 `uncertain`
  (*etono*, *dadi*, *dobo*, *rono*, *svito*, *tajlo*, *viĉo*), 5
  fragments (*oklo*, *pro-ponoj*, *tradu_kar_*, *dudekunu*, *ptoj*), 3
  names (*Likaonido*, *Guna*, *Leta*), 3 inflections (*sciatas*,
  *dubendas*, *atingintis*).
- **Segmentation**: 16 of 356 wrong (4.5%) — `NO_SPLIT` *akratona*,
  *cedrato*, *depozicio*, *indiumo*, *kanopo*, *kastila*, *kombato*,
  *kupulo*, *morbida*, *musketo*, *orfano*, *relato*, *saksona*,
  *ververe*; overrides *reagema* (reag+em), *respirado* (respir+ad).
  `--recite` gave literary citations to 11 batch-29 entries.

Totals after batch 30: **14520** v2 entries; corpus-mined **16736**,
11127 segmented and linked; dictionary **39192**; queue **1956**, all
wp-only (>= 25 wp, no literary source).

## Batch 31 (esp-6d4) — wp-only@25, 500 reviewed, 473 promoted

`DICT/review/v2-batch31-{a,b}.tsv`, re-mined first: wp-only tier (no
literary source) 69 down to 39 wp articles. Modern encyclopaedic
vocabulary: *saĝtelefono*, *kosmoteleskopo*, *ritmenbluso*, *seksismo*,
*rearbarigo*, *trabfakaĵo*, *masklarejo*, *kladogramo*.

- **473 lemma** (307 noun, 122 adj, 36 verb, 8 adv) — all promoted, all
  with Wikipedia-only citations by construction.
- **27 rejected** (5.4%): 16 inflections — the Wikipedia passive habit
  *-itis*/*-atas* (*venditis*, *deklaritis*, *publikigitis*,
  *konsekritis*, *dungitis*, *transportitis*, *troviĝantas*…); 9 foreign
  (*Africano*, *Cultura*, *Cidade*, *freguesias*, *Enseñanza*, Latin
  *sive*, *canadensis*, *capensis*, *robusta*); fragment *umava*
  (Šumava); `uncertain` *koĉo* (cochineal vs. coach).
- **Segmentation**: 16 of 214 wrong (7.5%, loan-heavy) — `NO_SPLIT`
  *acetono*, *albedo*, *cianido*, *elektrika*, *hepatito*, *liberaĉeti*,
  *pinjono*, *stigmato*, *talibano*, *ĥanato*; overrides
  *kontraŭregistara*, *laŭtema* (laŭ+tem), *libretisto*, *repisto*
  (rep+ist), *reorganiziĝi*, *separatisma*. `--recite` gave literary
  citations to 13 batch-30 entries.

Totals after batch 31: **14993** v2 entries; corpus-mined **17209**,
11331 segmented and linked; dictionary **39665**; queue **1450** (all
wp-only, 39 down to 25 wp).

## Batch 32 (esp-3qq) — wp-only, 500 reviewed, 473 promoted; dictionary passes 40k

`DICT/review/v2-batch32-{a,b}.tsv`, re-mined first: wp-only tier 93 down
to 32 wp articles. *ŝtatrenverso*, *saĝtelefono*-era *sunpanelo*,
*superheroo*, *duonkonduktaĵo*, *korbopilko*, *apoptozo*, *reciklado*,
*ventomuelejo*, *kosmopramo*.

- **473 lemma** (309 noun, 121 adj, 33 verb, 10 adv) — all promoted,
  Wikipedia-only citations.
- **27 rejected** (5.4%): 15 foreign (Spanish/Italian/Latin title and
  epithet words *Siete*, *Agua*, *Primera*, *viridis*, *gigas*,
  *japonica*, *cum laude*, *concerto grosso*, *sacrae*, *sopra*…), 5
  inflections (*muntitis*, *trovatas*, *kondamnitis*, *fermitis*,
  *planitis*), 3 names (*Toda*, *Aĥeno*, *Valdivia*), 2 `uncertain`
  (*esperto*, *tempero*), OCR *pocento* (procento), key collision *rupi*
  (rupio).
- **Segmentation**: 10 of 239 wrong (4.2%) — `NO_SPLIT` *bukono*,
  *elfarbaro*, *fulmaro*, *kaĝara*, *kontinuumo*, *migradopado*,
  *opidumo*, *subenkurba*; overrides *aranereto* (arane+et),
  *nereproduktulo* (ne+reprodukt+ul).

Totals after batch 32: **15466** v2 entries; corpus-mined **17682**,
11562 segmented and linked; dictionary **40138**; queue **941** (all
wp-only, 32 down to 25 wp).

## Batch 33 (esp-dx7) — wp-only, 500 reviewed, 480 promoted

`DICT/review/v2-batch33-{a,b}.tsv`, re-mined first: wp-only tier 32 down
to 28 wp articles. *kukabarao*, *nukleotido*, *eritrocito*, *obezeco*,
*bioteknologio*, *gasgiganto*, *kompaktdisko*, *volejbalo*, *jogurto*,
*benzinstacio*.

- **480 lemma** (331 noun, 105 adj, 38 verb, 6 adv) — all promoted,
  Wikipedia-only citations.
- **20 rejected** (4.0%): 9 foreign (*otras*, *goldenen*, *iPhone*,
  *Sesto*, *encomienda*, *anthos*, *adversus*, *arctos*, *officinalis*
  calque *oficina*), 8 `-itis`/`-atas` passives, 2 fragments (*ilina* ←
  Žilina; *ekskreci*, key collision with *ekskrecio*), name *Kari*.
- **Segmentation**: 20 of 225 wrong (8.9%) — 14 `NO_SPLIT` (*johanito*,
  *kombinato*, *krepuskula*, *lignito*, *mediana*, *militarismo*,
  *nukleotido*, *parieto*, *plumpinto*, *putino*, *sensorgano*,
  *sudeta*, *trilatere*, *ĉefaktoro*); 6 overrides (*interreproduktado*,
  *diserigi*, *malina*, *navarano*, *retirigi*, *retirigo*). The
  esp-b3y loan root *reform-* split *reformiĝi* correctly with no
  override.

Totals after batch 33: **15946** v2 entries; corpus-mined **18162**,
11773 segmented and linked; dictionary **40618**; queue **433** (all
wp-only, 28 down to 25 wp).

## Batch 34 (esp-qo7) — 432 reviewed, 411 promoted; phase-2b queue empty

`DICT/review/v2-batch34-{a,b}.tsv` (216/216), re-mined first on top of
glm's concordance sweep (f8e0d2b: 1505 `attestation` blocks refreshed by
the web lane, same shape, counts within a few sources — no conflict with
attest_scan). The whole remaining wp-only queue, 28 down to 25 wp, plus
one late mixed arrival (*populacigrandeco*).

- **411 lemma** (250 noun, 118 adj, 32 verb, 11 adv) — all promoted.
- **21 rejected** (4.9%): 11 foreign (*Bodas de Sangre*, *peuple*, *motu
  proprio*, *senegalensis*, *peregrinus*, *Homo erectus*, *Polskie*,
  *historischen*, *Fidei*, *Reino*, Spanish *inca*), 5 `-itis` passives,
  3 fragments (*lycéenne*, *Weißensee*, *Intra-*), OCR *ĉeha* (ĉeĥa),
  name *Lankastro*.
- **Segmentation**: 13 of 188 wrong (6.9%) — `NO_SPLIT` *benediktina*,
  *bolero*, *encefalito*, *holisma*, *kanino*, *kurona*, *nekrozo*,
  *populisma*, *reaktiva*, *realnome*, *teknikumo*, *trilera*; override
  *negado* (neg+ad). The *reaktiva* root then re-split the older
  *reaktivigi*/*reaktiviĝi* as reaktiv+ig/iĝ — overridden back to
  re+aktiv+ig/iĝ (reactivate).

Totals after batch 34: **16357** v2 entries; corpus-mined **18573**,
11949 segmented and linked; dictionary **41029**; queue **0** at the
esp-jpn thresholds.

### Phase 2c probe (after batch 34, `--queue $TMPDIR/probe.jsonl`)

| setting | mixed | wp-only | queue |
|---|---|---|---|
| mixed-wp 4, wp-only 20 | 672 | 1040 | 1712 |
| mixed-wp 3, wp-only 20 | 1016 | 1040 | 2056 |
| mixed-wp 3, wp-only 15 | 1016 | 2824 | 3840 |

Other buckets: `capitalised` 3150 (demonyms such as *italiano* that only
appear capitalised, held pending a names policy), `foreign` 1984,
`participle` 16683. Literary-first order: lower the mixed tier to 3 wp
first (1016), then wp-only to 20 (1040); 15 wp roughly triples the
wp-only band and should wait for a rejection-rate check at 20.

## Batch 35 (esp-273) — phase 2c opens; 500 reviewed, 444 promoted

esp-273 lowered the `gap_report` defaults to `--mixed-wp 3 --wp-only 20`
(queue 2047: mixed 1014, wp-only 1033). `DICT/review/v2-batch35-{a,b}.tsv`
covers the top 500 — the mixed tier at 1 literary + 4 wp — so **443 of
the 444 new entries carry a literary citation** (*sestino*, *jarlo*,
*grioto*, *termidoro*, *kedivo*, *oraĝo*, *liberpensanto*, *sakŝalmisto*,
*pupteatristo*, *ĉionmanĝanto*).

- **444 lemma** (281 noun, 85 adj, 62 verb, 16 adv) — all promoted.
- **56 rejected** (11.2%, double the wp-only rate — one literary source
  is a weak filter at 4 wp): 30 foreign (Latin binomials *Pinus cembra*,
  *Rubus idaeus*, *Tilia parvifolia*; German/French/Polish/Swahili
  entries of multilingual word lists *lauten*, *milieu*, *frais*,
  *jezioro*, *rafiki*, *sasa*; titles *Arc de Triomphe*, *Mesopotamia*),
  13 fragments (mojibake *dediÄante*, *ĝuados*, *alproksimiÄis*; elided
  *lingvon'*, *Mine'*), 6 names (*Nereus*, *O'Hara*, *Robin*, *Annaeus*,
  *Amala*, *Deino*), 3 OCR (*nmi*, *aaaa*, *avanaj*), 3 `uncertain`
  (*bullo* — standard *bulo*; *konversa*; *maliĝi*), 1 inflection
  (*dirintus*).
- **Segmentation**: 10 of 289 wrong (3.5%) — `NO_SPLIT` *arkana*,
  *budista*, *enirvojo*, *grioto*, *livida*, *skorpiono*; overrides
  *molinismo* (molin+ism), *malorganizado*, *intergeedzeco*
  (inter+ge+edz+ec), *disvastigiteco* (dis+vast+ig+it+ec).

Totals after batch 35: **16801** v2 entries; corpus-mined **19017**,
12232 segmented and linked; dictionary **41473**; queue **1547** (mixed
514 at 1+4..1+3, wp-only 1033).

## Batch 36 (esp-hmx) — mixed tier finished; 515 reviewed, 434 promoted

`DICT/review/v2-batch36-{a,b}.tsv` (258/257), re-mined first: the whole
remaining mixed tier, 1 literary + 5..3 wp. Every new entry carries a
literary citation (*trojko*, *arĥimandrito*, *pasigrafio*, *florealo*,
*cindromerkredo*, *smilodonto*, *kavernurso*, *ĉielskrapulo*,
*vortŝerco*, *bazopilko*).

- **434 lemma** (277 noun, 91 adj, 52 verb, 14 adv) — all promoted.
- **81 rejected** (15.7%, up from 11.2% at 1+4): 41 foreign (Latin
  binomials, German/French/Polish/Czech/Portuguese word-list cells,
  Occidental/Ido pronouns *vostre*, *omno*), 14 `uncertain` (poetic
  elisions *gel'*, *fol'*, *tret'*; non-standard *definicio*, *lupulo*,
  *somno*), 11 OCR (*oio*/*oie* for ĉio/ĉie, *reSo* for reĝo, *Lombon*
  for tombon, *savaĝa*, *risa*, *antiva*, *pompilo*), 10 fragments, 5
  names. The 1-literary tier gets noisier as wp support drops; the lit
  source is often a single OCR'd Bahá'í or poetry scan.
- **Segmentation**: 14 of 274 wrong (5.1%) — `NO_SPLIT` *georgino*,
  *klareto*, *oficino*, *plakato*, *returniri*, *taliumo*, *ursulina*;
  overrides *kuniĝadi*, *misionisto* (mision+ist), *peraera*/*peraere*
  (per+aer), *reformulo* (reform+ul), *republikano*, *restariginto*
  (re+star+ig+int).
- `--recite v2-` gave 31 batch-35 entries extra literary passages from
  their one literary source (literary-first ordering), replacing
  Wikipedia second/third citations.

Totals after batch 36: **17235** v2 entries; corpus-mined **19451**,
12499 segmented and linked; dictionary **41907**; queue **1030** (all
wp-only, >= 20 wp). Mixed tier exhausted at 1 lit + 3 wp.

## Batch 37 (esp-6g2) — wp-only >= 20; 500 reviewed, 459 promoted

`DICT/review/v2-batch37-{a,b}.tsv`, re-mined first: wp-only 44 down to
22 wp (a few late arrivals above 25). *eŭkarioto*, *homeostazo*,
*tabulkomputilo*, *tekokomputilo*, *nuboskrapulo*, *kibernetiko*,
*ventogeneratoro*, *azilpetanto*, *kontinentbreto*, *orcino*.

- **459 lemma** (320 noun, 100 adj, 31 verb, 8 adv) — all promoted.
- **41 rejected** (8.2%): 28 foreign (Latin binomial epithets and titles
  *arborea*, *virginianus*, *Summa Theologiae*, *sensu stricto*;
  Spanish *caso*, *obra*, *loco*, *silencio*, *Patrimonio*), 5
  `-itis`/`-atas` passives, 5 `uncertain` anglicisms or non-standard
  forms (*klami* claim, *reserĉado* research, *eksterna*, *difera*,
  *nomendas*), 2 fragments (LaTeX *theta*, *Żeromski*), *Metallica*.
- **Segmentation**: 17 of 222 wrong (7.7%) — 13 `NO_SPLIT` (*arkonto*,
  *bubona*, *halogenido*, *keratino*, *kvarcito*, *patriarkato*,
  *perianto*, *piaristo*, *pilono*, *romanida*, *uropiga*, *vaskono*,
  *vetono*); overrides *endemismo*, *erotismo*, *separatisto*,
  *surrealismo*. Chemistry/biology *-id*, *-on*, *-at* endings are the
  usual trap.
- `--recite v2-` added literary passages to 9 batch-36 entries.

Totals after batch 37: **17694** v2 entries; corpus-mined **19910**,
12708 segmented and linked; dictionary **42366**; queue **528** (all
wp-only, 22..20 wp).

## Batch 38 (esp-1qw) — 526 reviewed, 472 promoted; phase-2c queue empty

`DICT/review/v2-batch38-{a,b}.tsv` (263/263), re-mined first: the whole
remaining wp-only queue, 22 down to 20 wp (*limgardistaro* at 27 a late
arrival). *platotektoniko*, *jonosfero*, *radioteleskopo*, *bitlibro*,
*aviadilŝipo*, *trafikŝtopiĝo*, *ventoturbino*, *sufrageto*, *kazuaro*.

- **472 lemma** (318 noun, 103 adj, 39 verb, 12 adv) — all promoted.
- **54 rejected** (10.3%): 24 foreign (Latin epithets *scrofa*,
  *latifolia*, *griseus*; Spanish *Castellana*, *fuego*, *hija*,
  *Adelantado*; Portuguese *caatinga*, already held as *kaatingo*),
  14 `uncertain` (non-standard or calqued *esperti*, *rivelado*,
  *regnado*, *interioro*, *kurva*, *rebo*; unclear coinages), 8
  `-itis`/`-atas` passives, 4 names, 3 fragments (LaTeX *rho*,
  *aŭtomobilo* → *mobila*, *contienen*), typo *fenomenono*.
- **Segmentation**: 16 of 225 wrong (7.1%) — 12 `NO_SPLIT` (*altitudina*,
  *arilo*, *bazotono*, *fluorido*, *internaciskale*, *konstantina*,
  *ladina*, *livono*, *pasato*, *saponino*, *travertino*, *velara*);
  overrides *kapetido*/*kapetida* (kapet+id), *konsolidiĝi*,
  *majoratulo*.

Totals after batch 38: **18166** v2 entries; corpus-mined **20382**,
12921 segmented and linked; dictionary **42838**; queue **0** at the
esp-273 thresholds.

**Wp-only rejection trend**: 4.0% (b33, 32..28 wp), 4.9% (b34, 28..25),
8.2% (b37, 44..22), 10.3% (b38, 22..20). Probe after b38: `--wp-only 18`
568, `--wp-only 15` 1748. Other buckets: `capitalised` 3133, `foreign`
1984, `participle` 16604.

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
- **Next batches**: phase 2 (esp-i9h) lowered the broad tier to 2
  sources; that tier is **exhausted** after batch 27. esp-jpn lowered the
  mixed (1 lit + >= 5 wp) and wp-only (>= 25 wp) tiers. The mixed tier is
  exhausted after batch 30; batch 34 emptied the phase-2b queue. Phase 2c
  (esp-273; demonym pass esp-6w3): mixed to 1 lit + >= 3 wp, then wp-only to >= 20 wp
  (probe table above). The
  *capitalised* bucket (3254) waits on a names policy.

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
