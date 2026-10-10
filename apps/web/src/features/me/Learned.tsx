/**
 * K2 — What Smart Health has learned (PRD F16).
 *
 * The agent only proposes. Here the person sees each thing it noticed, why it thinks so, and decides: confirm it, say it in their own
 * words, or delete it (a deleted idea is never proposed again). The week's digest shows everything it did, and the audit list shows
 * the runs behind it. Nothing here gives advice.
 */
import { useState } from 'react'
import { Trans, useTranslation } from 'react-i18next'
import { useAiUsage, useAudit, useDigest, useLearned, useLearnedAction } from '@/data/hooks'
import type { LearnedFact } from '@/data/types'
import { cn } from '@/lib/cn'
import { Header, Screen } from '@/ui/layout'
import { Alert, Button, Card, EmptyState, Field, SectionTitle, Skeleton, TextLink } from '@/ui/primitives'
import { Brain, CheckCircle, Info } from '@/ui/icons'

const clock = (iso: string) => new Date(iso).toLocaleString('en-US', { day: 'numeric', month: 'short', hour: 'numeric', minute: '2-digit' })
/** Bold numbers in the digest. The sentence itself is translated, so the number can sit anywhere in it. */
const BOLD = { b: <b className="num" /> }

function FactCard({ f }: { f: LearnedFact }) {
  const { t } = useTranslation()
  const act = useLearnedAction()
  const [editing, setEditing] = useState(false)
  const [text, setText] = useState(f.statement)
  const busy = act.isPending
  const source = f.source === 'user' ? t('me.learned.ownWords', 'In your own words') : t('me.learned.noticedBy', 'Noticed by Smart Health, {{pct}}% sure', { pct: Math.round(f.confidence * 100) })
  return (
    <Card className="flex flex-col gap-2">
      <div className="flex items-start justify-between gap-3">
        <p className="min-w-0 text-body font-bold leading-snug">{f.statement}</p>
        <span className={cn('flex-none rounded-chip px-2 py-0.5 text-micro font-bold', f.status === 'active' ? 'bg-ok-soft text-ok' : 'bg-brass-soft text-brass')}>
          {f.status === 'active' ? t('me.learned.confirmed', 'Confirmed') : t('me.learned.waiting', 'Waiting for you')}
        </span>
      </div>
      <p className="text-sub text-ink2">{f.why}</p>
      <p className="text-micro text-ink3">{t('me.learned.factMeta', '{{source}} · version {{version}}', { source, version: f.version })}</p>
      {editing && (
        <div className="flex flex-col gap-2">
          <Field label={t('me.learned.sayIt', 'Say it your way')} value={text} onChange={setText} multiline />
          <div className="flex gap-2">
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
        <div className="flex flex-wrap gap-2 pt-1">
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

function Digest() {
  const { t } = useTranslation()
  const { data } = useDigest()
  const { data: ai } = useAiUsage()
  if (!data) return <Skeleton className="h-40" />
  const r = data.reminders
  return (
    <Card tone="hero" className="flex flex-col gap-3">
      <SectionTitle>{t('me.learned.thisWeek', 'This week')}</SectionTitle>
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
      {ai && (
        <p className="text-sub text-ink2">
          {ai.blocked > 0 ? (
            <Trans i18nKey="me.learned.aiHeld" defaults="AI use today: <b>{{calls}}</b> of {{cap}} calls, {{n}} held back at the limit." values={{ calls: ai.calls, cap: ai.callCap, n: ai.blocked }} components={BOLD} />
          ) : (
            <Trans i18nKey="me.learned.aiUse" defaults="AI use today: <b>{{calls}}</b> of {{cap}} calls." values={{ calls: ai.calls, cap: ai.callCap }} components={BOLD} />
          )}
        </p>
      )}
      <p className="text-sub text-ink3">{t('me.learned.onlySuggests', 'It only suggests. It never changes your medicines, your numbers or its own safety rules.')}</p>
    </Card>
  )
}

function Audit() {
  const { t } = useTranslation()
  const [open, setOpen] = useState(false)
  const { data } = useAudit(open)
  const TRIGGER: Record<string, string> = {
    tick: t('me.learned.trigger.tick', 'Reminder check'),
    nightly: t('me.learned.trigger.nightly', 'Nightly review'),
    chat: t('me.learned.trigger.chat', 'A message'),
    log: t('me.learned.trigger.log', 'A log'),
    memory: t('me.learned.trigger.memory', 'Memory'),
    checkin: t('me.learned.trigger.checkin', 'Check-in'),
    scan: t('me.learned.trigger.scan', 'A scan'),
    brief: t('me.learned.trigger.brief', 'Brief'),
    onboarding: t('me.learned.trigger.onboarding', 'Onboarding'),
  }
  return (
    <section className="flex flex-col gap-2">
      <TextLink onClick={() => setOpen((o) => !o)} className="self-start">
        {open ? t('me.learned.hideDid', 'Hide what it did') : t('me.learned.seeDid', 'See what it did')}
      </TextLink>
      {open && (
        <Card tone="soft" className="flex flex-col gap-2">
          {!data && <Skeleton className="h-24" />}
          {data?.length === 0 && <p className="text-body text-ink2">{t('me.learned.nothingYet', 'Nothing yet.')}</p>}
          <ul className="divide-y divide-line">
            {data?.map((r) => (
              <li key={r.id} className="py-2 text-sub">
                <p className="font-bold">
                  {TRIGGER[r.trigger] ?? r.trigger}{' '}
                  <span className="font-normal text-ink3">{t('me.learned.auditMeta', '· {{when}} · {{status}}', { when: clock(r.at), status: r.status })}</span>
                </p>
                <p className="text-ink2">{r.steps.map((s) => s.node).join(t('me.learned.then', ' then '))}</p>
              </li>
            ))}
          </ul>
          <p className="text-micro text-ink3">{t('me.learned.recorded', 'Every run is recorded, and your own changes are logged too.')}</p>
        </Card>
      )}
    </section>
  )
}

export function Learned() {
  const { t } = useTranslation()
  const { data, isError } = useLearned()
  return (
    <Screen>
      <Header title={t('me.learned.title', 'What Smart Health has learned')} back backTo="K1" sub={t('me.learned.sub', 'Everything it noticed about you, and why. You decide what stays.')} />
      <Digest />
      {isError && <Alert tone="warn">{t('me.learned.loadError', 'We could not load this just now.')}</Alert>}
      {!data && !isError && <Skeleton className="h-40" />}
      {data && data.total === 0 && (
        <EmptyState icon={Brain}>
          {t('me.learned.empty', 'Nothing yet. As you log meals and doses, it will notice patterns and ask you to check them here.')}
        </EmptyState>
      )}
      {data?.groups.map((g) => (
        <section key={g.category} className="flex flex-col gap-3">
          <SectionTitle>{g.label}</SectionTitle>
          {g.facts.map((f) => (
            <FactCard key={f.id} f={f} />
          ))}
        </section>
      ))}
      <Alert tone="info" icon={Info}>
        {t('me.learned.notDiagnosis', 'These are patterns in your own logs, not a diagnosis. If a delete is wrong for you, nothing is lost: it just stops being used.')}
      </Alert>
      <Audit />
    </Screen>
  )
}
