# Which Esperanto verbs take an object

**The `-ig-`/`-iĝ-` pair does exactly what the grammars say, and the corpus
shows it with a clarity nothing else in this project has matched:** across 17
pairs where both forms are common enough to measure, the `-ig-` form takes a
direct object in 55–83% of its clauses and the `-iĝ-` form in 0–9%. Mean gap
**72.1 points, every pair in the predicted direction, none reversed**.


Transitivity is the hardest thing about Esperanto verbs for a learner, and
`DICT/entries.jsonl` records none of it. PIV marks verbs `tr.` or `ntr.` by
lexicographic assertion. This measures it.

```bash
python3 tools/transitivity.py --calibrate    # the gate: does the measure work
python3 tools/transitivity.py --pairs        # -ig- against -iĝ-
python3 tools/transitivity.py --top 40       # the ranking
python3 tools/transitivity.py --audit        # what got counted as an object
```

698,315 verb clauses over 240 <!--= sources() --> sources; 210,387
carried an object.

## The calibration is the whole argument

A transitivity measure that has not been shown to discriminate is a number
generator. So before anything else, twelve verbs whose transitivity is not in
dispute against twelve that are equally not in dispute:

| expected transitive | | expected intransitive | |
|---|---|---|---|
| `preni` | 75.7% | `iri` | 6.3% |
| `meti` | 75.8% | `fali` | 5.0% |
| `havi` | 73.1% | `veni` | 3.6% |
| `doni` | 67.7% | `esti` | 1.7% |
| `trovi` | 67.2% | `sidi` | 1.6% |
| `porti` | 67.1% | `stari` | 1.6% |
| `fari` | 63.2% | `dormi` | 1.3% |
| `vidi` | 50.4% | `kuŝi` | 1.2% |
| `legi` | 45.3% | `resti` | 1.2% |
| `aŭdi` | 42.3% | `morti` | 1.1% |
| `kompreni` | 39.6% | `okazi` | 1.0% |
| `skribi` | 34.0% | `aperi` | 0.5% |

**Lowest transitive 34.0%, highest intransitive 6.3%.** No overlap, and a
28-point gap between the two lists. Every number below rests on that.

The transitive verbs sit well below 100% because a transitive verb is not
obliged to take an object in every clause — *li skribis al mi*, *ĉu vi
komprenas?* — so the measure is a propensity, not a category. Read the ranking,
not the absolute value.

## `-ig-` against `-iĝ-`

The affixes exist to change transitivity: `-ig-` makes a verb causative and
transitive, `-iĝ-` makes it inchoative and intransitive. Both forms of the same
root, side by side:

| root | `-ig-` form | | `-iĝ-` form | |
|---|---|---|---|---|
| plen- | `plenigi` | 83.4% | `pleniĝi` | 0.9% |
| pligrand- | `pligrandigi` | 81.4% | `pligrandiĝi` | 2.6% |
| sid- | `sidigi` | 79.7% | `sidiĝi` | 1.1% |
| dis- | `disigi` | 79.4% | `disiĝi` | 1.1% |
| — | `igi` | 77.7% | `iĝi` | 0.3% |
| kuŝ- | `kuŝigi` | 80.0% | `kuŝiĝi` | 2.9% |
| maltrankvil- | `maltrankviligi` | 76.2% | `maltrankviliĝi` | 0.9% |
| liber- | `liberigi` | 77.2% | `liberiĝi` | 2.0% |
| star- | `starigi` | 75.6% | `stariĝi` | 1.4% |
| efektiv- | `efektivigi` | 74.1% | `efektiviĝi` | **0.0%** |
| trankvil- | `trankviligi` | 74.1% | `trankviliĝi` | **0.0%** |
| kontent- | `kontentigi` | 74.1% | `kontentiĝi` | 0.8% |
| disvast- | `disvastigi` | 73.3% | `disvastiĝi` | 2.7% |
| kviet- | `kvietigi` | 72.2% | `kvietiĝi` | 2.9% |
| kun- | `kunigi` | 67.6% | `kuniĝi` | 1.6% |
| vid- | `vidigi` | 54.8% | `vidiĝi` | 1.6% |
| sci- | `sciigi` | 55.8% | `sciiĝi` | 9.0% |

