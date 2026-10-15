import { useEffect, useState, type ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { useGo } from '@/app/navigation'
import { ROUTES, type RouteId } from '@/app/routeIds'
import { cn } from '@/lib/cn'
import { ProseLink } from '@/ui/primitives'
import { Check, Warning } from '@/ui/icons'
import { useAddDoctorQuestion, type ChatRoute, type ChatSource, type Item } from './api'

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

/**
 * A reply as paragraphs and bullet lists. The server writes the summary as "- " lines (three short bullets) and then the sentences it always
 * adds (where to look in the app, a doctor question) and a warm closing line, each as its own paragraph. A line that is not a bullet stays
 * a plain line. Links inside any of them still work through `linked`.
 */
function Prose({ text, askText }: { text: string; askText?: string }) {
  const blocks = text.split(/\n{2,}/).map((b) => b.trim()).filter(Boolean)
  return (
    <div className="flex flex-col gap-2.5">
      {blocks.map((block, bi) => {
        const runs: { bullets: boolean; lines: string[] }[] = []
        for (const line of block.split('\n')) {
          const bullet = line.startsWith('- ')
          const last = runs[runs.length - 1]
          if (last && last.bullets === bullet) last.lines.push(bullet ? line.slice(2) : line)
          else runs.push({ bullets: bullet, lines: [bullet ? line.slice(2) : line] })
        }
        return (
          <div key={bi} className={cn('flex flex-col gap-1.5', bi === 0 && blocks.length > 1 && !block.startsWith('- ') && 'font-semibold')}>
            {runs.map((run, ri) =>
              run.bullets ? (
                <ul key={ri} className="flex flex-col gap-2">
                  {run.lines.map((l, li) => (
                    <li key={li} className="flex gap-2.5">
                      <span className="mt-[0.6em] h-2 w-2 flex-none rounded-full bg-brand" aria-hidden />
                      <span className="min-w-0">{linked(l, askText)}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p key={ri}>{linked(run.lines.join('\n'), askText)}</p>
              ),
            )}
          </div>
        )
      })}
    </div>
  )
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

/** One message. The person's words sit on the right; Equinox's on the left. An urgent reply says so in words and shape, not colour alone. */
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
        {!mine && <span className="sr-only">{t('chat.saysPrefix', 'Equinox says:')} </span>}
        {urgent && (
          <span className="mb-1 flex items-center gap-1.5 font-bold">
            <Warning size={20} weight="fill" aria-hidden /> {t('chat.urgentTag', 'Urgent')}
          </span>
        )}
        {mine ? item.text : <Prose text={item.text} askText={askText} />}
        {!mine && sources && sources.length > 0 && <SourcesLine sources={sources} />}
      </div>
    </div>
  )
}

/** What the question is about, by its words: which of the person's own records the answer will read. Only used to word the waiting steps. */
export function topicsOf(question: string, t: (k: string, d: string) => string): string[] {
  const q = question.toLowerCase()
  const out: string[] = []
  const add = (re: RegExp, key: string, en: string) => re.test(q) && out.push(t(key, en))
  add(/glucose|sugar|reading|cgm|a1c|hba1c|spike/, 'chat.think.topic.glucose', 'glucose readings')
  add(/meal|food|eat|ate|diet|calor|carb|salt|sodium|lunch|dinner|breakfast|snack|dish/, 'chat.think.topic.meals', 'meals')
  add(/medic|dose|tablet|pill|metformin|stock|refill/, 'chat.think.topic.meds', 'medicines and doses')
  add(/step|walk|exercise|workout|activity|active/, 'chat.think.topic.activity', 'activity')
  add(/sleep|tired|rest/, 'chat.think.topic.sleep', 'sleep')
  add(/blood pressure|pressure|bp/, 'chat.think.topic.bp', 'blood pressure')
  add(/heart|pulse|spo2|oxygen/, 'chat.think.topic.heart', 'heart rate and oxygen')
  add(/symptom|pain|dizzy|thirst|headache|feel/, 'chat.think.topic.symptoms', 'symptoms you logged')
  add(/doctor|appointment|visit|clinic|check-?up|screening/, 'chat.think.topic.care', 'visits and doctor questions')
  return out.length ? out : [t('chat.think.topic.logs', 'your logs')]
}

/**
 * Shown while the answer is on its way: ONE line that changes as the assistant works (reading, accessing the data, comparing, writing, almost done),
 * with a soft shimmer, like a chat that is thinking out loud. It stays on "Almost done" until the answer arrives. With reduced motion there is no shimmer,
 * spinner or fade, only the words changing. The words follow the question's topic, so "accessing your meals" is shown only for a question about meals.
 */
export function ThinkingSteps({ question, route }: { question: string; route: ChatRoute | null }) {
  const { t } = useTranslation()
  const topics = topicsOf(question, (k, d) => t(k, d))
  const list = new Intl.ListFormat(undefined, { style: 'long', type: 'conjunction' }).format(topics)
  // the first words, before the server has said what kind of request this is
  const start = [t('chat.think.s1', 'Reading your question'), t('chat.think.sroute', 'Working out what you are asking')]
  const done = t('chat.think.s6', 'Almost done')
  const byRoute: Record<ChatRoute, string[]> = {
    // the person's own records
    personal: [
      t('chat.think.p1', 'Searching your personal data: {{list}}', { list }),
      t('chat.think.s3', 'Comparing with your own usual numbers'),
      t('chat.think.s4', 'Writing a simple summary for you'),
      t('chat.think.s5', 'Checking it is safe to show'),
    ],
    // meals and lighter alternatives
    food: [
      t('chat.think.f1', 'Searching your meals and the Singapore food list'),
      t('chat.think.f2', 'Finding lighter alternatives you could swap in'),
      t('chat.think.s4', 'Writing a simple summary for you'),
      t('chat.think.s5', 'Checking it is safe to show'),
    ],
    // ideas from what Equinox has learned
    ideas: [
      t('chat.think.i1', 'Looking at what Equinox has learned about you'),
      t('chat.think.i2', 'Matching it with your recent days'),
      t('chat.think.i3', 'Picking small changes you could try'),
      t('chat.think.s5', 'Checking it is safe to show'),
    ],
    // general health reading, not the person's own numbers
    knowledge: [
      t('chat.think.k1', 'Looking through trusted health guidance'),
      t('chat.think.k2', 'Picking out what is relevant to you'),
      t('chat.think.s4', 'Writing a simple summary for you'),
      t('chat.think.s5', 'Checking it is safe to show'),
    ],
    safety: [t('chat.think.sf1', 'Checking this question carefully'), t('chat.think.sf2', 'Preparing a careful reply')],
    quick: [t('chat.think.q1', 'Thinking')],
    urgent: [t('chat.think.u1', 'Checking what you need right now')],
  }
  const steps = route ? [...(route === 'quick' || route === 'urgent' ? [] : start.slice(0, 1)), ...byRoute[route], ...(route === 'quick' || route === 'urgent' ? [] : [done])] : start
  const [at, setAt] = useState(0)
  // a step never moves backwards: when the route arrives and the list is replaced, keep going from where the words had got to
  useEffect(() => {
    if (at >= steps.length - 1) return
    const id = window.setTimeout(() => setAt((n) => Math.min(n + 1, steps.length - 1)), at === 0 ? 1100 : 1500)
    return () => window.clearTimeout(id)
  }, [at, steps.length, route])
  const shown = steps[Math.min(at, steps.length - 1)]
  return (
    <div role="status" aria-live="polite" className="flex">
      <div className="flex max-w-[88%] items-center gap-3 rounded-card border border-line bg-card px-4 py-3 text-body">
        <span className="h-4 w-4 flex-none rounded-full border-2 border-brand/30 border-t-brand motion-safe:animate-spin" aria-hidden />
        <span key={shown} className="motion-safe:animate-[fadeUp_0.35s_ease-out]">
          <span className="think-shimmer">{shown}…</span>
        </span>
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
