import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAddMed, useConfirmScan, useMeds, useScan } from '@/data/hooks'
import { useGo } from '@/app/navigation'
import { href } from '@/app/routeIds'
import { useUi } from '@/state/store'
import type { Medication } from '@/data/types'
import { Header, Footer, Screen, Reveal } from '@/ui/layout'
import { Alert, Button, Card, Chip, ConfidenceChip, Field, SectionTitle, Skeleton, StatusPill, TextLink, Toggle } from '@/ui/primitives'
import { Camera, CheckCircle, Clock, Info, Pill, WarningCircle } from '@/ui/icons'
import { useDoseState } from './useDoseState'

/* ------------------------------------ H1 list ------------------------------------ */
export function MedList() {
  const { data } = useMeds()
  const go = useGo()
  const doseState = useDoseState()
  if (!data)
    return (
      <Screen tabs>
        <Header title="Medications" />
        <Skeleton className="h-56" />
      </Screen>
    )
  const refill = data.find((m) => m.refill && m.refill.daysLeft <= 7)
  return (
    <Screen tabs>
      <Header title="Medications" sub="Dose times come from your own labels." />
      <Button icon={Camera} onClick={() => go('H2')}>
        Scan a label
      </Button>
      <Button variant="secondary" onClick={() => go('H8')}>
        Add by hand
      </Button>
      {refill && (
        <Alert tone="info" icon={Clock} onClick={() => go('H6', { params: { id: refill.id } })}>
          {refill.name} runs out in about {refill.refill!.daysLeft} days. You may want to arrange a refill.
        </Alert>
      )}
      <ul className="flex flex-col gap-3">
        {data.map((m, i) => (
          <li key={m.id}>
            <Reveal id={`med-${m.id}`} i={i}>
              <MedCard m={m} state={doseState(m)} />
            </Reveal>
          </li>
        ))}
      </ul>
    </Screen>
  )
}

function MedCard({ m, state }: { m: Medication; state: { tone: 'ok' | 'info' | 'neutral' | 'warn'; label: string } | null }) {
  const go = useGo()
  return (
    <Card className="flex flex-col gap-3" onClick={() => go('H6', { params: { id: m.id } })}>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-h2 font-bold leading-tight">
            {m.name} <span className="font-normal text-ink2">{m.strength}</span>
          </p>
          <p className="text-sub text-ink2">
            {m.times.length ? m.times.join(', ') : 'No dose times'}
            {m.withFood && ', with food'}
          </p>
        </div>
        {state && <StatusPill tone={state.tone}>{state.label}</StatusPill>}
      </div>
      <div className="flex flex-wrap gap-2">
        {m.kind !== 'prescription' && <StatusPill tone="neutral" icon={Pill} bare>{m.kind === 'tcm' ? 'Herbal' : 'Supplement'}</StatusPill>}
        {m.badge === 'interaction' && (
          <span
            role="button"
            tabIndex={0}
            onClick={(e) => {
              e.stopPropagation()
              go('H5')
            }}
            onKeyDown={(e) => e.key === 'Enter' && go('H5')}
          >
            <StatusPill tone="warn" icon={WarningCircle}>
              Possible interaction
            </StatusPill>
          </span>
        )}
        {m.badge === 'not_checked' && (
          <StatusPill tone="neutral" icon={Info}>
            Not checked
          </StatusPill>
        )}
      </div>
    </Card>
  )
}

/* ---------------------------------- H2 scan: frame ---------------------------------- */
export function ScanFrame() {
  const navigate = useNavigate()
  return (
    <Screen>
      <Header title="Scan a label" back backTo="H1" sub="Step 1 of 3" />
      <div className="relative flex h-72 items-center justify-center overflow-hidden rounded-card bg-[#101815]" role="img" aria-label="Camera view with a frame to line the label up in">
        {['left-4 top-4 border-l-4 border-t-4', 'right-4 top-4 border-r-4 border-t-4', 'bottom-4 left-4 border-b-4 border-l-4', 'bottom-4 right-4 border-b-4 border-r-4'].map((c) => (
          <span key={c} className={`absolute h-10 w-10 rounded-sm border-[#E9EFEA] ${c}`} />
        ))}
        <p className="px-10 text-center text-body text-[#C9D3CD]">Line up the label inside the corners</p>
      </div>
      <Card tone="soft" className="flex flex-col gap-2">
        <SectionTitle>Tips</SectionTitle>
        <ul className="flex flex-col gap-1.5 text-body">
          <li>Use good light and keep the label flat.</li>
          <li>Hold still until the text looks sharp.</li>
          <li>Medicines, supplements and herbal products all work.</li>
        </ul>
      </Card>
      <Button icon={Camera} onClick={() => navigate(href('H3'))}>
        Take photo
      </Button>
      <p className="text-center text-sub text-ink3">Prototype: this uses a sample label.</p>
    </Screen>
  )
}

