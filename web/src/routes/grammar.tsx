import { createFileRoute } from '@tanstack/react-router'
import { useMemo, useState } from 'react'
import grammarMd from '#/data/grammar.md?raw'

export const Route = createFileRoute('/grammar')({
  component: GrammarPage,
})

/**
 * Minimal markdown renderer for the grammar guide. The guide uses headings,
 * prose, tables, bold/italic, inline code and em-dash lists — enough that a
 * dependency-free renderer keeps the app lean; swap for a full markdown
 * renderer if the guide grows fancier constructs.
 */
function renderMarkdown(md: string): string {
  const esc = (s: string) =>
    s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  const inline = (s: string) =>
    esc(s)
      .replace(/`([^`]+)`/g, '<code>$1</code>')
      .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
      .replace(/\*([^*]+)\*/g, '<em>$1</em>')

  const lines = md.split('\n')
  const out: string[] = []
  let i = 0
  while (i < lines.length) {
    const line = lines[i]
    if (!line.trim()) {
      i++
      continue
    }
    // table block
    if (line.trim().startsWith('|')) {
      const rows: string[][] = []
      while (i < lines.length && lines[i].trim().startsWith('|')) {
        const cells = lines[i].trim().replace(/^\|/, '').replace(/\|$/, '').split('|').map((c) => c.trim())
        if (!cells.every((c) => /^:?-{2,}:?$/.test(c) || c === '')) rows.push(cells)
        i++
      }
      out.push(
        '<table><thead><tr>' +
          rows[0].map((c) => `<th>${inline(c)}</th>`).join('') +
          '</tr></thead><tbody>' +
          rows
            .slice(1)
            .map((r) => '<tr>' + r.map((c) => `<td>${inline(c)}</td>`).join('') + '</tr>')
            .join('') +
          '</tbody></table>',
      )
      continue
    }
    // headings
    const h = line.match(/^(#{1,4})\s+(.*)$/)
    if (h) {
      const level = h[1].length
      // anchor top-level numbered sections (## 2. Morfologio — ...) as section-N
      const num = h[2].match(/^(\d+(?:\.\d+)?)\./)
      const anchor = num && level === 2 ? ` id="section-${num[1]}"` : ''
      out.push(`<h${level}${anchor}>${inline(h[2])}</h${level}>`)
      i++
      continue
    }
    // list items
    if (/^\s*[-*]\s+/.test(line) || /^\s*\d+\.\s+/.test(line)) {
      const items: string[] = []
      while (i < lines.length && (/^\s*[-*]\s+/.test(lines[i]) || /^\s*\d+\.\s+/.test(lines[i]))) {
        items.push(lines[i].replace(/^\s*(?:[-*]|\d+\.)\s+/, ''))
        i++
      }
      out.push('<ul>' + items.map((t) => `<li>${inline(t)}</li>`).join('') + '</ul>')
      continue
    }
    // paragraph: gather until blank/structural line
    const para: string[] = []
    while (
      i < lines.length &&
      lines[i].trim() &&
      !lines[i].trim().startsWith('|') &&
      !/^#{1,4}\s/.test(lines[i]) &&
      !/^\s*[-*]\s+/.test(lines[i])
    ) {
      para.push(lines[i])
      i++
    }
    out.push(`<p>${inline(para.join(' '))}</p>`)
  }
  return out.join('\n')
}

const SECTIONS = [
  { n: '1', label: 'Fundamentoj' },
  { n: '2', label: 'Morfologio' },
  { n: '3', label: 'Sintakso' },
  { n: '4', label: 'Fonologio kaj Ortografio' },
  { n: '5', label: 'Pragmatiko kaj Registro' },
  { n: '6', label: 'Uzado' },
]

function GrammarPage() {
  const html = useMemo(() => renderMarkdown(grammarMd), [])
  const [active, setActive] = useState('1')

  return (
    <div className="mx-auto flex max-w-6xl gap-8 px-4 py-10">
      <nav className="hidden w-48 shrink-0 md:block">
        <div className="sticky top-20 space-y-1 text-sm">
          {SECTIONS.map((s) => (
            <a
              key={s.n}
              href={`#section-${s.n}`}
              onClick={() => setActive(s.n)}
              className={
                'block rounded px-2 py-1 ' +
                (active === s.n
                  ? 'bg-neutral-100 font-semibold dark:bg-neutral-800'
                  : 'text-neutral-600 hover:bg-neutral-50 dark:text-neutral-400 dark:hover:bg-neutral-900')
              }
            >
              §{s.n} {s.label}
            </a>
          ))}
        </div>
      </nav>
      <article
        className="prose prose-neutral dark:prose-invert max-w-3xl"
        dangerouslySetInnerHTML={{ __html: html }}
      />
    </div>
  )
}
