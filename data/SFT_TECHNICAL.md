# SFT — Qwen fine-tuning datasets (Esperanto)

Three datasets in Qwen SFT chatml format
(https://qwen.readthedocs.io/en/v1.5/training/SFT/example.html): one JSON
object per line, `{"type": "chatml", "messages": [{"role", "content"}...],
"source"}`. Built for beads esp-8ii and esp-b4j. Reads (read-only)
SYNTH/agent_comms.jsonl, RAW/tatoeba/, and CORPUS/ literary files; writes
only inside SFT/.

| File | Samples | Direction | Source |
|---|---|---|---|
| `sft_conversation.jsonl` | 1,532 | Esperanto conversation | SYNTH (1,000) + CORPUS literary dialogue (532) |
| `sft_en2eo.jsonl` | 20,000 | English → Esperanto | Tatoeba |
| `sft_eo2en.jsonl` | 20,000 | Esperanto → English | Tatoeba |

## Datasets

### Conversation (1,532)
Two segments, tagged in `source`:

- `synth-agent-comms` (1,000): Esperanto task-coordination chat. System
  prompt "Vi estas helpema agento por taskokunordigo. Respondu en simpla
  Esperanto." The 50 SYNTH dialogue items become 4-turn multi-turn chats
  (user = requester turns, assistant = responder turns); the other 950
  single SYNTH messages become single-turn exchanges with a reply bank
  matched to the incoming message type (requests get commitments,
  acks/status/number/name messages get receipts).
- `literary-dialogue:<file>` (532): real Esperanto conversation extracted
  from the CORPUS literary corpus (pg-*, wsdump-*, wsrc-*; Zamenhof,
  Grabowski, Vallienne, ...), after a manual-review quality pass that
  added: per-file front-matter skip (first 6,000 chars), turn hygiene
  (must start uppercase, end with terminal punctuation, ≥25 chars, no
  inner guillemets/footnote brackets/verse numbers), inline-attribution
  filter ("ŝi diris" mid-turn), narration-gap tightened to ≤120 chars,
  and exclusion of grammar-textbook quote files. Gated at mean
  known-word rate ≥75 (tools/score_esperanto_text.py vocabulary);
  deduped across files. Every sample ends on an assistant turn. System
  prompt "Vi estas helpema parolpartnero. Respondu en simpla Esperanto."
  Roles alternate user/assistant across turns (quotes are not
  speaker-attributed — a known limitation of this heuristic extraction).
  Public-domain sources per CORPUS/PROVENANCE.md.

### Translation (20,000 each direction)
- Joined from RAW/tatoeba/ exports with the same link logic as
  tools/build_tatoeba_pairs.py (433,053 usable unique pairs after length
  (≤180 chars/side, ≥2 words) and duplicate-text collapse; 434,533 raw).
- 40,000 pairs sampled (seed 20261024), split disjointly: first half for
  en2eo, second half for eo2en — no pair appears in both files.
- Instruction phrasing alternates between English and Esperanto variants
  ("Translate the following ... into Esperanto." / "Traduku la jenan
  frazon el la angla al Esperanto."); the assistant replies with the
  translation only.
- `source`: `tatoeba`. Licence: Tatoeba full exports are CC-BY 2.0 FR —
  attribution required if models/datasets are published (same terms as
  CORPUS/tatoeba).

## Determinism

Seed **20261024**, isolated per-dataset `random.Random` instances (SEED for
conversation, SEED+1 for translation — one segment's template changes can't
perturb another's sample), sorted link enumeration, seeded `random.sample`,
sorted file/span order for the literary extractor. Rebuilds are
byte-identical — verified multiple times, latest:

- sft_conversation.jsonl `f14de3ade4c59e31…43a6` (1,532 samples)
- sft_en2eo.jsonl `4210f88d9f040382…f6d12`
- sft_eo2en.jsonl `2aa110b5652afba7…3c978b`

## Manual sample review (quality pass)

All three datasets were manually reviewed (random samples read in full)
before upload:

- **conversation/literary**: initial extraction had narration tails as
  turns ("diris nespire la maristo."), verse-file garbage (Chanson de
  Roland with mid-line «), essay scare-quotes with footnotes,
  comma-truncated fragments, front-matter book-review quotes, inline
  attributions ("ŝi diris" mid-turn), and grammar-textbook examples.
  All fixed by the hygiene filters above; post-fix review found genuine
  character dialogue (Andersen/Zamenhof, Vallienne, ...). Known
  residual: a few dramatic fragments from early texts with dated
  grammar ("li morti longe").
- **conversation/synth**: replies now match the incoming message type.
- **translation**: Tatoeba link alignment sampled 13/15 excellent;
  the residual flaw rate is community-source noise (e.g. "Mi parolu
  kun vi." for "I have to speak with you.") — not filterable without a
  grammar model, documented here.

Rebuild: `python3 SFT/build_sft_datasets.py` (requires RAW/tatoeba/ exports;
`python3 tools/fetch_tatoeba.py` fetches them idempotently).

## Validation (`SFT/validate_sft_datasets.py`)

All three files: chatml schema ok, user/assistant alternation ok, no empty
messages.

Esperanto-side known-word rate (tools/score_esperanto_text.py vocabulary —
UV roots + morphology + compounds; scores only the Esperanto side: assistant
replies for conversation/en2eo, the source sentence for eo2en):

- conversation: mean 99.14 (synth segment 100.00; literary segment
  naturally name/morphology-rich)
- en2eo: mean 94.38 (14,658 items at 100%, 2,784 at 80–89%)
- eo2en: mean 94.42 (14,765 items at 100%, 2,672 at 80–89%)

The sub-100% band is expected: Tatoeba's community Esperanto uses proper
names (Tomo, Sami, Ziri) and productive derivations (`enŝlosiĝis`,
`bonŝanculo`, `kapjesis`) that the UV-only scorer cannot recognise —
inspection of the low bands confirmed valid Esperanto, so no pairs were
dropped. Literary-prose calibration is ~90%; colloquial community text at
~94% is consistent with the documented marginal-band behaviour.
