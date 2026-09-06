# Does this corpus show Esperanto changing over time?

**For one feature out of three, yes, and the evidence is stronger than a
coefficient: no text written before 1911 uses `-io` for a country name.**
Thirty texts, thirteen hands, 543 country names, not one `-io`. From 1911 the
form appears and never disappears. The other two candidate features are null,
and one of them looked significant until the unit of analysis was fixed.

The earlier version of this document reported three null results. Two of those
still stand; the third was wrong, and so was one of the dates it rested on.
What changed was not the statistics but the unit: decades let a single book be
a period. See *Three units, three answers*.

Reproduce with:

```bash
python3 tools/date_sources.py --write     # -> RAW/DATES.tsv
python3 tools/diachronic.py --by-text     # each text one observation
python3 tools/diachronic.py --by-author   # each author one observation
python3 tools/diachronic.py --stem aŭstr  # one stem, text by text
python3 tools/diachronic.py --hold-out    # the decade table, for comparison
```

## Dating is the hard part, and it is where the errors are

Two dates exist for every text and only one of them is useful here.

The corpus records **edition** dates — the year of the printing that was
scanned. Language change needs **composition** dates. For a novel printed the
year it was written these agree; for anything else they can be decades apart,
and the divergence is concentrated in exactly the largest sources.
*El verkoj de E. Lanti* is filed 1982 and collects essays from 1922; Lanti died
in 1947. At 250k tokens, dating it 1982 would put 1920s prose in the 1980s
bucket and bend a trend on its own.

Four dating rules were tested and two were rejected on measurement:

| evidence | verdict |
|---|---|
| Gutenberg's `Original publication:` line | **kept.** Gives the Esperanto edition's publisher and year — 'Paris: Presa Esperantista Societo, 1904'. Unambiguous, 12 sources. |
| year in a Vikifontaro scan's filename | **kept for single works.** Unambiguous about the edition; for a collection it dates an anthology whose contents are older. |
| earliest plausible year in the text | **rejected for translations, kept for originals.** Against 23 independently dated sources it got 11 wrong, several by 30–60 years. |
| Wikidata title lookup | **rejected.** Of 10 well-known Esperanto works, 1 matched anything at all, and that match was a Polish film rather than the translation. Wikidata covers people well and obscure Esperanto translations badly. |

The translation rule matters most. **A translation's in-text year dates the
original, not the Esperanto.** Odd Tangerud's Ibsen translations carry 1888,
1890, 1892, 1894, 1895 and 1896 on their title pages and were made in the
1990s. Before that rule he was 43% of the corpus's "1890s". Where a source
names a translator, the in-text year is now inadmissible and the text stays
undated unless something dates the Esperanto itself.

The cost is coverage: **46% of the corpus by bytes is dated** — 25 sources at
high confidence, 55 at medium. `RAW/DATES.tsv` records the basis and confidence
for every source, and the undated ones say why.

### Four dating bugs, and the one that nearly produced a finding

Each of these was found by looking at *why* a number was what it was, and each
had been silently in place through the previous round of analysis.

**A birth year is not a publication year.** The in-text rule takes the earliest
plausible year in a text's first 40 lines. František Omelka's *La Alaska
stafeto* opens `Mi naskiĝis en la jaro 1904` — his birth year — and came out
dated 1904. It was written in 1951. Because his other book is dated 1937, the
pair read as **one author moving from `-ujo` to `-io` over 33 years**: the
single strongest form of diachronic evidence available, within-author change,
and it was an artefact. Corrected, the pair runs the other way — 1937 `-io`,
1952 `-ujo` — and says nothing. Years standing next to a birth or death word
are now discarded. Exactly one file in the corpus has this shape, and it was
the one that mattered.

**An accent dropped two authors.** The Vikifontaro author regex matched an
Esperanto-alphabet whitelist, so `Molière` and `Prévost` failed it and were
filed `(unattributed)` — the exact collapse the regex exists to prevent. It now
matches any letter.

**One writer under two names is two writers to a hold-out.** Vikifontaro
filenames give a bare surname and Gutenberg headers give a full name, so
`Luyken` and `Heinrich August Luyken` were two contributors, as were Bulthuis,
Grabowski and Vallienne. Four writers counted as eight, which is exactly what
the author-pooling test exists to prevent. A surname now folds into the full
name where exactly one full name matches it. This one surfaced while building
`tools/verb_frequency.py`, whose own author breakdown listed both Luykens side
by side. (Merging them moved the accusative control from −0.27 to −0.35, which
looked at the time like a reason to distrust the whole analysis. The control
was simply broken; see *The control behaves*.)

