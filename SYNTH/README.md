# SYNTH — synthetic Esperanto agent-communication corpus

Seeded, deterministic corpus of short task-coordination messages between
synthetic agents, in simple Esperanto built from Universala Vortaro-rooted
vocabulary. Generated for bead **esp-77w**. Nothing outside `SYNTH/` was
touched (DICT/entries.jsonl is read by the scorer only).

## Files

| File | What |
|---|---|
| `agent_comms.jsonl` | the corpus — 1000 items, one JSON object per line |
| `scores.jsonl` | per-item scorer results (`id`, `type`, `tokens`, `known_pct`) |
| `generate_synth_corpus.py` | generator (seeded, deterministic) |
| `score_synth_corpus.py` | per-item scoring against the repo scorer's vocabulary |
| `check_vocab.py` | vocabulary pre-check helper used during development |

## Item schema

```json
{"id": "synth-0001", "seed": 20261024, "type": "request",
 "sender": "Delta", "recipient": "Beto", "text": "Bonvolu provi la demandojn lunde."}
```

- `type`: `request` (250), `ack` (200), `status` (250), `number` (150),
  `name` (100), `dialogue` (50).
- `dialogue` items additionally carry `turns`: `[{sender, text}, ...]`
  (4-turn request→ack→progress→completion exchanges). For dialogues,
  `sender`/`recipient` are derived from the first two turns.
- `text` is always present (scoring field); for dialogues it is the turns
  joined with ` / `.

## Determinism

- **Seed: 20261024** (also recorded in every item's `seed` field).
- One `random.Random(SEED)`; per-kind template combinations are enumerated
  exhaustively and sampled with `random.sample` (no rejection loops — the
  generator always terminates); kinds are interleaved with a seeded shuffle.
- Regeneration is byte-identical. Verified sha256 (final build):
  `575375152b60e59a86258403d05c883d2a298cf13a41fc92d52426fc6ed621d3`.
- Regenerate: `python3 SYNTH/generate_synth_corpus.py`

## Validation (tools/score_esperanto_text.py vocabulary)

Per-item scoring (`score_synth_corpus.py`) applies the exact recognition
logic of `tools/score_esperanto_text.py` (UV roots + morphology + compounds)
to the `text` field only:

- **Content known-word rate: 100.00% on all 1000 items** (min = max = 100;
  9060 tokens total). Vocabulary was pre-checked against DICT/entries.jsonl
  and every template slot is UV-rooted.
- The repo CLI on the raw file reports **71.7% known** over 21218 tokens —
  the gap is JSONL structural keys (`seed`, `recipient`, `type`, ...), not
  Esperanto; the scorer tokenizes the whole file. Score the `text` field
  (scores.jsonl) for the content figure.
- Corpus grammar constraints beyond vocabulary: tense-compatible time
  phrases per template (future/imperative templates never take `hieraŭ`,
  past templates never take `morgaŭ`); plural accusatives after numerals;
  nominative subjects in `estas`-clauses.

## Score distribution (per item, known_pct)

```
100%: 1000 items   (no other buckets)
```

Per-type mean: all 100.00 (ack n=200, dialogue n=50, name n=100,
number n=150, request n=250, status n=250).
