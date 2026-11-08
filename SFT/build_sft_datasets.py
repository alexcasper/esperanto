#!/usr/bin/env python3
"""Build three Qwen SFT (chatml) fine-tuning datasets into SFT/:

  sft_conversation.jsonl  — Esperanto task-coordination conversations
                            (from SYNTH/agent_comms.jsonl)
  sft_en2eo.jsonl         — English -> Esperanto translation (Tatoeba)
  sft_eo2en.jsonl         — Esperanto -> English translation (Tatoeba)

Qwen SFT format (https://qwen.readthedocs.io/en/v1.5/training/SFT/example.html):
one JSON object per line:
  {"type": "chatml", "messages": [{"role": ..., "content": ...}, ...],
   "source": ...}

Determinism: fixed SEED, one random.Random, explicit sort keys everywhere.
Reads RAW/tatoeba/ (read-only; join mirrors tools/build_tatoeba_pairs.py)
and SYNTH/agent_comms.jsonl. Writes only inside SFT/.
"""
import bz2
import glob
import io
import json
import os
import random
import re
import sys
import tarfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), 'tools'))
import score_esperanto_text as scorer

scorer_roots, scorer_words = scorer.load_vocabulary()

SEED = 20261024
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SYNTH = os.path.join(ROOT, 'SYNTH', 'agent_comms.jsonl')
RAWT = os.path.join(ROOT, 'RAW', 'tatoeba')
N_TRANSLATION_PER_DIR = 20000
MAX_CHARS = 180          # per-side sentence cap
MIN_WORDS = 2            # per-side word floor

SYSTEM_ESPERANTO_AGENT = ('Vi estas helpema agento por taskokunordigo. '
                          'Respondu en simpla Esperanto.')
SYSTEM_ESPERANTO_CHAT = ('Vi estas helpema parolpartnero. '
                         'Respondu en simpla Esperanto.')

# literary dialogue extraction
QUOTE_RE = [re.compile(r'“([^”]{15,300})”', re.S),
            re.compile(r'«([^»]{15,300})»', re.S),
            re.compile(r'"([^"\n]{15,300})"')]
MAX_TURN_GAP = 120      # chars of narration allowed between two quotes
MAX_TURNS = 8
RUN_MEAN_KNOWN = 75.0   # scorer gate per dialogue run
FRONT_MATTER = 6000     # chars skipped per file (Gutenberg intro etc.)
# files quoting grammar examples, not conversation (detected in manual review)
GRAMMAR_META = re.compile(r'\b(propozicio|prepozicio|demonstrativo|'
                          r'infinitivo|participo|deklinac|konjugac)\b')


def read_sentences(path):
    want_lang = os.path.basename(path).split('_')[0]
    sentences = {}
    with bz2.open(path, 'rt', encoding='utf-8') as fh:
        for line in fh:
            fields = line.rstrip('\n').split('\t')
            sid, lang, text = int(fields[0]), fields[1], fields[2]
            if lang != want_lang:
                raise ValueError('%s: unexpected lang %r' % (path, lang))
            sentences[sid] = text
    return sentences


def iter_links(tarball):
    with tarfile.open(tarball, 'r:bz2') as tar:
        for member in tar:
            if member.name != 'links.csv':
                continue
            extracted = tar.extractfile(member)
            with io.TextIOWrapper(extracted, encoding='utf-8') as fh:
                for line in fh:
                    a, b = line.rstrip('\n').split('\t')
                    yield int(a), int(b)
            break


def tatoeba_pairs():
    """(epo_text, eng_text) pairs; mirrors build_tatoeba_pairs.py's join."""
    epo = read_sentences(os.path.join(RAWT, 'epo_sentences.tsv.bz2'))
    eng = read_sentences(os.path.join(RAWT, 'eng_sentences.tsv.bz2'))
    pairs = set()
    for a, b in iter_links(os.path.join(RAWT, 'links.tar.bz2')):
        if a in epo and b in eng:
            pairs.add((a, b))
        elif a in eng and b in epo:
            pairs.add((b, a))
    out = []
    for epo_id, eng_id in sorted(pairs):
        out.append((epo[epo_id], eng[eng_id]))
    return out


def chatml(system, turns, source):
    messages = []
    if system:
        messages.append({'role': 'system', 'content': system})
    for role, content in turns:
        messages.append({'role': role, 'content': content})
    return {'type': 'chatml', 'messages': messages, 'source': source}


