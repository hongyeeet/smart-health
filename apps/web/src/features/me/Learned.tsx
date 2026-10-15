/**
 * K2 — What Equinox has learnt (PRD F16).
 *
 * The agent only proposes. Here the person sees each thing it noticed, why it thinks so, and decides: confirm it, say it in their own
 * words, or delete it (a deleted idea is never proposed again). Four counts sit on top, then the list of things waiting for the person,
 * with the patterns from their history beside it. Nothing here gives advice.
 */
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useAiUsage, useDigest, useInsightsOverview, useLearned, useLearnedAction } from '@/data/hooks'
import type { LearnedFact } from '@/data/types'
import { cn } from '@/lib/cn'
import { Header, Screen } from '@/ui/layout'
import { Alert, Button, Card, EmptyState, Field, Skeleton } from '@/ui/primitives'
import { Bell, Brain, CheckCircle, Clock, ForkKnife, Footprints, type IconType } from '@/ui/icons'

type Kind = 'all' | 'doses' | 'meals' | 'checks'
type ListKind = Exclude<Kind, 'all'>

/** The barrier sentences end in a count such as "(43 times)". That count covers all time, while the other numbers are the last 30 days. */
const ALL_TIME_COUNT = /\((\d+) times?\)/

interface Row {
  fact: LearnedFact
  kind: ListKind
  category: string
  groupLabel: string
}

/** Which group a fact belongs to, from its key: dose habits and reasons, meal habits, check-ups. */
function kindOf(key: string): ListKind {
  if (key.startsWith('barrier.') || key.startsWith('routine.dose_timing')) return 'doses'
  if (key.startsWith('food.')) return 'meals'
  return 'checks'
}