**Twenty-six issues of one magazine are not twenty-six writers.** *The
Esperantist* (1903–05) is 26 separate Gutenberg files with no author header.
Pooled as `(unattributed)` they inflated the count of independent pre-1911
hands and made the magazine impossible to hold out. Issues of a periodical are now attributed
to the periodical, which is the conservative direction: it can only weaken a
claim about author diversity, never manufacture one.

## What the dated corpus looks like

2.3M tokens over ten decades, and lumpy:

| period | tokens | largest single contributor |
|---|---|---|
| 1880s | 23,684 | Zamenhof 70% |
| 1890s | 70,281 | Homer (Kofman's *Iliado*) 43% |
| 1900s | 795,540 | Vallienne 34% |
| 1910s | 241,882 | Luyken 37% |
| 1920s | 662,206 | Bulthuis 22% |
| 1930s | 268,899 | Sienkiewicz (Zamenhof's *Quo vadis*) 72% |
| 1950s | 100,994 | Rossetti 70% |
| 1990s | 9,377 | one source |
| 2000s | 2,261 | one source |
| 2020s | 56,153 | one source |

The 1940s, 1960s, 1970s and 1980s are absent. The 1990s and 2000s are a few
thousand tokens each. Only the 1900s–1930s have enough material from enough
hands to support any claim, and even there one writer carries a fifth to three
quarters of each decade.

## Three units, three answers

This is the methodological result, and it is worth more than any individual
feature. The same four measures, over the same texts, under three units of
analysis:

| feature | by decade | by text | by author | verdict |
|---|---|---|---|---|
| `ĥ` rate | swings, dies under hold-out | −0.09 (p=0.48) | −0.12 (p=0.45) | **null everywhere** |
| compound tenses | swings, no direction | **−0.35 (p=0.003)** | −0.13 (p=0.44) | **an author effect** |
| `-ujo` share | 100% until 1910, 48% in the 1930s | −0.45 (p=0.001) | **−0.57 (p=0.003)** | **survives** |
| `accusative` *(control)* | flat, 922–1081 | +0.22 (p=0.07) | −0.07 (p=0.66) | **behaves** |

`rho` is Spearman's; `p` is a permutation test — the years shuffled against the
values 20,000 times — because with 26 authors an asymptotic p would assume more
than we know.

**Compound tenses are the cautionary case.** At text level they are the
second-strongest result in the table and comfortably significant. Pooling each
author's texts into one observation takes rho from −0.35 to −0.13 and p from
0.003 to 0.44. Nothing about the language changed between those two lines; what
changed is that an author with six dated texts stopped counting as six pieces
of evidence. In a corpus where author and period are confounded by
construction, the text is not an independent observation and the by-text row is
the wrong row to read.

**The control behaves, and it took two fixes to find that out.** The accusative
is fixed by the Fundamento and cannot trend. It now reads −0.07 (p=0.66) at
author level and 922–1081 per 10,000 across every decade with real material,
which is what a control is supposed to look like.

It read −0.35 (p=0.03) until the measure itself was checked. The obvious test
for an accusative — a word ending in `-n` after a vowel that can carry one —
turns out to be **25% function words** on this corpus. Its single commonest
match is `en`, at 16% of everything it caught, followed by `kun`, `nun`, `jen`,
`tamen` and `sen`. The control was substantially measuring how often a period's
authors wrote the preposition *en*. Counting only real accusatives —
`-on/-ojn/-an/-ajn`, the accusative pronouns, the `-un` correlatives, and
nothing in `-en`, which is an adverb plus the directional `-n` — flattens it.

This matters twice over. It removes the noise floor an earlier version of this
document set at 0.35 and warned readers to measure every claim against: the
floor is not there, and `ujo-share` at −0.57 stands clear of a control that is
flat rather than of one that misbehaves. **And it is a warning about controls
in general.** A control only licenses the other measurements if the control
itself is measuring what its name says. This one had a plausible name, a
plausible regex, and caught the wrong words for two rounds of analysis. It was
found by building an accusative test carefully for a different question
entirely — see `ANALYSIS/transitivity.md`.

The control earned its place before that, too: the 1980s came out at 565
accusatives per 10,000 against 850–1,040 everywhere else — a 40% drop in
something that cannot drop. The cause was the Downes textbook,
English-language prose *about* Esperanto, already on the mining exclusion list
and never removed from this analysis.

## The one positive result: `-ujo` → `-io`

GRAMMAR §6.1 records that `-ujo` dominates the corpus without asking when that
stops being true. It stops being true in 1911, and the strongest evidence is
categorical rather than a coefficient.

```
first attestation of -io, split at 1911:
   before  30 texts, 13 hands,  543 country names,  0 use -io
   after   30 texts, 20 hands,  860 country names, 10 use -io
   permutation p (one-sided, text-level) = 0.0005
```

**A rate is carried by whoever writes most; an absence across thirteen hands is
not.** That is why this claim survives the author confound where the rate-based
ones do not. The pre-1911 half includes 16 issues of *The Esperantist*, a
magazine with dozens of contributors; eleven named writers — Devjatnin,
Stankiević, Fruictier, Zamenhof, Vallienne, Kotzebue, Motteau, Anton, Privat,
and the Molière and Prévost translations, which the Vikifontaro filenames
attribute to their original authors; and one `Various` anthology. None of them
writes `Anglio`. From 1911 ten texts do.

The rate trend agrees. At author level rho = −0.57 (p=0.003), and it survives
the harshest available robustness check: dropping the **two authors it leans on
most** — found by refitting without every pair, not by picking names — leaves
rho = −0.45 (p=0.030).

Three things this does **not** show, all of which the table makes plain:

| author | mean year | `-ujo` share |
|---|---|---|
| Devjatnin, Stankiević, Grabowski, Fruictier, *The Esperantist*, Zamenhof, Molière, Vallienne, Kotzebue, Prévost, Anton, *Various* | 1892–1908 | 100% |
| Ned Katryn | 1912 | 100% |
| Zakrzewski | 1913 | 92% |
| Edmond Privat | 1915 | 97% |
| Heinrich August Luyken | 1918 | 100% |
| Kabe | 1922 | 98% |
| *Literatura Mondo* | 1922 | 97% |
| Tojosato Tooguu | 1924 | 100% |
| **Lanti** | **1930** | **0%** |
| H. J. Bulthuis, Sienkiewicz, Rossetti | 1930–1950 | 100% |
| *(unattributed)* | 1939 | 94% |
| František Omelka | 1944 | 91% |
| Jorge Camacho | 1993 | 83% |

1. **It is not a completed change.** Eighteen of twenty-six authors are at
   100% `-ujo`, including every one of them after 1930 except Omelka and
   Camacho. Across
   the whole dated corpus `-io` is 91 tokens against 1,312 `-ujo`. What the
   corpus shows is a form entering, not a form winning.
2. **It is not evenly spread.** Eight of the ten `-io` texts are movement or
   reference prose — *Germana Esperantisto*, *Historio de Esperanto*, *Vivo de
   Zamenhof*, *Dokumentoj de Esperanto*, Kabe's *Vortaro*, Lanti's *Naciismo* —
   and the register where the form was being argued for is the register it
   appears in first. Two consecutive issues of *Literatura Mondo* split on it.
3. **Lanti is still the loudest voice and still not the finding.** He is 61 of
   the 91 `-io` tokens and the only author at 0% `-ujo`. He founded the
   anationalist movement, and the international `-io` is the form a reformist
   would reach for. Notably, removing him barely moves rho — with 21 authors
   tied at 100% he is one rank among many — which is why the earlier hold-out
   test, which dropped a *period's* largest contributor, could not settle this
   either way.

### What the Austria stem shows, and why it was checked

`aŭstr` was the one stem whose `-io` forms survived holding Lanti out, so it
was traced text by text on the suspicion that `Aŭstrio` vs `Aŭstrujo` might be
**referential rather than linguistic** — Austria-Hungary before 1918 against
the post-1918 republic, which would be a fact about Europe and not about
Esperanto.

```
1904 pg-37977          -ujo=2  -io=0      1921 pg-47259        -ujo=4  -io=0
1908 pg-52556          -ujo=1  -io=0      1921 pg-57184        -ujo=1  -io=5
1911 ia-dlibra.49099   -ujo=0  -io=5      1922 pg-52064        -ujo=1  -io=0
1912 pg-55574          -ujo=7  -io=0      1922 Kabe Vortaro     -ujo=0  -io=1
1913 Zakrzewski        -ujo=0  -io=7      1937 pg-26099        -ujo=0  -io=3
1920 pg-26359          -ujo=0  -io=1      1952 pg-32480        -ujo=1  -io=0
```

**The referential explanation fails**: `-io` is attested for Austria in 1911 and
1913, seven and five years before the Habsburg monarchy ended, and `-ujo`
continues in 1921 and 1952, well after. Both forms straddle 1918 in both
directions. Whatever separates them, it is not which Austria is meant. (Both
early attestations rest on medium-confidence dates; the 1913 one is a
filename-dated Vikifontaro scan and the 1911 one an uncorroborated in-text
year.)

### The stems, before and after 1911

Per stem, the split is the same shape everywhere it has data at all:

| stem | pre-1911 `-ujo` / `-io` | 1911+ `-ujo` / `-io` |
|---|---|---|
| `angl` | 72 / 0 | 71 / 0 |
| `franc` | 111 / 0 | 90 / 2 |
| `german` | 48 / 0 | 90 / 2 |
| `ital` | 39 / 0 | 47 / 10 |
| `aŭstr` | 3 / 0 | 14 / 22 |
| `brazil` | 2 / 0 | 1 / 11 |
| `uson`, `tuniz`, `argentin`, `aŭstrali` | *never named* | 0 / 29 |

The last row is a trap worth naming: `Usonio`, `Tunizio` and `Argentinio` look
like early `-io` and are not evidence of anything, because the pre-1911 corpus
never mentions those countries in either form. The one country of that kind it
does mention, it writes `Brazilujo`. So the natural mechanism — that `-io` was
already established for countries not named after a people, and spread from
there — is not supported here. Before 1911 this corpus has no `-io` of any
kind.

`angl` is the counter-case and it is honest to leave it in: England is the most
frequently named country in the corpus and it is 100% `-ujo` on both sides of
1911, in every dated text. The change is not uniform across stems.

*Anglio* is not absent from the corpus, though — it is absent from the **dated**
corpus. Over all 240 sources it occurs 26 times, against 240 *Anglujo*. That
gap between the dated and the full corpus is not a flaw in the sample; it is
the finding again, from the other side. The undated sources carrying the `-io`
forms are overwhelmingly the *El verkoj de E. Lanti* volumes, and they are
undated for a good reason — posthumous collections whose printing year says
nothing about when the prose was written, which is the first rule in this
document. Across the whole corpus: 79 of 85 *Francio*, 48 of 59 *Germanio* and
43 of 44 *Rusio* are Lanti.

So the half of the corpus this study had to exclude corroborates its
conclusion rather than threatening it. `-io` in this corpus is one author,
measured two independent ways.

## What would make this answerable

The binding constraint is authors per period, not tokens per period and not
better statistics.

1. **More independent authors per decade.** Three or four writers per period
   would let author be held out without exhausting the data. The 1900s already
   has this; nothing after 1940 does.
2. **Fill 1940–1990.** Currently two sources between 1939 and 1990 — Rossetti
   1950 and Omelka 1952. Post-war
   Esperanto is where `-io` is generally said to have won, and the corpus stops
   just as the change it can see beginning would have run to completion.
   Everything above describes an entry, and the completion is out of reach.
3. **Date the translations.** 76 sources name a translator and are undated
   because the text only dates the original. Translator identity dates them,
   and Wikidata covers people far better than it covers their translations —
   Edwin Grobe (1927–2015) and H. J. Bulthuis (1865–1945) both resolve. That
   is the highest-yield next step.
4. **Separate original Esperanto from translated Esperanto** before comparing
   anything. A translation's register follows its source text, and the corpus
   is majority translation.
5. **Separate literary prose from movement prose.** The `-io` texts are
   disproportionately the second kind, and register is currently confounded
   with date in the same way author is.

Until at least the first two hold, read `--by-author` and never `--by-text`,
and prefer a categorical claim — this form does not occur before this year —
to a rate, because that is the kind of claim in this study that survived
scrutiny best. And check what a control is actually counting before letting it
license anything: this one was 25% function words and said so to nobody for
two rounds.
