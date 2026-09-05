#!/usr/bin/env python3
"""Map step of lemma mining: extract candidate lemmas from one shard of CORPUS/.

Usage:
  python3 tools/mine_lemmas.py --shard I/N [--min-count 2] [--max-citations 3]
  python3 tools/mine_lemmas.py --plan N          # show the shard assignment

Each shard writes exactly one file, DICT/shards/shard-<I>-of-<N>.jsonl, and
reads only the CORPUS/ files assigned to it. Nothing is shared between shards,
so shards can run concurrently — in separate agents, processes or machines —
without coordination. tools/reconcile_lemmas.py performs the reduce.

Shards are packed by file size, largest first into the lightest shard, because
the corpus is lopsided: Originala Verkaro is 1.4 MB and the smallest sources
are a few kilobytes, so round-robin would leave one shard doing most of the
work.

Text that is not Esperanto is skipped before tokenizing, at four scales:
whole files (a foreign-language grammar), single lines (see line_is_foreign,
which reaches a bilingual periodical), spans within a line (see foreign_spans,
which reaches a Latin binomial or a translator's credit in parentheses), and
columns (see foreign_columns, which reaches the Fundamento's five translation
columns without discarding the Esperanto beside them).

Output records are one JSON object per line:

  {"lemma": "...", "kind": "unknown", "count": 12, "pos_guess": "noun",
   "forms": {"vorto": 9, "vortoj": 3},
   "citations": [{"source": "pg-8224.txt", "line": 412, "text": "..."}],
   "verdict": null, "gloss": null, "note": null}

`verdict`, `gloss` and `note` are left null by this script. They are the
judgment a reviewer adds: whether a candidate is a real Esperanto lemma, an
OCR artefact, a proper noun or a foreign word — the part that needs a reader
rather than a regular expression.
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import esperanto  # noqa: E402  (path set above)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORPUS = os.path.join(ROOT, 'CORPUS')
SHARDS = os.path.join(ROOT, 'DICT', 'shards')
LEDGER = os.path.join(ROOT, 'DICT', 'verdicts.jsonl')

# 'grammar' sources are English prose about Esperanto; mining them for Esperanto
# lemmas yields English. PROVENANCE.md marks them; match them by id here.
ENGLISH_HEAVY = {'pg-7787.txt', 'pg-8177.txt', 'pg-16967.txt',
                 # archive.org additions that are English or French prose
                 # about Esperanto, not Esperanto: scored 28-54% recognisable
                 # by tools/score_esperanto_text.py against 90%+ for real
                 # Esperanto, because most of their tokens are not Esperanto.
                 'ia-key_to_the_ekzercaro.txt',
                 'ia-traduction_de_lekzercaro.txt',
                 'ia-esperanto-the-international-language-a-complete-'
                 'textbook-w-j-downes-1982.txt'}

# The Fundamento's multilingual tables put French, German, Russian and Polish
# gloss columns beside the Esperanto, so mining them yields those languages.
MULTILINGUAL = {'wsrc-Fundamento_de_Esperanto_Universala_vortaro.txt',
                'wsrc-Fundamento_de_Esperanto_Grammar.txt',
                # A 61-line index page: no body text, only the title block and
                # the publisher list, which fed 'irgend', 'any', 'przypadek'
                # into the candidate queue.
                'wsrc-Fundamento_de_Esperanto.txt'}

# Not words: the elided article, Roman numerals, and the abbreviations that
# recur across sources (Kabe's subject labels, citation shorthand). Every
# reviewer hit these, and 'l' alone reached 2884 occurrences.
STOPWORDS = {'l', 'ktp', 'ekz', 'prof', 'kop', 'esp', 'fr', 'np', 'ex',
             'zool', 'ĥem', 'med', 'geom', 'fiz', 'bot', 'anat', 'mat',
             'haml', 'kos', 'no', 'nro', 'vol', 'pĝ', 'red', 'ks'}
ROMAN = re.compile(r'^[ivxlcdm]+$')

# Function words of the languages this corpus is mixed with. Every entry was
# checked against the dictionary: several look-alikes are deliberately absent
# because they are Esperanto words in their own right — des ("ju pli, des
# pli"), para ("paired"), jako ("jacket"), plus, por, sur, for, de, ne, la, je,
# da, ili. Each of those has the shape of a foreign word and is not available.
# Bare roots and endings are safe: est, las, not, mit and and are Esperanto
# roots, and is and ist are the past-tense ending and the -ist suffix, which
# the Fundamento lists as headwords. An Esperanto word always carries an
# ending, so these bare forms only ever appear in running text as German or
# English.
FOREIGN_MARKERS = {
    'the', 'and', 'of', 'is', 'was', 'were', 'this', 'that', 'these', 'with',
    'which', 'have', 'has', 'been', 'they', 'their', 'there', 'from', 'not',
    'are', 'you', 'his', 'her', 'its', 'but', 'what', 'when', 'would',
    'der', 'die', 'das', 'dem', 'den', 'und', 'ist', 'sind', 'nicht',
    'ein', 'eine', 'einer', 'einem', 'einen', 'auf', 'aus', 'mit', 'nach',
    'sich', 'sie', 'ihre', 'werden', 'wurde', 'haben', 'auch', 'wie',
    'les', 'une', 'est', 'sont', 'dans', 'pour', 'que', 'qui', 'avec',
    'cette', 'nous', 'vous', 'leur', 'tout',
    'nie', 'jest', 'przez', 'oraz', 'jednak', 'ktory',
    'del', 'las', 'los', 'como', 'esta',
}
FOREIGN_MARKERS -= esperanto.GRAMMATICAL     # never fight the real vocabulary

MIN_LINE_TOKENS = 4
MIN_LINE_KNOWN = 0.5


def recognised(token, roots, words, cache=None):
    """Is this token Esperanto the morphology knows? Memoized.

    Three separate tests ask this of every token in the corpus — the line
    filter, the span filter and classification itself — so the answer is
    computed once per distinct token rather than once per occurrence. Without
    the memo a single shard took seven minutes.
    """
    if cache is None:
        return esperanto.analyse(token, roots, words)[1] != 'unknown'
    hit = cache.get(token)
    if hit is None:
        hit = esperanto.analyse(token, roots, words)[1] != 'unknown'
        cache[token] = hit
    return hit


def line_is_foreign(line, roots, words, cache=None):
    """True if this line is not Esperanto, so nothing on it is a candidate.

    Excluding whole files is too coarse. The sources that flooded the review
    queue are mixed: the dlibra periodical is 70% Esperanto and 6% German, the
    Ekzercaro prints its German, French and English translations beside the
    Esperanto, and even a clean book carries a publisher's address page, a
    quoted passage of Leibniz and a transliterated Russian paradigm. Reviewers
    reported that two thirds of every 320-item queue was foreign words.

    Measured per line the two languages separate almost completely: in
    Originala Verkaro 97.4% of lines are at least 80% recognisable and only 42
    fall below half, and every one of those 42 is furniture, formulae, an
    alphabet table or a foreign quotation. So the rule is a recognisability
    floor, plus a list of foreign function words for lines too short to score.
    """
    tokens = [t for t in esperanto.TOKEN.findall(line) if len(t) > 1]
    if not tokens:
        return False
    lowered = {t.lower() for t in tokens}
    if lowered & FOREIGN_MARKERS:
        # One 'und' or 'the' settles it, and settles the short lines that a
        # ratio cannot: a two-word table cell, a running head, a caption.
        return True
    if len(tokens) < MIN_LINE_TOKENS:
        return False        # too little evidence to judge; let it through
    known = sum(1 for t in tokens if recognised(t, roots, words, cache))
    return known / len(tokens) < MIN_LINE_KNOWN


PARENTHESIS = re.compile(r'\(([^()]{3,80})\)')
MAX_SPAN_TOKENS = 4


def foreign_spans(line, roots, words, cache=None):
    """Character ranges on this line that are not Esperanto, as (start, end).

    Latin is the one language a per-line test cannot reach, and reviewers said
    so: Kabe's Vortaro prints its binomials inside otherwise Esperanto lines —
    'Muŝo (Musca domestica)' — so the line scores as Esperanto and the
    binomial is mined. Six arrived disguised as verbs, because citation_form
    read the Latin -us and -is as tense endings and filed domesticus under
    'domestici'.

    The parenthesis alone cannot decide it: the same shape holds Esperanto
    stage directions, (Vilhelmo silentas), (Volas iri), (Post semajno). What
    decides it is that a short parenthesis with nothing recognisable inside is
    not Esperanto. Measured over the mined corpus that is 517 spans and 730
    distinct tokens, and they are exactly what a reviewer should never see:
    Latin binomials (Abies pectinata, Ascaris lumbricoides), translator
    credits (translated by Clarence Bicknell), currency notes (francs,
    roubles, cents) and citation shorthand (ibid, pp, Oxon). One recognisable
    word anywhere in the span is enough to keep the whole of it.
    """
    spans = []
    for match in PARENTHESIS.finditer(line):
        tokens = [t for t in esperanto.TOKEN.findall(match.group(1))
                  if len(t) > 1]
        if not 2 <= len(tokens) <= MAX_SPAN_TOKENS:
            continue
        if any(recognised(t, roots, words, cache) for t in tokens):
            continue
        spans.append(match.span(1))
    return spans


MIN_GLOSS_COLUMNS = 4
# Above this share of later-column tokens being real dictionary words, the
# columns are an Esperanto table rather than translations. One stray hit does
# not decide it: the German column of 'kaj et | and | und | и | i.' contains
# 'and', which is a genuine Esperanto root.
MAX_GLOSS_ESPERANTO = 0.6


def listed(token, roots, words):
    """Stricter than recognised(): the dictionary must actually hold this.

    No morphology, one ending at most. Used where an over-accepting analysis
    would be worse than a missed one.
    """
    low = token.lower()
    if low in words or low in roots:
        return True
    stem = esperanto.strip_ending(low)
    return stem in roots or stem in words


def foreign_columns(line, roots, words, cache=None):
    """Spans covering the translation columns of a multilingual gloss row.

    The Fundamento prints its vocabulary as one row per word with the
    Esperanto first and five translations after it, pipe-separated:

        patro père | father | Vater | отецъ | ojciec.

    Mining that yields French, English, German and Polish, and it did: 18 of
    one reviewer's 33 foreign verdicts came from this one file. Excluding the
    file is the wrong answer, because the Ekzercaro is also a core Esperanto
    text — its sibling files, which are nothing but tables, are excluded
    already.

    Pipes alone cannot decide it. Two other sources use them for tables that
    are Esperanto throughout: pg-42028 sets administrative, military, naval
    and ecclesiastical vocabulary side by side, and pg-51690 marks verse
    scansion.

    The ordinary recognisability test is not strict enough here either, because
    with 27000 entries the morphology builds 'father' and reads 'Vater' as the
    root vat-. So the later columns are judged by a stricter test — the token,
    or the token with one grammatical ending removed, must be a root or a
    headword the dictionary actually lists. That separates them cleanly:
    father, Vater, ojciec, earth, Erde, ziemia, clean, rein and czysty all
    fail it, while administraciaj, militistaj, maristaj and ekleziaj all pass.
    """
    if line.count('|') < MIN_GLOSS_COLUMNS - 1:
        return []
    columns, offset = [], 0
    for field in line.split('|'):
        columns.append((offset, offset + len(field), field))
        offset += len(field) + 1
    head = columns[0][2]
    if not any(recognised(t, roots, words, cache)
               for t in esperanto.TOKEN.findall(head) if len(t) > 1):
        return []            # the first column is not Esperanto either

    tokens = [t for _s, _e, field in columns[1:]
              for t in esperanto.TOKEN.findall(field) if len(t) > 1]
    if not tokens:
        return []
    passing = sum(1 for t in tokens if listed(t, roots, words))
    if passing / len(tokens) >= MAX_GLOSS_ESPERANTO:
        return []            # the later columns are Esperanto: a table

    spans = [(start, end) for start, end, _field in columns[1:]]
    # The first column is not purely Esperanto either: the Fundamento prints
    # the headword and then its French gloss, 'patro père', so 'père',
    # 'terre', 'homme' and 'mourir' leak from the column we keep. Once the row
    # is known to be a gloss row, everything after the first token of the
    # first column is a translation too.
    head_tokens = list(esperanto.TOKEN.finditer(columns[0][2]))
    if len(head_tokens) > 1:
        spans.append((head_tokens[0].end(), columns[0][1]))
    return spans


def normalise_token(token, roots, words):
    """Resolve the three apostrophe constructions, or reject the token.

    The tokenizer accepts the apostrophe, so three unrelated things arrive
    looking like vocabulary, and reviewers on three shards reported all three:

      * the elided article in verse — l'homaro, l'aero, l'espero, l'ĉielo,
        nine of them in one shard, all from Kofman's Iliad and Zamenhof's
        verse. The article is dropped and the noun kept.
      * Zamenhof's early morpheme-separated spelling — inter'naci'e, sci'i,
        frat'in'o. The apostrophes are morpheme boundaries, so the word is the
        pieces joined, and we accept that reading only if it yields something
        the dictionary recognises.
      * eye-dialect elision — h'm, s'pozi, n'nio, 'strordinare, kam'rado.
        Nothing can be recovered from these: the missing letters are the point.
        They are not vocabulary and are dropped.

    A trailing apostrophe (hord' for hordo) is deliberately left alone, since
    citation_form already restores the elided noun ending.
    """
    if "'" not in token.rstrip("'"):
        return token
    lowered = token.lower()
    if lowered.startswith("l'") and len(token) > 3:
        return token[2:]
    head, _, tail = token.partition("'")
    # A fixed expression in which the apostrophe elides an ending rather than
    # joining morphemes: dank' al (thanks to), where danke is the adverb and al
    # the preposition. Joining it would give 'dankal', dropping it would lose a
    # preposition the dictionary carries, so it is kept as written.
    if (tail.lower() in esperanto.GRAMMATICAL
            and (head.lower() + 'e') in words):
        return token
    joined = token.replace("'", '')
    if len(joined) > 2 and esperanto.analyse(joined, roots, words)[1] != 'unknown':
        return joined
    return None


def is_fragment(line, match):
    """True if the token is a piece of a longer word, not a word itself.

    The tokenizer only accepts Esperanto letters, so a foreign name breaks into
    pieces at the first letter outside the alphabet: Volapük yields 'volap',
    and the abbreviation d-ro yields 'ro'. Both then look like frequent unknown
    lemmas. Checking the characters either side of the match catches them.
    """
    before = line[match.start() - 1] if match.start() else ''
    after = line[match.end()] if match.end() < len(line) else ''
    for neighbour in (before, after):
        if neighbour and (neighbour.isalpha() or neighbour == '-'):
            if neighbour not in esperanto.ESPERANTO_LETTERS:
                return True
            if neighbour == '-':
                return True
    return False


def corpus_files():
    skip = ENGLISH_HEAVY | MULTILINGUAL
    return sorted(f for f in os.listdir(CORPUS)
                  if f.endswith('.txt') and f not in skip)


def plan_shards(count):
    """Greedy longest-first packing, so every shard gets similar total bytes."""
    files = [(os.path.getsize(os.path.join(CORPUS, f)), f)
             for f in corpus_files()]
    files.sort(reverse=True)
    shards = [[] for _ in range(count)]
    weights = [0] * count
    for size, name in files:
        lightest = weights.index(min(weights))
        shards[lightest].append(name)
        weights[lightest] += size
    return shards, weights


def classify(token, roots, words, cache):
    """(lemma, kind) for one token, memoized on the token.

    The corpus is 5.3 million tokens over a few hundred thousand distinct
    forms and each classification walks the morphology, so without the memo
    the same word is analysed thousands of times. Nothing here may depend on
    the line the token came from; the one test that does — is_fragment — stays
    at the call site.
    """
    hit = cache.get(token)
    if hit is not None:
        return hit

    lemma, kind = esperanto.analyse(token, roots, words)
    low = token.lower()

    if lemma is not None and kind == 'known' and lemma != low:
        # analyse() collapses a word onto its root, which is the right key for
        # neither purpose here: 'vort' and 'banlok' are stems, not words, so a
        # reviewer's verdict would be filed under something they never saw.
        # Key every recognised word by its own citation form instead — that
        # also keeps the key stable when the morphology improves, and keying
        # by the analysed root once cost 917 approved lemmas their record.
        citation = esperanto.citation_form(token)
        infinitive = esperanto.participle_infinitive(token, roots, words)
        if infinitive:
            # A participle of a verb we know is a form of that verb, not a
            # derivation of it. Reducing it only on the unknown path left the
            # whole class in the derived queue, where four reviewers
            # independently measured it at 36-46% of everything they were
            # shown: rostita, balancante, meritanta, ŝtelita.
            lemma = infinitive
        elif citation in words:
            # Already a headword, so not a discovery. Reviewers kept meeting
            # the same handful — boato, frido, kato, vermo, tamburo — which
            # arrive in verse with an elided ending (boat', frid') that
            # strip_ending cannot reduce, so the derivation test fired on a
            # word the dictionary already holds.
            lemma = citation
        elif esperanto.strip_ending(low) != lemma:
            # More than root plus ending: a derivation, and settled policy is
            # that a productive derivation earns its own entry.
            lemma, kind = citation, 'derived'
        else:
            lemma = citation

    elif kind == 'unknown':
        if token[:1].isupper():
            # Capitalised tokens keep their surface form: stripping a final -n
            # as if it were the accusative turned Hutton into 'hutto' and
            # London into 'londo', which four reviewers reported.
            lemma = low
        else:
            infinitive = esperanto.participle_infinitive(token, roots, words)
            if infinitive:
                lemma, kind = infinitive, 'derived'
            else:
                # Otherwise unknown words split across their inflections,
                # filing kongreso/kongresoj/kongreson as three discoveries.
                lemma = esperanto.citation_form(token)

    cache[token] = (lemma, kind)
    return lemma, kind


def mine(files, roots, words, min_count, max_citations, filter_lines=True):
    lemmas = {}
    skipped = 0
    cache = {}         # token -> (lemma, kind)
    seen = {}          # token -> is it recognisable at all
    for name in files:
        path = os.path.join(CORPUS, name)
        with open(path, encoding='utf-8') as fh:
            for lineno, line in enumerate(fh, 1):
                if filter_lines and line_is_foreign(line, roots, words, seen):
                    skipped += 1
                    continue
                spans = ()
                if filter_lines:
                    if '(' in line:
                        spans = foreign_spans(line, roots, words, seen)
                    if '|' in line:
                        spans = list(spans) + foreign_columns(
                            line, roots, words, seen)
                for match in esperanto.TOKEN.finditer(line):
                    if any(start <= match.start() < end
                           for start, end in spans):
                        continue
                    token = normalise_token(match.group(), roots, words)
                    if token is None or len(token) < 2:
                        continue
                    lemma, kind = classify(token, roots, words, cache)
                    if lemma is None or kind in ('grammatical', 'correlative'):
                        continue
                    low = token.lower()
                    if low in STOPWORDS or ROMAN.match(low):
                        continue
                    if kind == 'unknown' and is_fragment(line, match):
                        kind = 'fragment'
                    record = lemmas.setdefault(lemma, {
                        'lemma': lemma, 'kind': kind, 'count': 0,
                        'pos_guess': esperanto.guess_pos(token),
                        'forms': {}, 'citations': [],
                        'caps': 0, 'lower': 0,
                        'verdict': None, 'gloss': None, 'note': None,
                    })
                    record['count'] += 1
                    record['forms'][low] = record['forms'].get(low, 0) + 1
                    if token[:1].isupper():
                        record['caps'] += 1
                    else:
                        record['lower'] += 1
                    if len(record['citations']) < max_citations:
                        snippet = ' '.join(line.split())
                        if len(snippet) > 160:
                            cut = snippet.find(token)
                            start = max(0, cut - 70)
                            snippet = ('…' if start else '') + \
                                snippet[start:start + 150] + '…'
                        record['citations'].append({
                            'source': name, 'line': lineno, 'text': snippet})
    kept = {}
    for lemma, record in lemmas.items():
        if record['count'] < min_count:
            continue
        # A word that never appears in lower case is a name, whatever the
        # morphology thinks of it. The check used to apply only to unknown
        # words, which was enough while the compound rule was strict. Once it
        # allowed the second root to carry an ending, Esperanto morphology
        # began to accept the names in these books as compounds — Vinicii as
        # vin + icii, 910 occurrences of it, and Vilfrido, Petronii, Alicio,
        # Lundestad, Rorlund and twenty more besides. Two capitalised
        # occurrences and no lower-case one is the signal; one occurrence is
        # not, since a word can simply begin a sentence.
        if record['lower'] == 0:
            if record['kind'] == 'unknown':
                record['kind'] = 'name'
            elif record['kind'] in ('known', 'derived') and record['caps'] > 1:
                # Overriding the morphology needs more evidence than
                # overriding nothing: one capitalised occurrence can just be
                # a word beginning a sentence.
                record['kind'] = 'name'
        kept[lemma] = record
    return kept, skipped


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--shard', help='I/N, e.g. 3/8')
    parser.add_argument('--plan', type=int, help='print the shard assignment')
    parser.add_argument('--min-count', type=int, default=1,
                        help='drop lemmas seen fewer than this many times IN '
                             'THIS SHARD. Defaults to 1, i.e. keep everything: '
                             'the threshold belongs in the reduce, where the '
                             'counts from all shards have been summed. Applied '
                             'here at 2 it silently lost every word attested '
                             'once in each of several books — duondorme in '
                             'four, eŭkaristio in two, enrigardado in three — '
                             'because no single shard ever reached 2.')
    parser.add_argument('--max-citations', type=int, default=3)
    parser.add_argument('--keep-foreign-lines', action='store_true',
                        help='do not skip lines that fail the Esperanto '
                             'recognisability check (for comparing runs)')
    parser.add_argument('--ledger', nargs='?', const=LEDGER, default=None,
                        help='re-apply verdicts from a ledger after mining, so '
                             'the map can be re-run without discarding review '
                             'work held in the shard files')
    args = parser.parse_args()

    if args.plan:
        shards, weights = plan_shards(args.plan)
        for i, (files, weight) in enumerate(zip(shards, weights), 1):
            print('shard %d/%d: %2d files, %7.1f KB  (%s%s)'
                  % (i, args.plan, len(files), weight / 1024, files[0][:38],
                     ', …' if len(files) > 1 else ''))
        return 0

    if not args.shard or '/' not in args.shard:
        parser.error('--shard I/N is required (or use --plan N)')
    index, count = (int(part) for part in args.shard.split('/'))
    if not 1 <= index <= count:
        parser.error('shard index %d out of range 1..%d' % (index, count))

    shards, _ = plan_shards(count)
    files = shards[index - 1]
    roots, words = esperanto.load_vocabulary()
    lemmas, skipped = mine(files, roots, words, args.min_count,
                           args.max_citations, not args.keep_foreign_lines)

    restored = 0
    if args.ledger and os.path.exists(args.ledger):
        with open(args.ledger, encoding='utf-8') as fh:
            for line in fh:
                if not line.strip():
                    continue
                decided = json.loads(line)
                record = lemmas.get(decided['lemma'])
                if record is None:
                    # The citation form can change when the morphology is
                    # corrected — eliris and eliras now both file under
                    # eliri — so a verdict keyed on the old surface form
                    # would be silently orphaned. Follow it to the new key.
                    record = lemmas.get(
                        esperanto.citation_form(decided['lemma']))
                if record is None:
                    # Same for the participles, which now file under their
                    # verb: a verdict on 'alnajlita' belongs to 'alnajli'.
                    moved = esperanto.participle_infinitive(
                        decided['lemma'], roots, words)
                    if moved:
                        record = lemmas.get(moved)
                if record:
                    record['verdict'] = decided.get('verdict')
                    record['gloss'] = decided.get('gloss')
                    # Bound the restored note too, so a ledger written by an
                    # older build cannot reintroduce the growth.
                    note = decided.get('note')
                    record['note'] = note[:600] if note else None
                    restored += 1

    os.makedirs(SHARDS, exist_ok=True)
    out = os.path.join(SHARDS, 'shard-%d-of-%d.jsonl' % (index, count))
    ordered = sorted(lemmas.values(),
                     key=lambda r: ({'unknown': 0, 'derived': 1, 'name': 2,
                                     'fragment': 3, 'known': 4}.get(r['kind'], 5),
                                    -r['count']))
    with open(out, 'w', encoding='utf-8') as fh:
        for record in ordered:
            fh.write(json.dumps(record, ensure_ascii=False) + '\n')

    unknown = sum(1 for r in ordered if r['kind'] == 'unknown')
    derived = sum(1 for r in ordered if r['kind'] == 'derived')
    print('shard %d/%d: %d files → %s' % (index, count, len(files), out))
    print('  %d lemmas (%d unknown, %d derived, %d other)'
          % (len(ordered), unknown, derived, len(ordered) - unknown - derived))
    if not args.keep_foreign_lines:
        print('  %d lines skipped as not Esperanto' % skipped)
    if args.ledger:
        print('  %d verdicts restored from %s'
              % (restored, os.path.basename(args.ledger)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