/** One thing the agent noticed. The list version is the large card row; the pattern version is the compact row in the side card. */
function FactRow({ row, icon: Icon, pattern = false }: { row: Row; icon: IconType; pattern?: boolean }) {
  const { t } = useTranslation()
  const act = useLearnedAction()
  const f = row.fact
  const [editing, setEditing] = useState(false)
  const [text, setText] = useState(f.statement)
  const busy = act.isPending
  const confirmed = f.status === 'active'
  const pct = Math.round(f.confidence * 100)
  const statement = f.statement.replace(
    ALL_TIME_COUNT,
    (_m, n: string) => `(${n} ${Number(n) === 1 ? t('me.learned.time', 'time') : t('me.learned.times', 'times')}, ${t('me.learned.allTime', 'all time')})`,
  )
  const source = f.source === 'user' ? t('me.learned.ownWords', 'In your own words') : t('me.learned.noticedBy', 'Noticed by Equinox, {{pct}}% sure', { pct })

  const statusLabel = confirmed
    ? t('me.learned.confirmed', 'Confirmed')
    : pattern
      ? t('me.learned.notConfirmed', 'Not confirmed')
      : t('me.learned.waiting', 'Waiting for you')
  const pill = cn('flex-none rounded-chip px-2 py-0.5 text-micro font-bold', confirmed ? 'bg-ok-soft text-ok' : 'bg-brass-soft text-brass')

  const editBox = editing && (
    <div className="mt-2 flex flex-col gap-2">
      <Field label={t('me.learned.sayIt', 'Say it your way')} value={text} onChange={setText} multiline />
      <div className="flex flex-wrap gap-2">
        <Button
          size="md"
          className="!w-auto"
          disabled={busy || text.trim().length < 3}
          onClick={() => act.mutate({ id: f.id, action: 'edit', text }, { onSuccess: () => setEditing(false) })}
        >
          {t('me.learned.saveWording', 'Save my wording')}
        </Button>
        <Button
          size="md"
          variant="secondary"
          className="!w-auto"
          onClick={() => {
            setEditing(false)
            setText(f.statement)
          }}
        >
          {t('me.learned.cancel', 'Cancel')}
        </Button>
      </div>
    </div>
  )

  const actions = !editing && (
    <>
      {f.status === 'proposed' && (
        <Button size="md" className="!w-auto" icon={CheckCircle} disabled={busy} onClick={() => act.mutate({ id: f.id, action: 'confirm' })}>
          {t('me.learned.rightOne', 'That is right')}
        </Button>
      )}
      <Button size="md" variant="secondary" className="!w-auto" disabled={busy} onClick={() => setEditing(true)}>
        {t('me.learned.change', 'Change it')}
      </Button>
      <Button size="md" variant="ghost" className="!w-auto text-danger" disabled={busy} onClick={() => act.mutate({ id: f.id, action: 'delete' })}>
        {t('me.learned.delete', 'Delete')}
      </Button>
    </>
  )

  const error = act.isError && <Alert tone="danger">{t('me.learned.didNotSave', 'That did not save. Please try again.')}</Alert>

  if (pattern) {
    return (
      <div className="flex gap-2.5 border-t border-line py-3 first:border-t-0">
        <span className="flex h-[30px] w-[30px] flex-none items-center justify-center rounded-full bg-brand-soft text-brand">
          <Icon size={16} aria-hidden />
        </span>
        <div className="flex min-w-0 flex-1 flex-col gap-1">
          <div className="flex flex-wrap items-center gap-2">
            <p className="min-w-0 text-sub font-bold leading-snug">{statement}</p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <span className={pill}>{statusLabel}</span>
            <span className="text-micro text-ink3">{t('me.learned.patternSure', '{{pct}}% sure', { pct })}</span>
          </div>
          {editBox}
          {!editing && <div className="mt-1 flex flex-wrap gap-1.5">{actions}</div>}
          {error}
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-wrap gap-x-3.5 gap-y-2 border-t border-line py-3.5 first:border-t-0 sm:flex-nowrap">
      <span className="flex h-[34px] w-[34px] flex-none items-center justify-center rounded-full bg-brand-soft text-brand">
        <Icon size={18} aria-hidden />
      </span>
      <div className="flex min-w-0 basis-[calc(100%-3.5rem)] flex-col gap-1 sm:flex-1 sm:basis-auto">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-micro font-bold uppercase tracking-wide text-ink3">{row.groupLabel}</span>
          <span className={pill}>{statusLabel}</span>
        </div>
        <p className="text-body leading-snug text-ink">{statement}</p>
        <p className="text-sub text-ink2">{f.why}</p>
        <div className="mt-0.5 flex flex-wrap items-center gap-2.5">
          <div className="relative h-1.5 w-[90px] overflow-hidden rounded-full bg-well">
            <div className="absolute inset-y-0 left-0 bg-brand" style={{ width: `${pct}%` }} />
          </div>
          <span className="text-micro text-ink3">{source}</span>
        </div>
        {editBox}
        {error}
      </div>
      {!editing && <div className="flex w-full flex-none flex-row flex-wrap gap-1.5 pl-[3.125rem] sm:w-auto sm:flex-col sm:self-center sm:pl-0">{actions}</div>}
    </div>
  )
}

/** One line of AI use today: what it is, the calls used against that kind's own daily cap. A kind over its cap says so in plain words. */
export function AiUseToday() {
  const { t } = useTranslation()
  const { data: ai, isError, isLoading } = useAiUsage()
  const kindName = (provider: string): string => {
    switch (provider) {
      case 'vertex_vision':
        return t('me.learned.ai.vision', 'Photo and label reads')
      case 'vertex_generate':
        return t('me.learned.ai.generate', 'Text written for you')
      case 'vertex_embed':
        return t('me.learned.ai.embed', 'Search lookups')
      case 'jev':
        return t('me.learned.ai.jev', 'Safety checks')
      default:
        return t('me.learned.ai.other', 'Other AI use')
    }
  }
  const anyOver = ai?.providers.some((p) => p.overCap) ?? false
  return (
    <Card className="p-4">
      <div className="mb-2 flex items-baseline justify-between gap-3">
        <h2 className="text-body font-bold">{t('me.learned.aiToday', 'AI use today')}</h2>
        {ai && (
          <span className="text-micro text-ink3">
            {anyOver ? t('me.learned.aiSomePaused', 'Some paused') : t('me.learned.aiWithin', 'within daily limits')}
          </span>
        )}
      </div>
      {isLoading && !ai && <Skeleton className="h-16" />}
      {isError && !ai && <p className="text-sub text-ink3">{t('me.learned.aiLoadError', 'We could not load AI use today.')}</p>}
      {ai && ai.providers.length === 0 && <p className="text-sub text-ink3">{t('me.learned.aiNone', 'No AI use recorded today yet.')}</p>}
      {ai && ai.providers.length > 0 && (
        <ul className="flex flex-col">
          {ai.providers.map((p) => (
            <li key={p.provider} className="flex flex-col gap-0.5 border-t border-line py-2 first:border-t-0">
              <div className="flex items-center gap-2.5">
                <span className="min-w-0 flex-1 text-micro text-ink">{kindName(p.provider)}</span>
                <div className="relative h-1.5 w-20 flex-none overflow-hidden rounded-full bg-well">
                  <div
                    className="absolute inset-y-0 left-0 bg-info"
                    style={{ width: `${p.cap > 0 ? Math.min(100, Math.round((p.calls / p.cap) * 100)) : 0}%` }}
                  />
                </div>
                <span className="num w-16 flex-none text-right text-micro text-ink2">
                  {p.calls} / {p.cap}
                </span>
              </div>
              {p.overCap && <span className="text-micro text-ink3">{t('me.learned.aiPaused', 'Paused until tomorrow')}</span>}
            </li>
          ))}
        </ul>
      )}
    </Card>
  )
}

const FILTERS: { key: Kind; label: string }[] = [
  { key: 'all', label: 'All' },
  { key: 'doses', label: 'Doses' },
  { key: 'meals', label: 'Meals' },
  { key: 'checks', label: 'Check-ups' },
]

export function Learned() {
  const { t } = useTranslation()
  const { data, isError } = useLearned()
  const { data: digest } = useDigest()
  const [filter, setFilter] = useState<Kind>('all')

  const rows: Row[] = []
  const overview = useInsightsOverview(90)
  const patterns = overview.data?.patterns ?? []
  for (const g of data?.groups ?? []) {
    for (const f of g.facts) {
      const kind = kindOf(f.key)
      const groupLabel =
        kind === 'doses'
          ? t('me.learned.catDoses', 'Doses and reminders')
          : kind === 'meals'
            ? t('me.learned.catMeals', 'Your meals')
            : t('me.learned.catChecks', 'Check-ups')
      rows.push({ fact: f, kind, category: g.category, groupLabel })
    }
  }
  const everything = rows
  const waiting = everything.filter((r) => r.fact.status === 'proposed').length
  const confirmed = everything.filter((r) => r.fact.status === 'active').length
  const deleted = digest ? digest.lines.filter((l) => l.status === 'rejected').length : null
  const shown = rows.filter((r) => filter === 'all' || r.kind === filter)

  const iconFor = (r: Row): IconType => (r.kind === 'doses' ? Bell : r.kind === 'meals' ? ForkKnife : Clock)

  const tiles = [
    {
      value: String(waiting),
      label: t('me.learned.tileWaiting', 'Waiting for you'),
      status: waiting ? t('me.learned.tileWaitingSub', 'Check them below') : t('me.learned.tileAllChecked', 'All checked'),
      tone: waiting ? 'bg-brass-soft text-brass' : 'bg-ok-soft text-ok',
    },
    {
      value: String(confirmed),
      label: t('me.learned.tileConfirmed', 'Confirmed by you'),
      status: confirmed ? t('me.learned.tileInUse', 'In use') : t('me.learned.tileNoneYet', 'None yet'),
      tone: 'bg-ok-soft text-ok',
    },
    {
      value: String(patterns.length),
      label: t('me.learned.tilePatterns', 'Patterns in your history'),
      status: t('me.learned.tileNotProven', 'Not proven'),
      tone: 'bg-well text-ink2',
    },
    {
      value: deleted == null ? '–' : String(deleted),
      label: t('me.learned.tileDeleted', 'Deleted'),
      status: digest ? t('me.learned.tileDeletedWindow', 'Last {{n}} days', { n: digest.days }) : t('me.learned.noDataYet', 'No data yet'),
      tone: 'bg-well text-ink2',
    },
  ]

  return (
    <Screen wide>
      <Header
        title={t('me.learned.title', 'What Equinox has learnt')}
        back
        backTo="K1"
        sub={t('me.learned.sub', 'Everything it noticed about you, and why. You decide what stays.')}
      />

      <ul className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {tiles.map((tile) => (
          <li key={tile.label} className={cn('flex h-[78px] min-w-0 flex-col justify-center gap-px rounded-xl px-3 py-2.5', tile.tone)}>
            <span className="whitespace-nowrap text-[22px] font-bold leading-[26px]">{tile.value}</span>
            <span className="truncate text-micro text-ink2">{tile.label}</span>
            <span className="flex items-center gap-1.5 whitespace-nowrap text-micro font-bold">
              <span className="inline-block h-2 w-2 flex-none rounded-full bg-current" />
              {tile.status}
            </span>
          </li>
        ))}
      </ul>

      <div className="grid grid-cols-1 items-start gap-4 lg:grid-cols-[minmax(0,1fr)_332px] [&>*]:min-w-0">
        <section className="flex flex-col gap-2">
          <Card className="px-5 pb-3 pt-5">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <h2 className="text-body font-bold">{t('me.learned.waitingTitle', 'Waiting for you')}</h2>
              <div role="group" aria-label={t('me.learned.filterLabel', 'Show')} className="flex flex-wrap gap-1.5">
                {FILTERS.map((f) => {
                  const on = filter === f.key
                  const n = f.key === 'all' ? rows.length : rows.filter((r) => r.kind === f.key).length
                  return (
                    <button
                      key={f.key}
                      type="button"
                      aria-pressed={on}
                      onClick={() => setFilter(f.key)}
                      className={cn(
                        'press flex h-[34px] flex-none items-center gap-1.5 whitespace-nowrap rounded-full border-[1.5px] px-3.5 text-sub',
                        on ? 'border-brand bg-brand font-bold text-on-brand' : 'border-line bg-card text-ink',
                      )}
                    >
                      {t(`me.learned.filter.${f.key}`, f.label)} <span className="opacity-70">{n}</span>
                    </button>
                  )
                })}
              </div>
            </div>
            {isError && <Alert tone="warn">{t('me.learned.loadError', 'We could not load this just now.')}</Alert>}
            {!data && !isError && <Skeleton className="mt-3 h-40" />}
            {data && data.total === 0 && (
              <div className="mt-3">
                <EmptyState icon={Brain}>
                  {t('me.learned.empty', 'Nothing yet. As you log meals and doses, it will notice patterns and ask you to check them here.')}
                </EmptyState>
              </div>
            )}
            {data && data.total > 0 && (
              <div className="mt-2">
                {shown.length === 0 && <p className="py-4 text-sub text-ink3">{t('me.learned.nothingHere', 'Nothing in this group yet.')}</p>}
                {shown.map((r) => (
                  <FactRow key={r.fact.id} row={r} icon={iconFor(r)} />
                ))}
              </div>
            )}
          </Card>
          <p className="px-1 text-micro text-ink3">
            {t(
              'me.learned.notDiagnosis',
              'These are patterns in your own logs, not a diagnosis. If a delete is wrong for you, nothing is lost: it just stops being used.',
            )}
          </p>
        </section>

        <aside className="flex flex-col gap-4">
          <Card className="px-4 pb-2 pt-4">
            <div className="flex items-baseline justify-between gap-3">
              <h2 className="text-body font-bold">{t('me.learned.patternsTitle', 'Patterns in your history')}</h2>
              <span className="text-micro text-ink3">{t('me.learned.patternsFound', '{{n}} found', { n: patterns.length })}</span>
            </div>
            <p className="mb-1 mt-0.5 text-micro text-ink3">
              {t('me.learned.patternsSub', 'Two things that go together in your logs. They do not prove a cause.')}
            </p>
            {overview.data && patterns.length === 0 && <p className="py-3 text-sub text-ink3">{t('me.learned.patternsNone', 'No patterns yet.')}</p>}
            {!data && !isError && <Skeleton className="my-2 h-24" />}
            {patterns.map((p) => (
              <div key={p.key} className="flex min-h-[3.75rem] items-center gap-3 border-t border-line/60 py-2 first:border-t-0">
                <span className="flex h-[30px] w-[30px] flex-none items-center justify-center rounded-full bg-brand-soft text-brand" aria-hidden>
                  {p.key.includes('walk') ? <Footprints size={15} /> : <ForkKnife size={15} />}
                </span>
                <div className="min-w-0 flex-1">
                  <p className="text-sub leading-snug">{p.text}</p>
                  <div className="mt-1 flex items-center gap-2">
                    <div className="relative h-[5px] w-[60px] overflow-hidden rounded-[3px] bg-well">
                      <div
                        className="absolute inset-y-0 left-0 bg-brand/60"
                        style={{ width: `${Math.round((p.n / Math.max(...patterns.map((x) => x.n))) * 100)}%` }}
                      />
                    </div>
                    <span className="text-micro text-ink3">{t('me.learned.patternN', '{{n}} matched', { n: p.n })}</span>
                  </div>
                </div>
              </div>
            ))}
          </Card>
          <AiUseToday />
          <Card className="p-4 text-sub text-ink2">
            {t('me.learned.onlySuggests', 'It only suggests. It never changes your medicines, your numbers or its own safety rules.')}
          </Card>
        </aside>
      </div>
    </Screen>
  )
}
