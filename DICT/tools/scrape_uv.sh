#!/bin/sh
# Fetch the Universala Vortaro (Fundamento de Esperanto, 1905) from the
# Akademio de Esperanto and parse it into uv_final.json.
# (akademio-de-esperanto.org/fundamento/universala_vortaro.html)
set -e
cd "$(dirname "$0")"
curl -sL --max-time 60 -o /tmp/uv.html \
  'https://akademio-de-esperanto.org/fundamento/universala_vortaro.html'
python3 parse_uv.py  > /dev/null     # pass 1 (line format; also writes /tmp/uv_entries.json)
python3 parse_uv2.py > /dev/null     # pass 2 (sequential cursor)
python3 merge_uv.py                 # merges passes -> /tmp/uv_final.json
python3 build_dict.py               # -> ../entries.jsonl
