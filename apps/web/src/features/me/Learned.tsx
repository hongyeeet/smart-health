/**
 * K2 — What Smart Health has learned (PRD F16).
 *
 * The agent only proposes. Here the person sees each thing it noticed, why it thinks so, and decides: confirm it, say it in their own
 * words, or delete it (a deleted idea is never proposed again). "What gets in the way" starts with a row of numbers from the database.
 * The week's digest shows the counts. Nothing here gives advice.
 */
import { useState } from 'react'
import { Trans, useTranslation } from 'react-i18next'
import { useAiUsage, useDigest, useLearned, useLearnedAction } from '@/data/hooks'
import type { LearnedFact } from '@/data/types'
import { cn } from '@/lib/cn'
import { Header, Screen } from '@/ui/layout'
import { Alert, Button, Card, EmptyState, Field, SectionTitle, Skeleton } from '@/ui/primitives'
import { Brain, CheckCircle, Info } from '@/ui/icons'
import { BarrierKpis } from './learned/BarrierKpis'

const BOLD = { b: <b className="num" /> }

/** The barrier sentences end in a count such as "(43 times)". That count covers all time, while the KPI row above is the last 30 days. */
const ALL_TIME_COUNT = /\((\d+) times?\)/

function FactCard({ f }: { f: LearnedFact }) {
  const { t } = useTranslation()
  const act = useLearnedAction()
  const statement = f.statement.replace(ALL_TIME_COUNT, (_m, n: string) => `(${n} ${Number(n) === 1 ? t('me.learned.time', 'time') : t('me.learned.times', 'times')}, ${t('me.learned.allTime', 'all time')})`)
  const [editing, setEditing] = useState(false)
  const [text, setText] = useState(f.statement)
  const busy = act.isPending
  const source = f.source === 'user' ? t('me.learned.ownWords', 'In your own words') : t('me.learned.noticedBy', 'Noticed by Smart Health, {{pct}}% sure', { pct: Math.round(f.confidence * 100) })
  return (
    <Card className="flex h-full flex-col gap-2">
      <div className="flex items-start justify-between gap-3">
        <p className="min-w-0 text-body font-bold leading-snug">{statement}</p>
        <span className={cn('flex-none rounded-chip px-2 py-0.5 text-micro font-bold', f.status === 'active' ? 'bg-ok-soft text-ok' : 'bg-brass-soft text-brass')}>
          {f.status === 'active' ? t('me.learned.confirmed', 'Confirmed') : t('me.learned.waiting', 'Waiting for you')}
        </span>
      </div>
      <p className="text-sub text-ink2">{f.why}</p>
      <p className="text-micro text-ink3">{t('me.learned.factMeta', '{{source}} · version {{version}}', { source, version: f.version })}</p>
      {editing && (
        <div className="flex flex-col gap-2">
          <Field label={t('me.learned.sayIt', 'Say it your way')} value={text} onChange={setText} multiline />
          <div className="flex flex-wrap gap-2">
            <Button size="md" className="!w-auto" disabled={busy || text.trim().length < 3} onClick={() => act.mutate({ id: f.id, action: 'edit', text }, { onSuccess: () => setEditing(false) })}>
              {t('me.learned.saveWording', 'Save my wording')}
            </Button>
            <Button size="md" variant="secondary" className="!w-auto" onClick={() => { setEditing(false); setText(f.statement) }}>
              {t('me.learned.cancel', 'Cancel')}
            </Button>
          </div>
        </div>
      )}
      {!editing && (
        <div className="mt-auto flex flex-wrap gap-2 pt-1">
          {f.status === 'proposed' && (
            <Button size="md" className="!w-auto" icon={CheckCircle} disabled={busy} onClick={() => act.mutate({ id: f.id, action: 'confirm' })}>
              {t('me.learned.rightOne', 'That is right')}
            </Button>
          )}
          <Button size="md" variant="secondary" className="!w-auto" disabled={busy} onClick={() => setEditing(true)}>
            {t('me.learned.change', 'Change it')}
          </Button>
          <Button size="md" variant="ghost" className="!w-auto" disabled={busy} onClick={() => act.mutate({ id: f.id, action: 'delete' })}>
            {t('me.learned.delete', 'Delete')}
          </Button>
        </div>
      )}
      {act.isError && <Alert tone="danger">{t('me.learned.didNotSave', 'That did not save. Please try again.')}</Alert>}
    </Card>
  )
}

/**
 * AI use today, one line per kind of AI call, with that kind's own count and cap from the usage endpoint. A kind that has used its
 * cap says so in plain words. Nothing here is a fixed number: the counts and caps come from the server.
 */