`efektiviĝi` and `trankviliĝi` take an object in **none** of their 163 and 168
clauses. `sciiĝi` at 9.0% is the least clean, and for a reason worth naming: it
governs `pri` rather than the accusative (*sciiĝi pri io*), so most of its 9%
is residual noise rather than an object.

This is the strongest single result in the project, and it is worth being clear
about what makes it strong. It is not the size of the gap. It is that the
prediction was made by the grammar before the measurement, applies to 17
independent roots, and is not carried by any one of them — the smallest gap,
`sciigi`/`sciiĝi`, is still 47 points.

## The ranking

Most transitive of the verbs with 400+ clauses: `turni` 85.6%, `plenigi`
83.4%, `levi` 82.6%, `etendi` 81.4%, `fermi` 79.6%, `devigi` 79.1%, `kisi`
79.0%, `ĵeti` 78.4%, `premi` 78.1%, `igi` 77.7%.

Least: `brili` **0.0%** over 645 clauses, `naskiĝi` 0.3%, `konsisti` 0.4%,
`aŭdiĝi` 0.4%, `finiĝi` 0.4%, `aperi` 0.5%, `aspekti` 0.6%, `perei` 0.6%,
`erari` 0.6%, `vekiĝi` 0.6%, `montriĝi` 0.7%, `agi` 0.7%.

The bottom of the list is a roll-call of `-iĝ-` verbs — `naskiĝi`, `aŭdiĝi`,
`finiĝi`, `vekiĝi`, `montriĝi`, `troviĝi`, `leviĝi`, `fariĝi` — mixed with the
verbs that are intransitive without needing an affix to say so. Nothing in the
bottom twenty is a verb anyone would call transitive.

## What wears an accusative and is not an object

Three things, and each was found by reading what the measure was counting
rather than by reasoning about it in advance.

**Directional.** `en la domon`, `sur la tablon`, `iri Parizon`. The accusative
marks motion toward. Excluded where a place preposition governs the noun, and
for anything in `-en` (`hejmen`, `tien`, `supren`), which is an adverb plus the
directional `-n` and never an object. 10,848 exclusions.

**Adverbial.** `la tutan tagon`, `tri fojojn`, and the date construction
`okazis la okan de Majo`, where the noun is elided entirely and only an
accusative ordinal is left. That last one had `okazi` — a verb that cannot take
an object — reading 6.4%, all of it dates. 7,345 exclusions.

**Another verb's object.** `li iris vidi la plimulton`; `ŝi sidis aŭskultante
la horloĝojn`; `ĝi estos ĉirkaŭinta la terglobon`; `lasis ilin fali`. An
infinitive or participle between a verb and an accusative owns that accusative,
and in the causative construction the accusative sits between the finite verb
and its infinitive complement and belongs to the finite one. Without these
rules `esti` inherited the object of every participle it fronted. Fixing it
moved `esti` from 8.3% to 1.7%, `okazi` from 6.4% to 1.0% and `dormi` from 3.0%
to 1.3%.

And a fourth, which is not about syntax at all: **the obvious accusative test
is 25% function words.** Matching any `-n` after a vowel that can carry one —
the textbook description — makes `en` the commonest accusative in the corpus at
16% of all matches, followed by `kun`, `nun`, `jen`, `tamen`, `sen`, plus names
like `Aslaksen`. Only `-on/-ojn/-an/-ajn`, the accusative pronouns and the
`-un` correlatives are counted here.

That last discovery reached back into the previous study. `tools/diachronic.py`
used exactly the textbook regex for its **control** — the measure whose whole
job was to confirm that periods differ only by date. It read −0.35 (p=0.03), a
significant trend in a quantity fixed by the Fundamento, and
`ANALYSIS/diachronic.md` accordingly warned readers to treat any rho below 0.35
as noise. With the accusative counted properly the control reads **−0.07
(p=0.66)** — flat, as it always should have been. The noise floor was an
artefact of counting the preposition *en*. See that document, which has been
corrected.

## The floor, and what is still wrong

`iri` at 6.3% is the highest intransitive and the honest limit of the method.
Its hits are the **bare directional accusative** — *iri Parizon*, *iri sian
vojon*, *iros vian vojon* — motion toward a destination with no preposition to
mark it. Catching those needs to know that Parizo is a place and vojo a path,
which needs a lexicon this project does not have; and any rule of the form "a
motion verb's accusative is directional" would assume the answer it is meant to
measure. So it stays, it is named, and 6% is the floor below which a difference
between two verbs means nothing.

Three further limits worth stating:

1. **Clause boundaries are punctuation and conjunctions**, which over-splits
   (*la grandan, belan domon*) and under-splits where a writer omits a comma.
   Over-splitting loses objects, so the measure is biased down, uniformly.
2. **Propensity is not category.** `skribi` at 34% is transitive; it simply
   often appears without an object. A verb's position in the ranking is
   informative; the number by itself is not a transitivity verdict.
3. **The corpus is period material and mostly translation.** A translator's
   argument structure follows the source language more closely than an original
   author's would.

## Written into the dictionary

`DICT/entries.jsonl` now carries the measurement on **662 of its 4,169 verb
entries** — 366 transitive, 155 intransitive, 141 uncertain — with the evidence
attached:

```json
"transitivity": {"verdict": "intransitive", "object_share": 0.003,
                 "clauses": 383, "basis": "corpus"}
