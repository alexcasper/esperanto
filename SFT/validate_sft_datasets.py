#!/usr/bin/env python3
"""Validate the SFT/ datasets: Qwen chatml schema, counts, dedupe, and
Esperanto-side scoring with the repo scorer's vocabulary.
"""
import collections
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import score_esperanto_text as s

FILES = ['sft_conversation.jsonl', 'sft_en2eo.jsonl', 'sft_eo2en.jsonl']


def known_pct(text, roots, words):
    tokens = [t for t in s.TOKEN.findall(text) if len(t) > 1]
    if not tokens:
        return None, 0
    hits = sum(1 for t in tokens if s.recognised(t, roots, words))
    return 100.0 * hits / len(tokens), len(tokens)


def main():
    roots, words = s.load_vocabulary()
    for name in FILES:
        path = os.path.join(HERE, name)
        n, roles_bad, empty = 0, 0, 0
        keys_ok = True
        seen_msgs = set()
        dup_msgs = 0
        pcts = []
        for line in open(path, encoding='utf-8'):
            sample = json.loads(line)
            n += 1
            if sample.get('type') != 'chatml' or 'messages' not in sample \
                    or 'source' not in sample:
                keys_ok = False
            msgs = sample['messages']
            roles = [m['role'] for m in msgs]
            core = [r for r in roles if r != 'system']
            if core != ['user', 'assistant'] * (len(core) // 2) or \
                    (len(core) % 2 != 0) or roles[0] not in ('system', 'user'):
                roles_bad += 1
            for m in msgs:
                if not m.get('content', '').strip():
                    empty += 1
                key = (m['role'], m['content'])
                if key in seen_msgs:
                    dup_msgs += 1
                seen_msgs.add(key)
            for m in msgs:
                # score only the Esperanto side of each sample:
                # conversation/en2eo -> assistant reply; eo2en -> the
                # Esperanto source sentence (after the instruction blank line)
                if name == 'sft_eo2en.jsonl':
                    if m['role'] != 'user':
                        continue
                    target = m['content'].split('\n\n')[-1]
                else:
                    if m['role'] != 'assistant':
                        continue
                    target = m['content']
                pct, _ = known_pct(target, roots, words)
                if pct is not None:
                    pcts.append(pct)
        token_weighted = None
        print('%s: %d samples | schema_ok=%s | bad_roles=%d | empty=%d | '
              'duplicate messages=%d'
              % (name, n, keys_ok, roles_bad, empty, dup_msgs))
        if pcts:
            buckets = collections.Counter(int(p // 10) * 10 for p in pcts)
            print('  Esperanto assistant-side known%%: mean=%.2f min=%.2f '
                  'max=%.2f' % (sum(pcts) / len(pcts), min(pcts), max(pcts)))
            for b in sorted(buckets):
                print('    %3d-%3d%%: %d' % (b, b + 9, buckets[b]))


if __name__ == '__main__':
    main()
