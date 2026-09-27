import entries from '#/data/entries.json'
import englishIndex from '#/data/english-index.json'
import sources from '#/data/sources.json'
import type { DictEntry, EnglishIndexEntry, SourceRecord } from './types'

export const ENTRIES = entries as DictEntry[]
export const ENGLISH_INDEX = englishIndex as EnglishIndexEntry[]
export const SOURCES = sources as SourceRecord[]

/** Esperanto alphabet ordering: a b c ĉ d e f g ĝ h ĥ i j ĵ k l m n o p r s ŝ t u ŭ v z */
const ALPHA = 'abcĉdefgĝhĥijĵklmnoprsŝtuŭvz'
const RANK = new Map([...ALPHA].map((c, i) => [c, i]))

export function epoSortKey(w: string): number[] {
  return [...w.toLowerCase()].map((c) => RANK.get(c) ?? 99)
}

export function searchEntries(
  query: string,
  opts: { pos?: string; source?: string; limit?: number } = {},
): DictEntry[] {
  const q = query.trim().toLowerCase()
  const limit = opts.limit ?? 50
  const out: DictEntry[] = []
  for (const e of ENTRIES) {
    if (opts.pos && e.pos !== opts.pos) continue
    if (opts.source && !e.source.startsWith(opts.source)) continue
    if (q) {
      const w = e.word.toLowerCase()
      if (
        !w.startsWith(q) &&
        !w.includes(q) &&
        !e.gloss_en.toLowerCase().includes(q)
      )
        continue
    }
    out.push(e)
    if (out.length >= limit) break
  }
  return out
}

export const POS_LIST = Array.from(
  new Set(ENTRIES.map((e) => e.pos)),
).sort()
export const SOURCE_LIST = Array.from(
  new Set(ENTRIES.map((e) => e.source)),
).sort()
