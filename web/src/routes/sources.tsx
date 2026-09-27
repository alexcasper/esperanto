import { createFileRoute } from '@tanstack/react-router'
import { useMemo, useState } from 'react'
import { SOURCES } from '#/data/dict'
import type { SourceRecord } from '#/data/types'

export const Route = createFileRoute('/sources')({
  component: SourcesPage,
})

type Filter = 'all' | 'excluded' | 'quarantined' | 'pool'

function SourcesPage() {
  const [q, setQ] = useState('')
  const [filter, setFilter] = useState<Filter>('all')

  const filtered = useMemo(() => {
    const needle = q.trim().toLowerCase()
    return SOURCES.filter((s) => {
      if (filter === 'excluded' && !s.excluded && !s.quarantined) return false
      if (filter === 'quarantined' && !s.quarantined) return false
      if (filter === 'pool' && (s.excluded || s.quarantined)) return false
      if (!needle) return true
      return (
        s.file.toLowerCase().includes(needle) ||
        s.title.toLowerCase().includes(needle) ||
        (s.origin ?? '').toLowerCase().includes(needle)
      )
    })
  }, [q, filter])

  const counts = useMemo(
    () => ({
      all: SOURCES.length,
      pool: SOURCES.filter((s) => !s.excluded && !s.quarantined).length,
      excluded: SOURCES.filter((s) => s.excluded).length,
      quarantined: SOURCES.filter((s) => s.quarantined).length,
    }),
    [],
  )

  return (
    <div className="mx-auto max-w-5xl px-4 py-10">
      <h1 className="text-3xl font-bold">Source catalog</h1>
      <p className="mt-2 text-sm text-neutral-500 dark:text-neutral-400">
        {SOURCES.length} sources recorded in <code>RAW/PROVENANCE.md</code>,
        joined with <code>CORPUS/MANIFEST.tsv</code> normalization stats and
        the mining-exclusion sets from <code>tools/mine_lemmas.py</code>.
      </p>

      <div className="mt-4 flex flex-wrap items-center gap-2">
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search file, title, origin…"
          className="w-72 rounded-md border border-neutral-300 bg-transparent px-3 py-1.5 text-sm outline-none focus:border-neutral-500 dark:border-neutral-700"
        />
        {(['all', 'pool', 'excluded', 'quarantined'] as Filter[]).map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={
              'rounded-md px-3 py-1.5 text-sm ' +
              (filter === f
                ? 'bg-neutral-900 text-white dark:bg-white dark:text-black'
                : 'border border-neutral-300 dark:border-neutral-700')
            }
          >
            {f} ({counts[f]})
          </button>
        ))}
      </div>

      <div className="mt-6 overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-neutral-300 text-xs uppercase tracking-wide text-neutral-500 dark:border-neutral-700">
            <tr>
              <th className="py-2 pr-4">File</th>
              <th className="py-2 pr-4">Title</th>
              <th className="py-2 pr-4">Origin</th>
              <th className="py-2 pr-4 text-right">Corpus lines</th>
              <th className="py-2">Status</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((s) => (
              <SourceRow key={s.file} s={s} />
            ))}
          </tbody>
        </table>
        {filtered.length === 0 && (
          <p className="mt-6 text-sm text-neutral-500">No matches.</p>
        )}
      </div>
    </div>
  )
}

function SourceRow({ s }: { s: SourceRecord }) {
  return (
    <tr className="border-b border-neutral-100 align-top dark:border-neutral-900">
      <td className="py-2 pr-4 font-mono text-xs">
        {s.url ? (
          <a href={s.url} className="underline decoration-dotted">
            {s.file}
          </a>
        ) : (
          s.file
        )}
      </td>
      <td className="py-2 pr-4">{s.title}</td>
      <td className="py-2 pr-4 text-xs text-neutral-500">{s.origin ?? '—'}</td>
      <td className="py-2 pr-4 text-right tabular-nums text-neutral-500">
        {s.corpus?.lines?.toLocaleString() ?? '—'}
      </td>
      <td className="py-2">
        {s.quarantined ? (
          <span className="rounded bg-red-100 px-2 py-0.5 text-xs text-red-800 dark:bg-red-950 dark:text-red-300">
            quarantined
          </span>
        ) : s.excluded ? (
          <span
            title={s.excluded}
            className="rounded bg-amber-100 px-2 py-0.5 text-xs text-amber-800 dark:bg-amber-950 dark:text-amber-300"
          >
            {s.excluded}
          </span>
        ) : (
          <span className="rounded bg-emerald-100 px-2 py-0.5 text-xs text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300">
            in pool
          </span>
        )}
      </td>
    </tr>
  )
}
