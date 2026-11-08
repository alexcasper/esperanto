---
language:
  - eo
  - en
license: cc-by-2.0
task_categories:
  - text-generation
  - translation
tags:
  - esperanto
  - sft
  - chatml
  - qwen
  - tatoeba
size_categories:
  - 10K<n<100K
---

# Esperanto SFT datasets (Qwen chatml format)

Three supervised-fine-tuning datasets for Qwen-class models, in the Qwen SFT
chatml JSONL format (`{"type": "chatml", "messages": [{"role", "content"}…],
"source"}`):

| File | Samples | Direction |
|---|---|---|
| `sft_conversation.jsonl` | 1,532 | Esperanto conversation (multi-turn) |
| `sft_en2eo.jsonl` | 20,000 | English → Esperanto |
| `sft_eo2en.jsonl` | 20,000 | Esperanto → English |

## Sources

- **Conversation** — two tagged segments in `source`:
  - `synth-agent-comms` (1,000): seeded synthetic Esperanto
    task-coordination messages (agent requests, acks, status updates,
    numbers, names, 4-turn dialogues) built from Universala-Vortaro-rooted
    vocabulary; replies typed to the incoming message kind.
  - `literary-dialogue:<file>` (532): dialogue extracted from public-domain
    Esperanto literature (Zamenhof's Andersen/Dickinson translations,
    Grabowski, Vallienne, Kabe, …), passed through turn-hygiene and
    Esperanto-known-word filters; quotes are not speaker-attributed, roles
    alternate heuristically.
- **Translation** — 40,000 pairs sampled (seeded) from the Tatoeba
  en↔eo sentence links; instruction phrasing alternates English/Esperanto;
  assistant answers with the translation only.

## Licence / attribution

- Conversation: synthetic + public-domain literary sources.
- Translation: Tatoeba exports are **CC-BY 2.0 FR** — attribution required
  if you redistribute or publish derivatives ("source: tatoeba" per sample).
  The card licence field reflects the dominant (Tatoeba) portion.

## Quality

- Esperanto-side known-word rate (Universala Vortaro roots + morphology):
  conversation 99.1%, en→eo 94.4%, eo→en 94.4%. Sub-100% scores are
  proper names and productive derivations outside the reference
  vocabulary, not errors (manually reviewed).
- Known residual noise: a small rate of community-translation flaws in
  Tatoeba pairs (e.g. tense slips), and unattributed literary turns.
- Builds are seeded and deterministic; rebuild tooling and the full QA
  record live in `SFT_TECHNICAL.md`.