def write_jsonl(path, samples):
    with open(path, 'w', encoding='utf-8') as fh:
        for sample in samples:
            fh.write(json.dumps(sample, ensure_ascii=False) + '\n')
    print('wrote %s (%d samples)' % (path, len(samples)))


def known_pct(text):
    tokens = [t for t in scorer.TOKEN.findall(text) if len(t) > 1]
    if not tokens:
        return 0.0
    hits = sum(1 for t in tokens if scorer.recognised(t, scorer_roots,
                                                      scorer_words))
    return 100.0 * hits / len(tokens)


def clean_turn(body):
    """Normalise a quoted span; return None if it fails turn hygiene.

    Guards against the noise seen in manual review: attribution tails
    ('diris nespire la maristo.'), comma-truncated fragments, verse lines
    with inner guillemets or line numbers, and footnote/meta quotes.
    """
    turn = re.sub(r'\s+', ' ', body).strip()
    if len(turn) < 25 or ' ' not in turn:
        return None
    if turn[0].islower():                      # narration tail, not speech
        return None
    if turn[-1] not in '.!?…':                 # mid-sentence fragment
        return None
    if re.search(r'[«”\[\]]|\b\d{2,}\b', turn):  # verse/footnote markers
        return None
    if re.search(r'\b(ŝi|li|ĝi|ni|ili|mi|vi) (diris|demandis|respondis|'
                 r'aldonis|kriis|ekkriis|parolis|muĝis)\b', turn):
        return None                           # attribution embedded mid-turn
    return turn


def literary_runs():
    """Dialogue runs (lists of quoted turns) from CORPUS literary files.

    Consecutive quoted spans with <= MAX_TURN_GAP chars of narration
    between them form one run; runs of >= 2 turns (capped at MAX_TURNS)
    are kept if their mean known-word rate clears RUN_MEAN_KNOWN.
    Deterministic: sorted file order, sorted span order.
    """
    patterns = ('pg-*.txt', 'wsdump-*.txt', 'wsrc-*.txt')
    seen_runs = set()
    runs = []
    for pattern in patterns:
        for path in sorted(glob.glob(os.path.join(ROOT, 'CORPUS', pattern))):
            text = open(path, encoding='utf-8', errors='replace').read()
            text = text[FRONT_MATTER:]   # skip Gutenberg front matter
            spans = []
            for rx in QUOTE_RE:
                for m in rx.finditer(text):
                    spans.append((m.start(), m.end(), m.group(1)))
            spans.sort()
            cleaned, last_end = [], -1
            for st, en, body in spans:
                if st < last_end:
                    continue
                cleaned.append((st, en, body))
                last_end = en
            runs_file, cur = [], []
            for st, en, body in cleaned:
                if cur and st - cur[-1][1] > MAX_TURN_GAP:
                    runs_file.append(cur)
                    cur = []
                cur.append((st, en, body))
            if cur:
                runs_file.append(cur)
            for run in runs_file:
                if len(run) < 2:
                    continue
                turns = [clean_turn(b) for _, _, b in run[:MAX_TURNS]]
                turns = [t for t in turns if t is not None]
                if len(turns) < 2:
                    continue
                if any(GRAMMAR_META.search(t) for t in turns):
                    continue
                key = tuple(turns)
                if key in seen_runs:
                    continue
                seen_runs.add(key)
                if sum(known_pct(t) for t in turns) / len(turns) \
                        < RUN_MEAN_KNOWN:
                    continue
                runs.append((os.path.basename(path), turns))
    return runs


