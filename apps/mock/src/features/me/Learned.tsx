import { useState } from 'react'
import { useFactAction, useFacts } from '@/data/hooks'
import { useGo } from '@/app/navigation'
import { useUi } from '@/state/store'
import type { MemoryFact } from '@/data/types'
import { Header, Screen, Reveal } from '@/ui/layout'
import { Button, Card, Dots, Field, SectionTitle, Skeleton, StatusPill } from '@/ui/primitives'
import { CaretRight, Info } from '@/ui/icons'

const cat: Record<MemoryFact['category'], string> = { routine: 'Routines', preference: 'Preferences', barrier: 'What gets in the way', food_response: 'Food responses', activity: 'Activity' }
const order: MemoryFact['category'][] = ['routine', 'activity', 'food_response', 'preference', 'barrier']

export function Learned() {
  const { data } = useFacts()
  if (!data)
    return (
      <Screen>
        <Header title="What Smart Health has learned" back backTo="K1" />
        <Skeleton className="h-60" />
      </Screen>
    )
  const { facts, compare } = data
  return (
    <Screen>
      <Header title="What Smart Health has learned" back backTo="K1" sub="Everything here is yours to confirm, change or delete." />
      <Reveal id="learn-compare">
        <Card tone="hero" className="flex flex-col gap-3">
          <SectionTitle>Week 1 and week 8</SectionTitle>
          <div className="grid grid-cols-[1fr_auto_auto] items-center gap-x-4 gap-y-2.5 [[data-ts='2']_&]:grid-cols-1">
            <span className="text-sub text-ink3" />
            <span className="text-right text-sub font-bold text-ink3 [[data-ts='2']_&]:hidden">Week 1</span>
            <span className="text-right text-sub font-bold text-ink3 [[data-ts='2']_&]:hidden">Week 8</span>
            {compare.rows.map((r) => (
              <div key={r.label} className="col-span-3 grid grid-cols-subgrid items-baseline [[data-ts='2']_&]:col-span-1">
                <span className="text-body">{r.label}</span>
                <span className="num text-right text-h2 text-ink2">{r.then}</span>
                <span className="num text-right text-h2 font-medium">
                  {r.now}
                  {r.flagged && <span className="sr-only"> (flagged)</span>}
                </span>
              </div>
            ))}
          </div>
          <StatusPill tone="warn">Fasting baseline: higher than at week 1</StatusPill>
          <div>
            <p className="mb-1.5 text-sub font-bold text-ink2">Built from</p>
            <ul className="flex flex-wrap gap-1.5">
              {compare.streams.map((s) => (
                <li key={s} className="rounded-chip bg-brand-soft px-3 py-1 text-sub text-brand">
                  {s}
                </li>
              ))}
            </ul>
          </div>
          <p className="text-sub text-ink2">{compare.stillLearning}</p>
        </Card>
      </Reveal>

      {order.map((c) => {
        const list = facts.filter((f) => f.category === c)
        if (!list.length) return null
        return (
          <section key={c} className="flex flex-col gap-3">
            <SectionTitle>{cat[c]}</SectionTitle>
            {list.map((f) => (
              <FactRow key={f.id} f={f} />
            ))}
          </section>
        )
      })}
      <p className="flex gap-2 text-sub text-ink3">
        <Info size={18} className="mt-0.5 flex-none" aria-hidden />
        Nothing here has been checked by a clinician. These are patterns in your own data.
      </p>
    </Screen>
  )
}

function FactRow({ f }: { f: MemoryFact }) {
  const act = useFactAction()
  const go = useGo()
  const toast = useUi((s) => s.showToast)
  const [editing, setEditing] = useState(false)
  const [text, setText] = useState(f.statement)
  return (
    <Card className="flex flex-col gap-3">
      {editing ? (
        <Field label="Change this" value={text} onChange={setText} multiline />
      ) : (
        <p className="text-body font-bold leading-snug">{f.statement}</p>
      )}
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
        <span className="flex items-center gap-2 text-sub text-ink2">
          <Dots n={f.confidence} /> {f.confidence === 3 ? 'Confident' : f.confidence === 2 ? 'Fairly sure' : 'Early guess'}
        </span>
        {f.status === 'proposed' ? <StatusPill tone="brass" bare>Waiting for you</StatusPill> : f.evidenceStatus === 'observed' ? <StatusPill tone="ok" bare>You confirmed this</StatusPill> : <StatusPill tone="neutral" bare>Calculated from your data</StatusPill>}
      </div>
      <button type="button" onClick={() => go(f.evidenceTo)} className="press flex items-center justify-between gap-2 rounded-field bg-well px-3 py-2.5 text-left text-sub">
        <span>
          <span className="text-ink3">Why I think this: </span>
          <span className="font-bold">{f.evidence}</span>
        </span>
        <CaretRight size={18} className="flex-none text-ink3" aria-hidden />
      </button>
      <div className="flex flex-wrap gap-2">
        {editing ? (
          <>
            <Button size="md" className="!w-auto flex-1" onClick={() => act.mutate({ id: f.id, action: 'edit', text }, { onSuccess: () => { setEditing(false); toast('Saved. Your version replaces the old one.') } })}>
              Save
            </Button>
            <Button size="md" className="!w-auto flex-1" variant="secondary" onClick={() => setEditing(false)}>
              Cancel
            </Button>
          </>
        ) : (
          <>
            <Button size="md" className="!w-auto flex-1" variant={f.status === 'proposed' ? 'primary' : 'secondary'} onClick={() => act.mutate({ id: f.id, action: 'confirm' }, { onSuccess: () => toast('Confirmed') })}>
              {f.status === 'proposed' ? 'Yes, that is right' : 'Confirm'}
            </Button>
            <Button size="md" className="!w-auto flex-1" variant="secondary" onClick={() => setEditing(true)}>
              Edit
            </Button>
            <Button size="md" className="!w-auto flex-1" variant="ghost" onClick={() => act.mutate({ id: f.id, action: 'delete' }, { onSuccess: () => toast('Deleted. We will not suggest it again.') })}>
              Delete
            </Button>
          </>
        )}
      </div>
    </Card>
  )
}
