# Does this corpus show Esperanto changing over time?

**Not yet, and the reason is structural rather than a matter of finding better
measures.** Each decade in the dated corpus is carried by one to three authors,
so author and period are confounded by construction. Every candidate trend
tested here dissolves when the period's dominant writer is held out. This
document records the method, the negative results, and what would have to
change for the question to become answerable.

Reproduce with:

```bash
python3 tools/date_sources.py --write     # -> RAW/DATES.tsv
python3 tools/diachronic.py --hold-out
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

Three dating rules were tested and two were rejected on measurement:

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

## What the dated corpus looks like

2.3M tokens over ten decades, and lumpy:

| period | tokens | largest single contributor |
|---|---|---|
| 1880s | 23,684 | Zamenhof 70% |
| 1890s | 70,281 | Homer (Kofman's *Iliado*) 43% |
| 1900s | 826,270 | Vallienne 33% |
| 1910s | 241,882 | Luyken 37% |
| 1920s | 662,206 | 24% |
| 1930s | 268,899 | Sienkiewicz (Zamenhof's *Quo vadis*) 72% |
| 1950s | 70,264 | one source |
| 1990s | 9,377 | one source |
| 2000s | 2,261 | one source |
| 2020s | 56,153 | one source |

The 1940s, 1960s and 1970s are absent. The 1990s and 2000s are a few thousand
tokens each. Only the 1900s–1930s have enough material from enough hands to
support any claim, and even there one writer carries a quarter to three
quarters of each decade.

## The control, and what it caught

`accusative` — tokens ending in `-n` after a vowel that can carry one — is
measured as a **control, not a finding**. The accusative is fixed by the
Fundamento and should not trend. If it does, the periods differ by something
other than date and every other figure is suspect.

It earned its place immediately. The 1980s came out at 565 per 10,000 against
850–1,040 everywhere else — a 40% drop in something that cannot drop. The cause
was the Downes textbook: English-language prose *about* Esperanto, already on
the mining exclusion list and never removed from this analysis. Most of its
tokens are English. With it excluded the control is flat across every period
(835–1,040), which is the evidence that the remaining comparisons are at least
measuring Esperanto.

## Three candidate trends, three null results

| feature | why it was chosen | result |
|---|---|---|
| `ĥ` rate | the best-known change in written Esperanto — *anarĥio* → *anarkio*, *ĥemio* → *kemio* | **no trend.** 3.4, 55.8, 7.0, 5.4, 9.3, 3.8, 2.0 … The 1890s spike is Kofman's *Iliado* and its Greek names — Aĥilo, Aĥajo — and falls from 55.8 to 17.6 when Homer is held out. Subject matter, not date. |
| `-ujo` vs `-io` for countries | GRAMMAR §6.1 records that `-ujo` dominates without asking when that stops being true | **no trend.** Every decade to 1920 is 95–100% `-ujo`. The 1930s reads 48%, which looks like a shift until you look: 61 of its 64 `-io` forms are in one book, Lanti's *Naciismo* (1930). Holding out the decade's largest contributor *strengthens* the apparent effect to 93% `-io`, because that removes *Quo vadis* and leaves Lanti alone. |
| compound tenses | GRAMMAR §6.3 records these are rarer than grammars suggest | **no trend.** Swings between 96 and 380 per 10,000 finite verbs with no direction, and moves by a third or more under hold-out. |

The Lanti result is worth stating positively, because it is the one thing here
that does replicate: **`-io` versus `-ujo` tracks the author, and in this case
plausibly the author's politics.** Lanti founded the anationalist movement, and
the international `-io` form is the one a reformist would reach for while
Zamenhof's *Quo vadis*, printed four years later, uses `-ujo` 32 times and
`-io` never. That is a real observation about Esperanto. It is not an
observation about time.

## What would make this answerable

The binding constraint is authors per period, not tokens per period and not
better statistics.

1. **More independent authors per decade.** Three or four writers per period
   would let author be held out without exhausting the data. The 1900s already
   has this; nothing after 1940 does.
2. **Fill 1940–1990.** Currently one source between 1939 and 1990. Post-war
   Esperanto is where `-io` is generally said to have won, so the corpus is
   missing precisely the period the best-known change happened in.
3. **Date the translations.** 76 sources name a translator and are undated
   because the text only dates the original. Translator identity dates them,
   and Wikidata covers people far better than it covers their translations —
   Edwin Grobe (1927–2015) and H. J. Bulthuis (1865–1945) both resolve. That
   is the highest-yield next step.
4. **Separate original Esperanto from translated Esperanto** before comparing
   anything. A translation's register follows its source text, and the corpus
   is majority translation.

Until at least the first two hold, figures from `tools/diachronic.py` should be
read as descriptions of particular books and their authors, and not as
evidence about the language.
