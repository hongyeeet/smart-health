import { useTranslation } from 'react-i18next'
import type { WebSource } from '@/data/types'

/**
 * The web pages behind a medicine explanation or a clash alert, one per site (the same site can come back twice with two addresses).
 * Shown by site name. A link is shown only when there is a page to open: Google's redirect link opens the real page and is labelled as
 * such; drug-label data from openFDA has no page and is plain text.
 */
export function uniqueSources(sources: WebSource[]): WebSource[] {
  const seen = new Set<string>()
  return sources.filter((s) => {
    const key = s.title.trim().toLowerCase().replace(/^www\./, '')
    if (seen.has(key)) return false
    seen.add(key)
    return true
  })
}

export function SourceItem({ s, linkClass }: { s: WebSource; linkClass?: string }) {
  const { t } = useTranslation()
  const url = s.url || ''
  if (!/^https?:\/\//i.test(url)) return <span className="break-words">{s.title}</span>
  if (url.includes('vertexaisearch.cloud.google.com')) {
    return (
      <a href={url} target="_blank" rel="noopener noreferrer" className={linkClass}>
        {t('sources.viaGoogle', '{{name}}, opens via Google', { name: s.title })}
      </a>
    )
  }
  return (
    <span className="break-words">
      {s.title}{' '}
      <a href={url} target="_blank" rel="noopener noreferrer" className={linkClass}>
        {t('sources.openPage', 'Open page')}
      </a>
    </span>
  )
}
