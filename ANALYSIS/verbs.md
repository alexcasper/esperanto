# Which verbs the corpus uses

**Verb frequency is the first measure in this project that survives the author
test.** Every one of fifteen authors puts `esti` first; mean pairwise rank
agreement on the verbs they all use is rho = +0.66 over 105 author pairs. The
diachronic study found the opposite for every rate it tried — each was carried
by whoever wrote most — so the contrast is the point. This ranking is a fact
about Esperanto as the corpus uses it, not about Vallienne or Luyken.

Reproduce with:

```bash
python3 tools/verb_frequency.py --top 30 --tense   # the ranked list
python3 tools/verb_frequency.py --affixes          # the design claim, measured
python3 tools/verb_frequency.py --audit            # what the gate admits and refuses
python3 tools/verb_frequency.py --by-author        # is it the language or the writer
```

## The list

808,711 verb tokens over 240 files, 11,386 distinct verbs.

| rank | verb | tokens | share | cumulative | commonest forms |
|---|---|---|---|---|---|
| 1 | `esti` | 105,336 | 13.03% | 13.0% | pres 51% past 30% |
| 2 | `povi` | 22,603 | 2.79% | 15.8% | pres 48% past 22% cond 15% |
| 3 | `diri` | 21,801 | 2.70% | 18.5% | past 59% pres 14% |
| 4 | `havi` | 13,958 | 1.73% | 20.2% | pres 48% past 26% |
| 5 | `fari` | 12,830 | 1.59% | 21.8% | past 29% inf 28% |
| 6 | `vidi` | 11,007 | 1.36% | 23.2% | past 37% pres 20% |
| 7 | `devi` | 10,522 | 1.30% | 24.5% | pres 64% past 19% |
| 8 | `voli` | 9,707 | 1.20% | 25.7% | pres 51% past 22% |
| 9 | `scii` | 8,498 | 1.05% | 26.7% | pres 60% past 19% |
| 10 | `veni` | 7,872 | 0.97% | 27.7% | past 36% pres 21% |

`esti` alone is an eighth of every verb in the corpus, and more than the next
four combined. After that the curve falls away fast and then flattens:

| | share of verb tokens |
|---|---|
| top 10 | 27.7% |
| top 50 | 45.0% |
| top 100 | 55.5% |
| top 500 | 81.4% |
| top 1000 | 89.9% |

**1,009 verbs — 8.9% of the distinct verbs — cover 90% of verb tokens**, and
3,994 verbs (35.1%) occur exactly once. An ordinary Zipf shape, which is worth
saying plainly: Esperanto is a constructed language, and one of the things this
measures is that its use is not constructed. Nobody planned that distribution.

## The design claim, measured

Esperanto's case is that a small root inventory plus productive affixes covers
the language. `--affixes` tests it directly by counting verbs that reduce to a
*separately listed* verb by stripping verbal affixes — `ekvidi` → `vidi`,
`plibonigi` → `bonigi`.

| | derived | of total |
|---|---|---|
| distinct verbs | 6,880 | **60.4%** |
| verb tokens | 57,334 | **7.1%** |

**The affix machinery generates most of the vocabulary and carries little of
the running text.** Six in ten distinct verbs are built rather than listed, but
they account for one token in fourteen. Derived verbs are numerous and rare;
simple verbs are few and constant. The productivity is real, and it lives
almost entirely in the tail.

The affixes doing the work, by token: `-iĝ-` 8,557, `-ig-` 6,739, `ek-` 6,625,
`-ad-` 5,800, `for-` 4,624, `al-` 4,287, `re-` 4,190, `el-` 3,408, `mal-`
2,376. The transitivity pair `-ig-`/`-iĝ-` leads, and `-iĝ-` leads `-ig-`,
which is the reverse of what a grammar's presentation order suggests.

## Mood tracks meaning, cleanly

The overall form mix reflects a corpus that is mostly narrative fiction:

| form | tokens | share |
|---|---|---|
| past | 274,872 | 34.0% |
| present | 210,263 | 26.0% |
| participle | 109,121 | 13.5% |
| infinitive | 107,310 | 13.3% |
| future | 43,988 | 5.4% |
| imperative | 40,316 | 5.0% |
| conditional | 22,841 | 2.8% |

Per verb, the distribution is not noise around that average — it is predictable
from what the verb means. Taking the top 120 verbs and asking which lean
hardest on each form:

| form | the verbs that lean on it |
|---|---|
| **imperative** | `pardoni` 57%, `aŭskulti` 35%, `lasi` 26%, `permesi` 24%, `memori` 19%, `helpi` 14% |
| **present** | `ekzisti` 64%, `devi` 64%, `ami` 63%, `scii` 60%, `bezoni` 59%, `opinii` 57% |
| **past** | `ekkrii` 88%, `respondi` 76%, `komenci` 69%, `demandi` 68%, `decidi` 62%, `diri` 59% |
| **conditional** | `povi` 15%, `voli` 10%, `deziri` 10%, `devi` 9%, `konsenti` 7% |

