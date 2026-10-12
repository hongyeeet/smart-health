import { useState, type ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { useGo } from '@/app/navigation'
import { ROUTES, type RouteId } from '@/app/routeIds'
import { cn } from '@/lib/cn'
import { ProseLink } from '@/ui/primitives'
import { Check, Warning } from '@/ui/icons'
import { useAddDoctorQuestion, type ChatSource, type Item } from './api'

/** A word or phrase in a reply that opens a screen. */
function InlineLink({ to, children }: { to: RouteId; children: ReactNode }) {
  const go = useGo()
  return <ProseLink onClick={() => go(to)}>{children}</ProseLink>
}

/** The offer to add the person's question to their doctor questions: the whole sentence is the link, and it says so once it is done. */
function DoctorQuestionLink({ text, children }: { text: string; children: ReactNode }) {
  const { t } = useTranslation()
  const add = useAddDoctorQuestion()
  const [done, setDone] = useState(false)
  if (done)
    return (
      <span className="inline-flex items-center gap-1 font-semibold text-brand" role="status">
        <Check size={16} aria-hidden /> {t('chat.addedToQuestions', 'Added to your doctor questions')}
      </span>
    )
  return (
    <ProseLink disabled={add.isPending} onClick={() => add.mutate(text, { onSuccess: () => setDone(true) })}>
      {children}
    </ProseLink>
  )
}

/**
 * The reply as words with links in them. The server marks the words that open a screen as [[K11|Review suggestions]]; a marker that does
 * not name a screen of the app shows as plain words, so a wrong marker can never produce a dead link.
 */
export function linked(text: string, askText?: string): ReactNode[] {
  const out: ReactNode[] = []
  const re = /\[\[([A-Z][A-Z0-9]*)\|([^\]]+)\]\]/g
  let at = 0
  let m: RegExpExecArray | null
  while ((m = re.exec(text))) {
    if (m.index > at) out.push(text.slice(at, m.index))
    out.push(
      m[1] === 'DQ' && askText ? (
        <DoctorQuestionLink key={m.index} text={askText}>{m[2]}</DoctorQuestionLink>
      ) : m[1] in ROUTES ? (
        <InlineLink key={m.index} to={m[1] as RouteId}>{m[2]}</InlineLink>
      ) : (
        m[2]
      ),
    )
    at = m.index + m[0].length
  }
  if (at < text.length) out.push(text.slice(at))
  return out
}

/** "Where this comes from: Your glucose, Your doses and Your medicines." with each name a link. */
function SourcesLine({ sources }: { sources: ChatSource[] }) {
  const { t, i18n } = useTranslation()
  const parts = sources.map((s) => ({ s, key: s.to }))
  let list: ReactNode[]
  try {
    list = new Intl.ListFormat(i18n.language, { style: 'long', type: 'conjunction' })
      .formatToParts(parts.map((p) => p.key))
      .map((p, i) => (p.type === 'element' ? <InlineLink key={i} to={p.value as RouteId}>{parts.find((x) => x.key === p.value)?.s.label}</InlineLink> : p.value))
  } catch {
    list = parts.flatMap((p, i) => [i ? ', ' : '', <InlineLink key={p.key} to={p.key as RouteId}>{p.s.label}</InlineLink>])
  }
  return (
    <span className="mt-2 block text-sub text-ink2">
      {t('chat.whereFrom', 'Where this comes from')}: {list}.
    </span>
  )
}

/** One message. The person's words sit on the right; Smart Health's on the left. An urgent reply says so in words and shape, not colour alone. */
export function Bubble({ item, sources, askText }: { item: Item; sources?: ChatSource[]; askText?: string }) {
  const { t } = useTranslation()
  const mine = item.role === 'user'
  const urgent = item.kind === 'urgent'
  return (
    <div className={cn('flex', mine ? 'justify-end' : 'justify-start')}>
      <div
        className={cn(
          'max-w-[88%] whitespace-pre-line break-words rounded-card px-4 py-3 text-body',
          mine ? 'bg-brand text-on-brand' : urgent ? 'border-2 border-danger bg-danger-soft text-ink' : 'border border-line bg-card text-ink',
        )}
      >
        {!mine && <span className="sr-only">{t('chat.saysPrefix', 'Smart Health says:')} </span>}
        {urgent && (
          <span className="mb-1 flex items-center gap-1.5 font-bold">
            <Warning size={20} weight="fill" aria-hidden /> {t('chat.urgentTag', 'Urgent')}
          </span>
        )}
        {mine ? item.text : linked(item.text, askText)}
        {!mine && sources && sources.length > 0 && <SourcesLine sources={sources} />}
      </div>
    </div>
  )
}

/** Shown while the answer is on its way. Still dots when the person asks for less motion. */
export function TypingIndicator() {
  const { t } = useTranslation()
  return (
    <div role="status" className="flex">
      <span className="sr-only">{t('chat.typing', 'Smart Health is typing')}</span>
      <div className="flex items-center gap-1.5 rounded-card border border-line bg-card px-4 py-4" aria-hidden>
        {[0, 1, 2].map((n) => (
          <span key={n} className="h-2.5 w-2.5 rounded-full bg-ink3 motion-safe:animate-pulse" style={{ animationDelay: `${n * 180}ms` }} />
        ))}
      </div>
    </div>
  )
}

/** An urgent reply ends with a link to the urgent screen: red and underlined so it stands out, but still a link in the text, not a button. */
export function Actions({ item }: { item: Item }) {
  const go = useGo()
  const urgent = (item.actions ?? []).find((a) => a.kind === 'open' && a.to === 'J1')
  if (!urgent) return null
  return (
    <p className="max-w-[88%] px-1 text-body">
      <button type="button" onClick={() => go('J1')} className="press inline cursor-pointer p-0 text-left font-bold text-danger underline decoration-danger underline-offset-[3px]">
        {urgent.label}
      </button>
    </p>
  )
}
