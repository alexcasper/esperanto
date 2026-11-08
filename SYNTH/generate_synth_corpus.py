#!/usr/bin/env python3
"""Generate a seeded, deterministic synthetic Esperanto agent-communication corpus.

Output: SYNTH/agent_comms.jsonl — 1000 short task-coordination messages
(requests, acknowledgements, status updates, numbers, names, short dialogues)
between synthetic agents, in simple grammatical Esperanto built from
Universala Vortaro-rooted vocabulary (verified against DICT/entries.jsonl via
tools/score_esperanto_text.py).

Determinism: single fixed SEED, one random.Random instance, list-based
vocabularies (never set iteration), and — for uniqueness — exhaustive
enumeration of each kind's template combinations followed by a seeded
random.sample (no rejection loops, so generation always terminates).
"""
import json
import os
import random
from itertools import product

SEED = 20261024
TARGET = 1000
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'agent_comms.jsonl')

AGENTS = ['Alfa', 'Beto', 'Gama', 'Delta', 'Epsilono', 'Zeto']

# Accusative objects (direct objects).
OBJECTS = ['la raporton', 'la dosieron', 'la mesaĝon', 'la liston',
           'la teston', 'la planon', 'la protokolon', 'la nomon',
           'la adreson', 'la kopion', 'la demandojn', 'la respondojn']
# Nominative objects (subjects / after prepositions).
OBJECTS_N = ['la raporto', 'la dosiero', 'la mesaĝo', 'la listo',
             'la testo', 'la plano', 'la protokolo', 'la nomo',
             'la adreso', 'la kopio', 'la demandoj', 'la respondoj']

VERBS_INF = ['sendi', 'legi', 'kontroli', 'fini', 'skribi', 'ĝisdatigi',
             'aldoni', 'forigi', 'provi', 'kopii']
IMPERATIVES = ['sendu', 'legu', 'kontrolu', 'finu', 'skribu', 'aldonu',
               'forigu', 'provu', 'kopiu']

TIMES = ['hodiaŭ', 'morgaŭ', 'nun', 'baldaŭ', 'tuj', 'hieraŭ',
         'antaŭ la sesa horo', 'post la tagmanĝo', 'lunde', 'vendrede',
         'matene', 'vespere', 'je la tria horo', 'antaŭ la fino de la tago']
# Tense-compatible subsets: future/imperative verbs can't take 'hieraŭ',
# past-tense verbs can't take 'morgaŭ'.
FUT_TIMES = [t for t in TIMES if t != 'hieraŭ']
PAST_TIMES = [t for t in TIMES if t != 'morgaŭ']

STATES = ['La servo funkcias bone', 'La reto estas rapida',
          'Ĉio estas preta', 'La dosiero estas granda',
          'La tasko estas facila', 'La problemo estas grava',
          'La testo estis bona', 'La teamo estas forta',
          'La laboro estas bona', 'La plano estas bona']

NUM_WORDS = ['unu', 'du', 'tri', 'kvar', 'kvin', 'ses', 'sep', 'ok', 'naŭ',
             'dek', 'dudek', 'tridek', 'kvindek', 'cent']


def pairs():
    """All ordered distinct agent pairs, deterministic order."""
    return [(a, b) for a in AGENTS for b in AGENTS if a != b]


def combos(text_fn, slot_lists):
    """Enumerate (text_fn over slots) for the cartesian product of slots."""
    return [text_fn(*slots) for slots in product(*slot_lists)]


# --- per-kind enumerators: list of unique Esperanto texts -------------------

def request_texts():
    texts = []
    texts += combos(lambda v, o, t: 'Bonvolu %s %s %s.' % (v, o, t),
                    [VERBS_INF, OBJECTS, FUT_TIMES])
    texts += combos(lambda v, o, t: 'Ĉu vi povas %s %s %s?' % (v, o, t),
                    [VERBS_INF, OBJECTS, FUT_TIMES])
    texts += ['Mi bezonas %s por la tasko.' % o for o in OBJECTS]
    texts += combos(lambda i, o: 'Mi petas, ke vi %s %s.' % (i, o),
                    [IMPERATIVES, OBJECTS])
    texts += ['Kiam vi finos la laboron? %s estas la limo.' % t
              for t in FUT_TIMES]
    return texts


def ack_texts():
    texts = []
    texts += ['Jes, mi faros ĝin %s.' % t for t in FUT_TIMES]
    texts += combos(lambda o, t: 'Dankon. Mi ricevis %s %s.' % (o, t),
                    [OBJECTS, PAST_TIMES])
    texts += ['Bone, mi komprenas. Mi komencos %s.' % t for t in FUT_TIMES]
    texts += combos(lambda o, t: 'Mi konfirmas: %s estos preta %s.' % (o, t),
                    [OBJECTS_N, FUT_TIMES])
    texts += ['Ne problemo. Mi helpos al vi %s.' % t for t in FUT_TIMES]
    texts += combos(lambda o, t: 'Certe. Mi sendos %s %s.' % (o, t),
                    [OBJECTS, FUT_TIMES])
    return texts