function AiUseToday() {
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
  return (
    <div className="flex flex-col gap-1.5">
      <p className="text-sub font-bold text-ink2">{t('me.learned.aiToday', 'AI use today')}</p>
      {isLoading && !ai && <Skeleton className="h-12" />}
      {isError && !ai && <p className="text-sub text-ink3">{t('me.learned.aiLoadError', 'We could not load AI use today.')}</p>}
      {ai && ai.providers.length === 0 && <p className="text-sub text-ink3">{t('me.learned.aiNone', 'No AI use recorded today yet.')}</p>}
      {ai && ai.providers.length > 0 && (
        <ul className="flex flex-col text-sub text-ink2">
          {ai.providers.map((p) => (
            <li key={p.provider} className="flex flex-wrap items-baseline justify-between gap-x-3 border-b border-line py-1.5 last:border-b-0">
              <span>
                <Trans
                  i18nKey="me.learned.aiLine"
                  defaults="{{kind}}: <b>{{calls}}</b> of <b>{{cap}}</b> today"
                  values={{ kind: kindName(p.provider), calls: p.calls, cap: p.cap }}
                  components={BOLD}
                />
              </span>
              {p.overCap && <span className="text-ink3">{t('me.learned.aiPaused', 'Paused until tomorrow')}</span>}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

function Digest() {
  const { t } = useTranslation()
  const { data } = useDigest()
  if (!data) return <Skeleton className="h-40" />
  const r = data.reminders
  return (
    <Card tone="hero" className="flex flex-col gap-3">
      <SectionTitle>{t('me.learned.thisWeek', 'This week')}</SectionTitle>
      <div className="grid gap-4 lg:grid-cols-2 lg:gap-8 [&>*]:min-w-0">
      <div className="flex flex-col gap-3">
      <ul className="flex flex-col gap-1.5 text-body">
        <li>
          {data.newFacts === 1 ? (
            <Trans i18nKey="me.learned.noticedOne" defaults="<b>{{n}}</b> thing noticed or changed" values={{ n: data.newFacts }} components={BOLD} />
          ) : (
            <Trans i18nKey="me.learned.noticedMany" defaults="<b>{{n}}</b> things noticed or changed" values={{ n: data.newFacts }} components={BOLD} />
          )}
        </li>
        <li>
          <Trans
            i18nKey="me.learned.reminderCounts"
            defaults="<b>{{sent}}</b> reminders sent, <b>{{opened}}</b> opened, <b>{{acted}}</b> acted on"
            values={{ sent: r.sent, opened: r.opened, acted: r.acted }}
            components={BOLD}
          />
        </li>
        <li>
          <Trans
            i18nKey="me.learned.suggestionCounts"
            defaults="<b>{{chosen}}</b> of <b>{{shown}}</b> suggestions chosen by you"
            values={{ chosen: data.suggestions.chosen, shown: data.suggestions.shown }}
            components={BOLD}
          />
        </li>
        <li>
          <Trans
            i18nKey="me.learned.guardCounts"
            defaults="Safety checks on its own wording: <b>{{passed}}</b> passed, <b>{{blocked}}</b> blocked"
            values={{ passed: data.guard.passed, blocked: data.guard.blocked }}
            components={BOLD}
          />
        </li>
      </ul>
      {data.topSuggestions.length > 0 && (
        <div>
          <p className="text-sub font-bold text-ink2">{t('me.learned.learningFrom', 'Suggestions it is learning from')}</p>
          <ul className="text-sub text-ink2">
            {data.topSuggestions.map((s, i) => (
              <li key={i}>{t('me.learned.suggestionLine', '{{name}}: shown {{shown}}, chosen {{chosen}}', { name: s.name, shown: s.shown, chosen: s.chosen })}</li>
            ))}
          </ul>
        </div>
      )}
      </div>
      <AiUseToday />
      </div>
      <p className="text-sub text-ink3">{t('me.learned.onlySuggests', 'It only suggests. It never changes your medicines, your numbers or its own safety rules.')}</p>
    </Card>
  )
}

export function Learned() {
  const { t } = useTranslation()
  const { data, isError } = useLearned()
  return (
    <Screen>
      <Header title={t('me.learned.title', 'What Smart Health has learned')} back backTo="K1" sub={t('me.learned.sub', 'Everything it noticed about you, and why. You decide what stays.')} />
      <Digest />
      <section className="flex flex-col gap-3">
        <SectionTitle>{t('me.learned.barrierTitle', 'What gets in the way')}</SectionTitle>
        <BarrierKpis />
      </section>
      {isError && <Alert tone="warn">{t('me.learned.loadError', 'We could not load this just now.')}</Alert>}
      {!data && !isError && <Skeleton className="h-40" />}
      {data && data.total === 0 && (
        <EmptyState icon={Brain}>
          {t('me.learned.empty', 'Nothing yet. As you log meals and doses, it will notice patterns and ask you to check them here.')}
        </EmptyState>
      )}
      {data?.groups.map((g) => (
        <section key={g.category} className="flex flex-col gap-3">
          <SectionTitle>{g.category === 'barrier' ? t('me.learned.barrierIdeas', 'Ideas about what gets in the way') : g.label}</SectionTitle>
          <div className="grid grid-cols-1 gap-3 lg:grid-cols-2 [&>*]:min-w-0">
            {g.facts.map((f) => (
              <FactCard key={f.id} f={f} />
            ))}
          </div>
        </section>
      ))}
      <Alert tone="info" icon={Info}>
        {t('me.learned.notDiagnosis', 'These are patterns in your own logs, not a diagnosis. If a delete is wrong for you, nothing is lost: it just stops being used.')}
      </Alert>
    </Screen>
  )
}
