/**
 * K2 — What Smart Health has learned (PRD F16).
 *
 * The agent only proposes. Here the person sees each thing it noticed, why it thinks so, and decides: confirm it, say it in their own
 * words, or delete it (a deleted idea is never proposed again). The week's digest shows everything it did, and the audit list shows
 * the runs behind it. Nothing here gives advice.
 */
import { useState } from 'react'
import { useAiUsage, useAudit, useDigest, useLearned, useLearnedAction } from '@/data/hooks'
import type { LearnedFact } from '@/data/types'
import { cn } from '@/lib/cn'
import { Header, Screen } from '@/ui/layout'
import { Alert, Button, Card, EmptyState, Field, SectionTitle, Skeleton, TextLink } from '@/ui/primitives'
import { Brain, CheckCircle, Info } from '@/ui/icons'

const TRIGGER_LABEL: Record<string, string> = { tick: 'Reminder check', nightly: 'Nightly review', chat: 'A message', log: 'A log', memory: 'Memory', checkin: 'Check-in', scan: 'A scan', brief: 'Brief', onboarding: 'Onboarding' }
const clock = (iso: string) => new Date(iso).toLocaleString('en-US', { day: 'numeric', month: 'short', hour: 'numeric', minute: '2-digit' })

function FactCard({ f }: { f: LearnedFact }) {
  const act = useLearnedAction()
  const [editing, setEditing] = useState(false)
  const [text, setText] = useState(f.statement)
  const busy = act.isPending
  return (
    <Card className="flex flex-col gap-2">
      <div className="flex items-start justify-between gap-3">
        <p className="min-w-0 text-body font-bold leading-snug">{f.statement}</p>
        <span className={cn('flex-none rounded-chip px-2 py-0.5 text-micro font-bold', f.status === 'active' ? 'bg-ok-soft text-ok' : 'bg-brass-soft text-brass')}>{f.status === 'active' ? 'Confirmed' : 'Waiting for you'}</span>
      </div>
      <p className="text-sub text-ink2">{f.why}</p>
      <p className="text-micro text-ink3">
        {f.source === 'user' ? 'In your own words' : `Noticed by Smart Health, ${Math.round(f.confidence * 100)}% sure`} · version {f.version}
      </p>
      {editing && (
        <div className="flex flex-col gap-2">
          <Field label="Say it your way" value={text} onChange={setText} multiline />
          <div className="flex gap-2">
            <Button size="md" className="!w-auto" disabled={busy || text.trim().length < 3} onClick={() => act.mutate({ id: f.id, action: 'edit', text }, { onSuccess: () => setEditing(false) })}>
              Save my wording
            </Button>
            <Button size="md" variant="secondary" className="!w-auto" onClick={() => { setEditing(false); setText(f.statement) }}>
              Cancel
            </Button>
          </div>
        </div>
      )}
      {!editing && (
        <div className="flex flex-wrap gap-2 pt-1">
          {f.status === 'proposed' && (
            <Button size="md" className="!w-auto" icon={CheckCircle} disabled={busy} onClick={() => act.mutate({ id: f.id, action: 'confirm' })}>
              That is right
            </Button>
          )}
          <Button size="md" variant="secondary" className="!w-auto" disabled={busy} onClick={() => setEditing(true)}>
            Change it
          </Button>
          <Button size="md" variant="ghost" className="!w-auto" disabled={busy} onClick={() => act.mutate({ id: f.id, action: 'delete' })}>
            Delete
          </Button>
        </div>
      )}
      {act.isError && <Alert tone="danger">That did not save. Please try again.</Alert>}
    </Card>
  )
}

function Digest() {
  const { data } = useDigest()
  const { data: ai } = useAiUsage()
  if (!data) return <Skeleton className="h-40" />
  const r = data.reminders
  return (
    <Card tone="hero" className="flex flex-col gap-3">
      <SectionTitle>This week</SectionTitle>
      <ul className="flex flex-col gap-1.5 text-body">
        <li>
          <b className="num">{data.newFacts}</b> {data.newFacts === 1 ? 'thing' : 'things'} noticed or changed
        </li>
        <li>
          <b className="num">{r.sent}</b> reminders sent, <b className="num">{r.opened}</b> opened, <b className="num">{r.acted}</b> acted on
        </li>
        <li>
          <b className="num">{data.suggestions.chosen}</b> of <b className="num">{data.suggestions.shown}</b> suggestions chosen by you
        </li>
        <li>
          Safety checks on its own wording: <b className="num">{data.guard.passed}</b> passed, <b className="num">{data.guard.blocked}</b> blocked
        </li>
      </ul>
      {data.topSuggestions.length > 0 && (
        <div>
          <p className="text-sub font-bold text-ink2">Suggestions it is learning from</p>
          <ul className="text-sub text-ink2">
            {data.topSuggestions.map((s, i) => (
              <li key={i}>
                {s.name}: shown {s.shown}, chosen {s.chosen}
              </li>
            ))}
          </ul>
        </div>
      )}
      {ai && (
        <p className="text-sub text-ink2">
          AI use today: <b className="num">{ai.calls}</b> of {ai.callCap} calls{ai.blocked > 0 ? `, ${ai.blocked} held back at the limit` : ''}.
        </p>
      )}
      <p className="text-sub text-ink3">It only suggests. It never changes your medicines, your numbers or its own safety rules.</p>
    </Card>
  )
}

function Audit() {
  const [open, setOpen] = useState(false)
  const { data } = useAudit(open)
  return (
    <section className="flex flex-col gap-2">
      <TextLink onClick={() => setOpen((o) => !o)} className="self-start">
        {open ? 'Hide what it did' : 'See what it did'}
      </TextLink>
      {open && (
        <Card tone="soft" className="flex flex-col gap-2">
          {!data && <Skeleton className="h-24" />}
          {data?.length === 0 && <p className="text-body text-ink2">Nothing yet.</p>}
          <ul className="divide-y divide-line">
            {data?.map((r) => (
              <li key={r.id} className="py-2 text-sub">
                <p className="font-bold">
                  {TRIGGER_LABEL[r.trigger] ?? r.trigger} <span className="font-normal text-ink3">· {clock(r.at)} · {r.status}</span>
                </p>
                <p className="text-ink2">{r.steps.map((s) => s.node).join(' then ')}</p>
              </li>
            ))}
          </ul>
          <p className="text-micro text-ink3">Every run is recorded, and your own changes are logged too.</p>
        </Card>
      )}
    </section>
  )
}

export function Learned() {
  const { data, isError } = useLearned()
  return (
    <Screen>
      <Header title="What Smart Health has learned" back backTo="K1" sub="Everything it noticed about you, and why. You decide what stays." />
      <Digest />
      {isError && <Alert tone="warn">We could not load this just now.</Alert>}
      {!data && !isError && <Skeleton className="h-40" />}
      {data && data.total === 0 && (
        <EmptyState icon={Brain}>
          Nothing yet. As you log meals and doses, it will notice patterns and ask you to check them here.
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
        These are patterns in your own logs, not a diagnosis. If a delete is wrong for you, nothing is lost: it just stops being used.
      </Alert>
      <Audit />
    </Screen>
  )
}