Four coherent classes, and none of them was chosen in advance. The imperative
verbs are the verbs of polite request — *pardonu* is more than half of every
use of `pardoni`, because it is how one says sorry. The present-leaning verbs
are stative and modal, things that are the case rather than things that happen.
The past-leaning verbs are the machinery of narration: someone cried out,
answered, asked, began. The conditional belongs almost entirely to the modals.

Compound tenses, which GRAMMAR §6.3 says are rarer than their prominence
suggests, are **14,262 of 576,866 finite verbs — 2.47%**.

## The gate, and what it caught

A token counts as a verb only when the infinitive it reduces to is vouched for.
The ending cannot do this job, though Esperanto's reputation says it can:

| shape | tokens | the twelve commonest |
|---|---|---|
| `-i` | 111,571 | mi, li, vi, pri, ili, ŝi, ĉi, ni, pli, ĝi, oni, i |
| `-u` | 33,157 | kiu, tiu, ĉu, unu, nu, du, ĉiu, iu, estu, neniu, plu, diru |

Pronouns, prepositions, correlatives and numerals. Only two of those
twenty-four are verbs. So the tool works in four tiers, reported separately
because they carry different confidence:

| tier | tokens | distinct | test |
|---|---|---|---|
| listed | 697,354 | 3,455 | a dictionary entry with `pos: verb` |
| derived | 57,334 | 6,880 | reduces by verbal affixes to one |
| root-listed | 54,023 | 1,051 | Rule 6: the stem is a headword under `-o`, `-a` or `-e` |
| unconjugated | 4,573 | — | root-listed, but the corpus never inflects it — dropped |
| rejected | 30,941 | — | none of the above |

The audit found two failure classes that nothing else would have:

**Adverbs that look like participles.** `subite` ("suddenly") and `rilate`
("regarding") end in `-it-e` and `-at-e`, so they parse as participles of
`subi` and `rili`. That is 3,245 tokens, enough to put a non-word in the top
thirty. **Latin and French infinitives.** The corpus contains both, so `fili`,
`ipsi`, `fati` and `mardi` all look like Esperanto infinitives whose stem is
coincidentally a dictionary headword.

One rule removes both: a root-listed lemma must be attested somewhere in the
corpus in a finite or imperative form. **A real verb gets conjugated**; a bare
`-i` or a participle is not enough. Neither `subi` nor `mardi` ever is.

## What the gate found in the dictionary

`povi` and `voli` — the second and eighth commonest verbs in the corpus, 32,310
tokens between them — **are not in the dictionary**. What is there is
`pova (adj) "be able, can"` and `vola (adj) "wish, will"`, both from the
Fundamento's Universala Vortaro, both with plainly verbal glosses filed under
an adjective ending. A reviewer had also seen `povi` during mining and marked
it `inflection — regular participle of povi`, so it was never promoted either.
Two independent failures, on the same two words.

They are not alone. 1,051 lemmas reach the root-listed tier, meaning the
dictionary records a root's noun or adjective but not its verb, while the
corpus conjugates it:

| infinitive | corpus tokens | what the dictionary has instead |
|---|---|---|
| `povi` | 22,603 | `pova` (adj) |
| `voli` | 9,707 | `vola` (adj) |
| `eniri` | 2,628 | `eniro` (noun) |
| `foriri` | 2,153 | `foriro` (noun) |
| `plenigi` | 750 | `plenigo` (noun) |
| `aspekti` | 750 | `aspekte` (adv) |
| `trafi` | 635 | `trafo` (noun) |
| `klopodi` | 470 | `klopodo` (noun) |
| `kapabli` | 459 | `kapabla` (adj) |
| `rajti` | 426 | `rajta` (adj) |

Filed as a bead rather than fixed here: deciding which of 1,051 belong in the
dictionary is review work, not a code change, and `DICT/entries.jsonl` is
rebuilt from reviewed candidates.

## Caveats

1. **The corpus is mostly narrative fiction in translation.** Past tense at 34%
   and `diri` at rank 3 describe that register, not Esperanto in general.
   Kabe is the visible proof: his 1922 *Vortaro* puts `diri` at rank 44 and
   `scii` at 58, because a dictionary does not say "he said". He is also the
   least-agreeing author in the pairwise table, which is the measure working.
2. **The root-listed tier rests on a rule, not a lexicographer.** Its head is
   clean and its tail (1–3 tokens each) mixes genuine adjectival verbs —
   `belas`, `novas`, `afablas` are real Esperanto — with residual noise. It is
   6.7% of tokens and is never merged into the listed count.
3. **`--by-author` covers 15 authors with 5,000+ verb tokens.** That is enough
   for the agreement statistic and not enough to say anything about change over
   time; the diachronic study explains why the dated corpus cannot support that
   for verbs either.
4. The 30,941 rejected tokens are dominated by proper names (`vinicius` 910,
   `petronius` 574) and English (`this` 420), which is the gate working.
