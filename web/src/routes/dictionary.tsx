import { createFileRoute, Link } from '@tanstack/react-router'
import { useMemo, useState } from 'react'
import { ENTRIES, POS_LIST, SOURCE_LIST, SOURCE_MAP, searchEntries } from '#/data/dict'
import type { DictEntry } from '#/data/types'

export const Route = createFileRoute('/dictionary')({
  component: DictionaryPage,
})

function DictionaryPage() {
  const [q, setQ] = useState('')
  const [pos, setPos] = useState('')
  const [source, setSource] = useState('')

  const results = useMemo(
    () => searchEntries(q, { pos: pos || undefined, source: source || undefined, limit: 100 }),
    [q, pos, source],
  )

  const citedCount = useMemo(
    () => ENTRIES.filter((e) => e.citations?.length).length,
    [],
  )

  return (
    <div className="mx-auto max-w-5xl px-4 py-10">
      <h1 className="text-3xl font-bold">Dictionary</h1>
      <p className="mt-2 text-sm text-neutral-500 dark:text-neutral-400">
        {ENTRIES.length.toLocaleString()} entries from{' '}
        <code>DICT/entries.jsonl</code> — Fundamento UV-1905, corpus-mined,
        Reta Vortaro, O'Connor 1906. {citedCount.toLocaleString()} words backed by
        corpus attestations & literary citations.
      </p>

      <div className="mt-4 flex flex-wrap items-center gap-2">
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search word or English gloss…"
          className="w-80 rounded-md border border-neutral-300 bg-transparent px-3 py-1.5 text-sm outline-none focus:border-neutral-500 dark:border-neutral-700"
        />
        <select
          value={pos}
          onChange={(e) => setPos(e.target.value)}
          className="rounded-md border border-neutral-300 bg-transparent px-2 py-1.5 text-sm dark:border-neutral-700"
        >
          <option value="">all POS</option>
          {POS_LIST.map((p) => (
            <option key={p} value={p}>
              {p}
            </option>
          ))}
        </select>
        <select
          value={source}
          onChange={(e) => setSource(e.target.value)}
          className="rounded-md border border-neutral-300 bg-transparent px-2 py-1.5 text-sm dark:border-neutral-700"
        >
          <option value="">all layers</option>
          {SOURCE_LIST.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
        <span className="text-xs text-neutral-500">
          {results.length >= 100 ? '100+' : results.length} shown
        </span>
      </div>

      <div className="mt-6 space-y-2">
        {results.map((e) => (
          <EntryCard key={e.word} e={e} />
        ))}
      </div>
    </div>
  )
}

function EntryCard({ e }: { e: DictEntry }) {
  const [open, setOpen] = useState(false)
  const hasDetail = Boolean(
    e.citations?.length || e.grammar_refs?.length || e.dated_gloss || e.attestation,
  )
  return (
    <div className="rounded-lg border border-neutral-200 p-3 dark:border-neutral-800">
      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <span className="text-lg font-semibold">{e.word}</span>
        <span className="text-xs uppercase tracking-wide text-neutral-500">
          {e.pos}
        </span>
        <span className="text-sm">{e.gloss_en}</span>
        {e.gloss_fr && (
          <span className="text-xs italic text-neutral-500">{e.gloss_fr}</span>
        )}
        {e.attestation && (
          <span
            title={`${e.attestation.count.toLocaleString()} occurrences across ${e.attestation.sources.toLocaleString()} sources (${e.attestation.sources_lit ?? 0} lit / ${e.attestation.sources_wiki ?? 0} wiki)`}
            className="rounded bg-emerald-50 px-2 py-0.5 text-xs font-medium text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300"
          >
            {e.attestation.count.toLocaleString()}× · {e.attestation.sources_lit ? `${e.attestation.sources_lit} lit` : `${e.attestation.sources} src`}
          </span>
        )}
        <span className="ml-auto rounded bg-neutral-100 px-2 py-0.5 text-xs text-neutral-600 dark:bg-neutral-800 dark:text-neutral-300">
          {e.source}
        </span>
      </div>
      {e.dated_gloss && (
        <div className="mt-1 text-xs text-neutral-500">
          1906 wording: <em>{e.dated_gloss}</em>
        </div>
      )}
      {hasDetail && (
        <>
          <button
            onClick={() => setOpen(!open)}
            className="mt-1 text-xs text-neutral-500 underline decoration-dotted hover:text-neutral-800 dark:hover:text-neutral-200"
          >
            {open ? 'hide details' : `details ${e.citations?.length ? `(${e.citations.length} quotes)` : ''}`}
          </button>
          {open && (
            <div className="mt-2 space-y-2 border-t border-neutral-100 pt-2 text-sm dark:border-neutral-800">
              {e.attestation && (
                <div className="text-xs text-neutral-500">
                  attested: <strong>{e.attestation.count.toLocaleString()}×</strong> across{' '}
                  <strong>{e.attestation.sources.toLocaleString()}</strong> source(s)
                  {typeof e.attestation.sources_lit === 'number' && (
                    <span className="ml-1 text-neutral-400">
                      ({e.attestation.sources_lit.toLocaleString()} literary · {e.attestation.sources_wiki?.toLocaleString() ?? 0} wiki)
                    </span>
                  )}
                </div>
              )}
              {e.citations?.map((c, i) => {
                const srcRec = SOURCE_MAP.get(c.source)
                return (
                  <blockquote
                    key={i}
                    className="border-l-2 border-neutral-300 pl-3 text-sm italic dark:border-neutral-700"
                  >
                    “{c.text}”
                    <footer className="mt-0.5 text-xs not-italic text-neutral-500">
                      {srcRec ? (
                        <>
                          <span className="font-medium text-neutral-700 dark:text-neutral-300">
                            {srcRec.title}
                          </span>{' '}
                          <span className="font-mono text-[11px] text-neutral-400">
                            ({c.source})
                          </span>
                        </>
                      ) : (
                        <span className="font-mono text-xs">{c.source}</span>
                      )}
                    </footer>
                  </blockquote>
                )
              })}
              {e.grammar_refs?.map((r, i) => (
                <div key={i} className="text-xs">
                  <Link
                    to="/grammar"
                    hash={`section-${r.section}`}
                    className="text-emerald-700 underline decoration-dotted dark:text-emerald-400"
                  >
                    GRAMMAR §{r.section}
                  </Link>{' '}
                  — {r.topic}
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  )
}
