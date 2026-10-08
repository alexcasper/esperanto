export interface DictEntry {
  word: string
  pos: string
  gloss_en: string
  gloss_fr?: string
  root?: string
  morphology?: Record<string, unknown>
  source: string
  dated_gloss?: string
  grammar_refs?: { section: string; topic: string }[]
  english_headwords?: string[]
  attestation?: {
    count: number
    sources: number
    sources_lit?: number
    sources_wiki?: number
  }
  citations?: { source: string; text: string }[]
}

export interface SourceRecord {
  file: string
  title: string
  sha?: string
  origin?: string
  url?: string
  quarantined?: boolean
  excluded?: string
  corpus?: {
    method: string
    lines: number | null
    sha: string
    fixes?: string
  }
}

export interface EnglishIndexEntry {
  english: string
  esperanto: string[]
  source: string
}