/* ---------------------------------- H3 scan: review ---------------------------------- */
export function ScanReview() {
  const { data } = useScan()
  const navigate = useNavigate()
  const [ok, setOk] = useState<Record<string, boolean>>({})
  const [typed, setTyped] = useState<Record<string, string>>({})
  if (!data)
    return (
      <Screen>
        <Header title="Check what we read" back backTo="H2" />
        <Skeleton className="h-64" />
      </Screen>
    )
  const needs = data.fields.filter((f) => f.confidence === 'check').every((f) => ok[f.key])
  return (
    <Screen>
      <Header title="Check what we read" back backTo="H2" sub="Step 2 of 3. Nothing is saved until you confirm." />
      <ul className="flex flex-col gap-3">
        {data.fields.map((f) => (
          <li key={f.key}>
            <Card className="flex flex-col gap-2">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="text-sub font-bold text-ink2">{f.label}</span>
                <ConfidenceChip level={f.confidence} />
              </div>
              {f.confidence === 'unreadable' ? (
                <Field label="I can't read this, please type it" value={typed[f.key] ?? ''} onChange={(v) => setTyped({ ...typed, [f.key]: v })} hint="You can leave this empty." />
              ) : (
                <p className="text-h2 font-bold">{f.value}</p>
              )}
              {f.confidence === 'check' && (
                <Chip on={!!ok[f.key]} onClick={() => setOk({ ...ok, [f.key]: !ok[f.key] })} className="self-start">
                  {ok[f.key] ? 'Confirmed' : 'Tap to confirm'}
                </Chip>
              )}
            </Card>
          </li>
        ))}
      </ul>
      <Footer>
        <Button disabled={!needs} onClick={() => navigate(href('H4'))}>
          Confirm
        </Button>
        <Button variant="secondary" onClick={() => navigate(href('H2'))}>
          Retake photo
        </Button>
      </Footer>
    </Screen>
  )
}

/* ---------------------------------- H4 scan: plan ---------------------------------- */
export function ScanPlan() {
  const { data } = useScan()
  const confirm = useConfirmScan()
  const navigate = useNavigate()
  const go = useGo()
  const toast = useUi((s) => s.showToast)
  if (!data)
    return (
      <Screen>
        <Header title="Your dose plan" back backTo="H3" />
        <Skeleton className="h-48" />
      </Screen>
    )
  return (
    <Screen>
      <Header title="Your dose plan" back backTo="H3" sub="Step 3 of 3" />
      <Card className="flex flex-col gap-3">
        <p className="text-h2 font-bold">Clarithromycin 500 mg</p>
        <p className="text-body text-ink2">1 tablet, twice daily after meals, for 7 days. Times come from your label.</p>
        <ul className="divide-y divide-line">
          {data.schedule.map((s) => (
            <li key={s.time} className="flex items-center justify-between py-3 text-body">
              <span className="font-bold">{s.time}</span>
              <span className="text-ink2">{s.label}</span>
            </li>
          ))}
        </ul>
      </Card>
      <p className="text-sub text-ink2">When you add it, we check it against your other medicines and tell you if there is something to ask about.</p>
      <Footer>
        <Button
          icon={CheckCircle}
          disabled={confirm.isPending}
          onClick={() =>
            confirm.mutate(undefined, {
              onSuccess: () => {
                navigate(href('H1'), { replace: true })
                toast('Added to your medicines')
                setTimeout(() => go('H5'), 350)
              },
            })
          }
        >
          Add to my medicines
        </Button>
      </Footer>
    </Screen>
  )
}

/* ---------------------------------- H8 add by hand ---------------------------------- */
const timeOptions = ['8:00 am', '12:00 pm', '6:00 pm', '8:00 pm', '10:00 pm']
export function AddByHand() {
  const [name, setName] = useState('')
  const [strength, setStrength] = useState('')
  const [times, setTimes] = useState<string[]>(['8:00 am'])
  const [food, setFood] = useState(false)
  const add = useAddMed()
  const navigate = useNavigate()
  const toast = useUi((s) => s.showToast)
  return (
    <Screen>
      <Header title="Add a medicine" back backTo="H1" />
      <Field label="Name" value={name} onChange={setName} placeholder="As written on the label" />
      <Field label="Strength" value={strength} onChange={setStrength} placeholder="For example, 500 mg" />
      <div className="flex flex-col gap-2">
        <p className="text-sub font-bold">Times each day</p>
        <div className="flex flex-wrap gap-2">
          {timeOptions.map((t) => (
            <Chip key={t} on={times.includes(t)} onClick={() => setTimes(times.includes(t) ? times.filter((x) => x !== t) : [...times, t])}>
              {t}
            </Chip>
          ))}
        </div>
      </div>
      <div className="flex items-center justify-between gap-4 rounded-card border border-line bg-card p-3.5">
        <span className="text-body font-bold">Take with food</span>
        <Toggle on={food} onChange={setFood} label="Take with food" />
      </div>
      <Alert tone="info">We check it against our reference data. If we can't find it, it shows as Not checked. We never guess.</Alert>
      <Footer>
        <Button
          disabled={!name.trim() || times.length === 0 || add.isPending}
          onClick={() =>
            add.mutate({ name: name.trim(), strength: strength.trim() || 'Strength not entered', times, withFood: food }, { onSuccess: () => { toast('Added to your medicines'); navigate(href('H1'), { replace: true }) } })
          }
        >
          Save medicine
        </Button>
      </Footer>
      <TextLink onClick={() => navigate(href('H2'))} className="self-center">
        Scan a label instead
      </TextLink>
    </Screen>
  )
}
