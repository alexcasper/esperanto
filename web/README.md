# Esperanto Worksite — Web App

A local-first TanStack Start application visualising the repository's artifacts:
the corpus source catalog, the compiled dictionary (24.7k entries), and the
corpus-grounded grammar guide.

## Features & Routes

- `/` (`src/routes/index.tsx`) — Worksite overview and portal into the catalog, dictionary, and grammar guide.
- `/sources` (`src/routes/sources.tsx`) — Source catalog joining `RAW/PROVENANCE.md`, `CORPUS/MANIFEST.tsv`, and mining exclusion sets from `tools/mine_lemmas.py`. Filters by pool status, excluded sources, and quarantined works.
- `/dictionary` (`src/routes/dictionary.tsx`) — Fast client-side lexical search over `DICT/entries.jsonl` (24,666 entries), supporting part-of-speech filtering, source layer filtering, historical/dated gloss annotations (O'Connor 1906), literary citations, and deep-links into the grammar guide.
- `/grammar` (`src/routes/grammar.tsx`) — Rendered grammar guide (`GRAMMAR/grammar.md`) featuring the 16 Fundamento rules, morphology tables, syntax, phonology, pragmatics, and corpus usage analysis (§6) with verified corpus citations and section anchors.

## Development & Build

```bash
# 1. Build data bundles from repo artifacts (DICT, CORPUS, GRAMMAR)
python3 tools/build_site_data.py

# 2. Generate TanStack file routes (if routes are added or changed)
cd web && pnpm generate-routes

# 3. Start development server (http://localhost:3000)
pnpm dev

# 4. Production build & preview (http://localhost:4173)
pnpm build
pnpm preview --port 4173
```

## Architecture & Data Flow

- `tools/build_site_data.py` reads repo artifacts (`DICT/entries.jsonl`, `RAW/PROVENANCE.md`, `CORPUS/MANIFEST.tsv`, `GRAMMAR/grammar.md`) and compiles compact JSON/Markdown bundles into `web/src/data/`.
- `src/data/dict.ts` provides Esperanto-aware collation and client-side searching.
- Styling uses Tailwind CSS v4 with support for light/dark themes.