def status_texts():
    texts = []
    texts += combos(lambda o, t: 'La tasko estas preta. Mi sendis %s %s.'
                    % (o, t), [OBJECTS, PAST_TIMES])
    texts += combos(lambda o, t: 'Mi laboras pri %s. Ĝi estos finita %s.'
                    % (o, t), [OBJECTS_N, FUT_TIMES])
    texts += [s + '.' for s in STATES]
    texts += ['%s procentoj de la tasko estas faritaj.' % n.capitalize()
              for n in NUM_WORDS]
    texts += ['La kodo havas eraron. Mi korektis ĝin %s.' % t
              for t in PAST_TIMES]
    texts += ['Mi komencis la laboron hieraŭ kaj mi daŭrigos %s.' % t
              for t in FUT_TIMES]
    texts += ['La testo estas finita %s. Ĉio estas bone.' % t
              for t in PAST_TIMES]
    return texts


def number_texts():
    texts = []
    texts += ['Ni bezonas %s dosierojn por la tasko.' % n for n in NUM_WORDS]
    texts += ['La laboro daŭros %s horojn.' % n for n in NUM_WORDS]
    texts += combos(lambda n, t: 'Sendu al mi %s mesaĝojn %s.' % (n, t),
                    [NUM_WORDS, FUT_TIMES])
    texts += ['Nombro de eraroj: %s.' % n for n in NUM_WORDS]
    texts += combos(lambda n1, n2: 'La teamo havas %s membrojn, ne %s.'
                    % (n1, n2), [NUM_WORDS, NUM_WORDS])
    return texts


def name_texts():
    texts = []
    texts += ['Saluton, %s. Kiel vi fartas?' % a for a in AGENTS]
    texts += ['Mia nomo estas %s. Mi estas nova agento.' % a for a in AGENTS]
    texts += ['Ĉu %s estas nun libera? Mi bezonas helpon.' % a
              for a in AGENTS]
    texts += combos(lambda o, a: 'Sendu %s al %s, mi petas.' % (o, a),
                    [OBJECTS, AGENTS])
    texts += ['Saluton, %s! Dankon pro via rapida respondo.' % a
              for a in AGENTS]
    texts += ['%s, ĉu vi havas tempon por la tasko?' % a for a in AGENTS]
    texts += combos(lambda a, t: 'Mia amiko %s helpos al vi %s.' % (a, t),
                    [AGENTS, FUT_TIMES])
    return texts


def dialogue_texts():
    texts = []
    for a, b in pairs():
        for v, o, t in product(VERBS_INF, OBJECTS, FUT_TIMES):
            texts.append(' / '.join([
                '%s: Bonvolu %s %s %s.' % (a, v, o, t),
                '%s: Jes, mi faros ĝin. Ĝi estos preta %s.' % (b, t),
                '%s: Dankon. Mi atendas la rezulton.' % a,
                '%s: Mi finis. La rezulto estas bona; vi povas kontroli ĝin.' % b,
            ]))
    return texts


def main():
    rnd = random.Random(SEED)
    quotas = [('request', request_texts, 250),
              ('ack', ack_texts, 200),
              ('status', status_texts, 250),
              ('number', number_texts, 150),
              ('name', name_texts, 100),
              ('dialogue', dialogue_texts, 50)]

    pools = []
    for kind, texts_fn, quota in quotas:
        texts = texts_fn()
        assert len(set(texts)) == len(texts), '%s has duplicate templates' % kind
        assert quota <= len(texts), (
            '%s quota %d exceeds unique space %d' % (kind, quota, len(texts)))
        chosen = rnd.sample(texts, quota)
        items_kind = []
        for text in chosen:
            item = {'id': None, 'seed': SEED, 'type': kind,
                    'text': text}
            if kind == 'dialogue':
                turns = [part.split(': ', 1) for part in text.split(' / ')]
                item['turns'] = [{'sender': s, 'text': t} for s, t in turns]
                item['sender'] = turns[0][0]
                item['recipient'] = turns[1][0]
            else:
                a, b = pairs()[rnd.randrange(len(pairs()))]
                item['sender'], item['recipient'] = a, b
            items_kind.append(item)
        pools.append(items_kind)

    items = [item for pool in pools for item in pool]
    assert len(items) == TARGET
    rnd.shuffle(items)
    for n, item in enumerate(items, 1):
        item['id'] = 'synth-%04d' % n

    with open(OUT, 'w', encoding='utf-8') as fh:
        for item in items:
            fh.write(json.dumps(item, ensure_ascii=False, sort_keys=True) + '\n')
    print('wrote %d items to %s (seed=%d)' % (len(items), OUT, SEED))


if __name__ == '__main__':
    main()