def build_conversation(rnd):
    """user/assistant chats from SYNTH agent communications.

    Dialogue items become 4-turn multi-turn chats (user = requester turns,
    assistant = responder turns). Single-message items get a deterministic
    seeded assistant reply from an ack-style template bank.
    """
    items = [json.loads(line) for line in
             open(SYNTH, encoding='utf-8')]
    samples = []
    for item in items:
        if item['type'] == 'dialogue':
            turns = [(t['sender'], t['text']) for t in item['turns']]
            first = turns[0][0]
            chat = []
            for sender, text in turns:
                role = 'user' if sender == first else 'assistant'
                chat.append((role, text))
            samples.append(chatml(SYSTEM_ESPERANTO_AGENT, chat,
                                  'synth-agent-comms'))
        else:
            # reply type matched to the incoming message type: requests get
            # commitments, acks/status/number/name messages get receipts
            banks = {
                'request': [
                    'Jes, mi faros ĝin tuj.',
                    'Bone, mi komprenas. Mi komencos baldaŭ.',
                    'Mi konfirmas: la tasko estos farita morgaŭ.',
                    'Ne problemo. Mi helpos al vi.',
                    'Certe. Mi sendos la raporton antaŭ la fino de la tago.',
                ],
                'ack': [
                    'Dankon. Mi ĝojas ricevi vian respondon.',
                    'Bone, mi komprenas vin.',
                    'Dankon por via rapida respondo.',
                ],
                'status': [
                    'Bone. Dankon por la mesaĝo.',
                    'Tre bone, mi atendas la rezulton.',
                    'Bone, mi komprenas la staton.',
                ],
                'number': [
                    'Bone, mi komprenas la nombron.',
                    'Dankon. La nombro estas grava por la plano.',
                ],
                'name': [
                    'Saluton! Mi ĝojas pri via mesaĝo.',
                    'Saluton, mia nomo estas Delta. Mi estas agento.',
                ],
            }
            bank = banks.get(item['type'], banks['ack'])
            chat = [('user', item['text']),
                    ('assistant', bank[rnd.randrange(len(bank))])]
            samples.append(chatml(SYSTEM_ESPERANTO_AGENT, chat,
                                  'synth-agent-comms'))
    n_synth = len(samples)
    for fname, turns in literary_runs():
        # every chatml sample must end on an assistant turn; drop a
        # trailing unpaired user turn from odd-length runs
        if len(turns) % 2 == 1:
            turns = turns[:-1]
        chat = []
        for i, turn in enumerate(turns):
            chat.append(('user' if i % 2 == 0 else 'assistant', turn))
        samples.append(chatml(SYSTEM_ESPERANTO_CHAT, chat,
                              'literary-dialogue:' + fname))
    print('  conversation: %d synth + %d literary'
          % (n_synth, len(samples) - n_synth))
    write_jsonl(os.path.join(HERE, 'sft_conversation.jsonl'), samples)
    return samples


def usable(epo_text, eng_text):
    for text in (epo_text, eng_text):
        if not text or len(text) > MAX_CHARS:
            return False
        if len(text.split()) < MIN_WORDS:
            return False
    return True


def build_translation(rnd):
    pairs = [p for p in tatoeba_pairs() if usable(*p)]
    # collapse identical-text duplicates so one frequent sentence doesn't
    # dominate the sample
    seen_texts, unique_pairs = set(), []
    for epo_text, eng_text in pairs:
        key = (epo_text, eng_text)
        if key in seen_texts:
            continue
        seen_texts.add(key)
        unique_pairs.append(key)
    print('tatoeba: %d usable unique pairs' % len(unique_pairs))
    need = 2 * N_TRANSLATION_PER_DIR
    if len(unique_pairs) < need:
        raise SystemExit('need %d pairs, only %d usable'
                         % (need, len(unique_pairs)))
    chosen = rnd.sample(unique_pairs, need)
    half = len(chosen) // 2
    e2e, e2e_src = chosen[:half], chosen[half:]

    instr_e2e = ('Translate the following English sentence into Esperanto. '
                 'Answer with the Esperanto translation only.\n\n{}')
    instr_e2e_es = ('Traduku la jenan frazon el la angla al Esperanto. '
                    'Respondu nur per la Esperanta traduko.\n\n{}')
    instr_en = ('Translate the following Esperanto sentence into English. '
                'Answer with the English translation only.\n\n{}')
    instr_en_es = ('Traduku la jenan frazon el Esperanto en la anglan. '
                   'Respondu nur per la angla traduko.\n\n{}')

    samples = []
    for epo_text, eng_text in e2e:
        instruction = (instr_e2e if rnd.randrange(2) == 0 else instr_e2e_es)
        samples.append(chatml(None, [
            ('user', instruction.format(eng_text)),
            ('assistant', epo_text)], 'tatoeba'))
    write_jsonl(os.path.join(HERE, 'sft_en2eo.jsonl'), samples)

    samples = []
    for epo_text, eng_text in e2e_src:
        instruction = (instr_en if rnd.randrange(2) == 0 else instr_en_es)
        samples.append(chatml(None, [
            ('user', instruction.format(epo_text)),
            ('assistant', eng_text)], 'tatoeba'))
    write_jsonl(os.path.join(HERE, 'sft_eo2en.jsonl'), samples)


def main():
    # isolated per-dataset generators: changes to one segment's template
    # bank must not perturb the other segments' seeded samples
    build_conversation(random.Random(SEED))
    build_translation(random.Random(SEED + 1))


if __name__ == '__main__':
    main()