```

Twelve `-ig-`/`-iĝ-` pairs have both halves annotated and both decided —
`liberigi` 0.77 against `liberiĝi` 0.02, `efektivigi` 0.74 against
`efektiviĝi` 0.000. Fewer than the 17 measurable pairs, because several
`-ig-` forms are not dictionary entries at all: `plenigi` is absent, which is
the root-listed gap of `ANALYSIS/verbs.md` showing up from another direction.

That is `komenciĝi`. Its partner `komenci` does **not** come out transitive —
it measures 18.4% over 3,344 clauses and lands in `uncertain`, for a reason
worth knowing: **46% of `komenci`'s occurrences are followed immediately by an
infinitive** — *li komencis demandi*, *komencis verŝi la akvon* — where the
object belongs to the second verb. `komenci` mostly takes a verb complement,
not a noun object.

That is the fourth limit of the measure, and the one that shapes the
`uncertain` band: **it counts nominal objects only.** `povi` 14.6%, `devi`
12.6%, `voli` 18.5%, `kuraĝi` 16.7%, `provi` 26.9%, `deziri` 25.0% are all the
same shape. None of them is intransitive, and the 5% floor is low enough that
none is called intransitive — but none is called transitive either, correctly,
because the thing they take is not a noun. `uncertain` is doing real work here:
it is picking out a third class rather than confessing ignorance.

The thresholds are set **inside** the gap the calibration set shows, not at its
edges: transitive at ≥40% and intransitive at ≤5%, against an observed gap of
6.3% to 34.0%. So `skribi` (34.0%), `kompreni` (39.6%), `iri` (6.3%) and `fali`
(5.0%) all come out `uncertain` and go to a human. Putting the cut-offs at the
edges of the gap would classify the entire calibration set correctly and would
be fitting the thresholds to the answer. Nothing is misclassified under these;
four of twenty-four are declined, which is the point.

`uncertain` is written rather than left blank, because a verb the corpus was
asked about and did not settle is a different thing from a verb nobody
measured. The remaining 84% of verb entries appear in fewer than 100 clauses
and carry no field at all rather than a guess.

One check the thresholds were not tuned against, since the `-ig-`/`-iĝ-` verbs
were never in the calibration set: of 58 `-ig-` verbs, 53 come out transitive
and 5 uncertain; of 49 `-iĝ-` verbs, 47 intransitive and 2 uncertain. **No
contradictions in either direction** across 107 verbs. The two uncertain
`-iĝ-` forms are `sciiĝi` (9.0%, governs *pri*) and `foriĝi` (11.0%, picks up
directional accusatives), both of which are the known limits doing what they
do rather than surprises.

The field is derived data. `promote_lemmas.py --rebuild` re-promotes
corpus-mined entries and drops it from them, so `tools/annotate_transitivity.py
--apply` belongs after every rebuild; it is idempotent.

---

*The figures in this document are a snapshot of the analysis run it describes,
dated 2026-09-06, and are not live counts — updating them silently would
rewrite a finding rather than maintain a total. Figures elsewhere that are
meant to track the data carry an inline check marker and are verified by
`python3 tools/check_figures.py`; see `DICT/README.md` for the mechanism.*
