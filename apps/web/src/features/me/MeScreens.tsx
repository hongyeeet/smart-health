import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { appConfig } from '@/config/app'
import { useAddQuestion, useCarePlan, usePlanAppointment, useRemoveQuestion, useSources, useSync } from '@/data/hooks'
import type { Locale, PreventiveItem } from '@/data/types'
import { useGo } from '@/app/navigation'
import { href } from '@/app/routeIds'
import { useUi } from '@/state/store'
import { Header, Footer, Screen } from '@/ui/layout'
import { Segmented } from '@/ui/controls'
import { Alert, Button, Card, Chip, Field, SectionTitle, Skeleton, StatusPill, TextLink, Toggle, type Tone } from '@/ui/primitives'
import { Camera, CalendarBlank, Drop, Download, Trash, Watch, X, Eye, Footprints, Syringe, Heartbeat, type IconType } from '@/ui/icons'

/* ------------------------------------ K3 care plan ------------------------------------ */
const prevTone: Record<PreventiveItem['status'], { tone: Tone; label: string }> = {
  overdue: { tone: 'danger', label: 'Overdue' },
  due_soon: { tone: 'warn', label: 'Due soon' },
  ok: { tone: 'ok', label: 'Up to date' },
  unknown: { tone: 'neutral', label: 'Not recorded' },
}
const prevIcon: Record<string, IconType> = { eye: Eye, foot: Footprints, hba1c: Drop, flu: Syringe }

export function CarePlan() {
  const { data } = useCarePlan()
  const go = useGo()
  const add = useAddQuestion()
  const remove = useRemoveQuestion()
  const [q, setQ] = useState('')
  if (!data)
    return (
      <Screen>
        <Header title="Care plan" back backTo="K1" />
        <Skeleton className="h-60" />
      </Screen>
    )
  return (
    <Screen>
      <Header title="Care plan" back backTo="K1" />
      <Card tone="hero" className="flex flex-col gap-3">
        <div className="flex items-center gap-2 text-sub font-bold text-ink2">
          <CalendarBlank size={20} className="text-brand" aria-hidden /> Next appointment
        </div>
        <div>
          <p className="text-h2 font-bold">{data.appointment.label}</p>
          <p className="text-body text-ink2">{data.appointment.when}</p>
          <p className="text-sub text-ink3">In {data.appointment.inDays} days. {data.appointment.place}</p>
        </div>
        <Button variant="secondary" onClick={() => go('K7')}>
          Plan an appointment
        </Button>
      </Card>

      <section className="flex flex-col gap-1">
        <SectionTitle>Check-ups</SectionTitle>
        <ul className="divide-y divide-line">
          {data.preventive.map((p) => {
            const Icon = prevIcon[p.id] ?? Heartbeat
            const s = prevTone[p.status]
            return (
              <li key={p.id} className="flex items-center gap-3 py-3">
                <span className="flex h-11 w-11 flex-none items-center justify-center rounded-full bg-brand-soft text-brand">
                  <Icon size={22} aria-hidden />
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block text-body font-bold">{p.label}</span>
                  <span className="block text-sub text-ink2">{p.detail}</span>
                </span>
                <StatusPill tone={s.tone}>{s.label}</StatusPill>
              </li>
            )
          })}
        </ul>
        <p className="text-sub text-ink3">Intervals are placeholders until your doctor confirms them.</p>
      </section>

      <section className="flex flex-col gap-3">
        <SectionTitle>My questions for the doctor</SectionTitle>
        <ul className="flex flex-col gap-2">
          {data.questions.map((qq) => (
            <li key={qq.id} className="flex items-start gap-2 rounded-card border border-line bg-card p-3.5">
              <span className="flex-1 text-body">{qq.text}</span>
              <button type="button" aria-label="Remove question" onClick={() => remove.mutate(qq.id)} className="press flex h-10 w-10 flex-none items-center justify-center rounded-full text-ink3 hover:bg-well">
                <X size={20} aria-hidden />
              </button>
            </li>
          ))}
        </ul>
        <Field label="Add your own question" value={q} onChange={setQ} placeholder="Type or say it in your own words" />
        <Button variant="secondary" disabled={!q.trim()} onClick={() => add.mutate({ text: q.trim(), origin: 'user' }, { onSuccess: () => setQ('') })}>
          Add question
        </Button>
      </section>

      <Footer>
        <Button onClick={() => go('L1')}>Generate my doctor brief</Button>
      </Footer>
    </Screen>
  )
}

/* -------------------------------------- K4 sources -------------------------------------- */
export function Sources() {
  const { data } = useSources()
  const sync = useSync()
  const toast = useUi((s) => s.showToast)
  const go = useGo()
  return (
    <Screen>
      <Header title="Connected sources" back backTo="K1" sub="These only send data to Smart Health." />
      {!data ? (
        <Skeleton className="h-48" />
      ) : (
        <ul className="flex flex-col gap-3">
          {data.map((s) => {
            const Icon = s.id === 'watch' ? Watch : s.id === 'sensor' ? Drop : Camera
            return (
              <li key={s.id}>
                <Card className="flex items-center gap-3">
                  <span className="flex h-12 w-12 flex-none items-center justify-center rounded-full bg-brand-soft text-brand">
                    <Icon size={24} aria-hidden />
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block text-body font-bold">{s.label}</span>
                    <span className="block text-sub text-ink2">{s.detail}</span>
                    <span className="block text-sub text-ink3">Last synced {s.synced}</span>
                  </span>
                  <StatusPill tone="ok">{s.status === 'connected' ? 'Connected' : 'Allowed'}</StatusPill>
                </Card>
              </li>
            )
          })}
        </ul>
      )}
      <Button variant="secondary" disabled={sync.isPending} onClick={() => sync.mutate(undefined, { onSuccess: () => toast('Synced just now') })}>
        {sync.isPending ? 'Syncing...' : 'Sync now (prototype)'}
      </Button>
      <TextLink onClick={() => go('C8')} className="self-start">
        Glucose sensor sprint details
      </TextLink>
      <p className="text-sub text-ink3">You can import a file from a watch instead. Your data stays yours: you can disconnect any source at any time.</p>
    </Screen>
  )
}

/* ------------------------------------ K5 language ------------------------------------ */
export function LanguageDisplay() {
  const { locale, setLocale, theme, setTheme, textScale, setTextScale } = useUi()
  return (
    <Screen>
      <Header title="Language and display" back backTo="K1" />
      <section className="flex flex-col gap-3">
        <SectionTitle>Language</SectionTitle>
        <div className="flex flex-wrap gap-2" role="radiogroup" aria-label="Language">
          {appConfig.locales.map((l) => (
            <Chip key={l.code} on={locale === l.code} onClick={() => setLocale(l.code as Locale)}>
              {l.native}
            </Chip>
          ))}
        </div>
        <p className="text-sub text-ink3">Medicine explanations are translated by machine and not yet reviewed. Chinese is available first.</p>
      </section>
      <section className="flex flex-col gap-3">
        <SectionTitle>Colour</SectionTitle>
        <Segmented label="Colour theme" value={theme} onChange={setTheme} options={[{ value: 'light', label: 'Light' }, { value: 'dark', label: 'Dark' }]} />
      </section>
      <section className="flex flex-col gap-3">
        <SectionTitle>Text size</SectionTitle>
        <Segmented label="Text size" value={textScale} onChange={setTextScale} options={[{ value: 1, label: 'Standard' }, { value: 2, label: 'Extra large' }]} />
        <Card tone="soft">
          <p className="text-body">This is how your text will look. Readings use larger numbers: <span className="num text-h2">7.8</span> mmol/L.</p>
        </Card>
      </section>
    </Screen>
  )
}

/* ------------------------------------- K6 privacy ------------------------------------- */
export function Privacy() {
  const { consentData, consentShare, setConsent } = useUi()
  const toast = useUi((s) => s.showToast)
  const [research, setResearch] = useState(false)
  const Row = ({ title, sub, on, onChange, locked }: { title: string; sub: string; on: boolean; onChange?: (v: boolean) => void; locked?: boolean }) => (
    <div className="flex items-start justify-between gap-4 py-3.5">
      <div>
        <p className="text-body font-bold">{title}</p>
        <p className="text-sub text-ink2">{sub}</p>
        {locked && <p className="text-sub text-ink3">Required to use the app.</p>}
      </div>
      <Toggle on={on} onChange={(v) => !locked && onChange?.(v)} label={title} />
    </div>
  )
  return (
    <Screen>
      <Header title="Privacy and consent" back backTo="K1" />
      <Card className="divide-y divide-line !py-1">
        <Row title="Use my health data" sub="Lets Smart Health read what you log and what your devices send." on={consentData || true} locked />
        <Row title="Share my doctor brief" sub="Optional. You choose each time you create a link." on={consentShare} onChange={(v) => setConsent('consentShare', v)} />
        <Row title="Use my data for research" sub="Optional. Never includes your name." on={research} onChange={setResearch} />
      </Card>
      <Button variant="secondary" onClick={() => toast('All share links revoked')}>
        Revoke access to my doctor brief
      </Button>
      <Alert tone="info">Names and identity numbers are never sent to the AI. Every time your doctor opens a link is logged.</Alert>
    </Screen>
  )
}

/* ---------------------------------- K7 plan appointment ---------------------------------- */
const kinds = ['Diabetes review', 'Eye screening', 'Foot check', 'Blood test', 'Flu vaccination']
const dates = ['Sun 11 Oct, 10:30 am', 'Tue 13 Oct, 9:00 am', 'Mon 19 Oct, 2:00 pm']
export function PlanAppointment() {
  const [kind, setKind] = useState('Diabetes review')
  const [when, setWhen] = useState(dates[0]!)
  const [ok, setOk] = useState(false)
  const plan = usePlanAppointment()
  const navigate = useNavigate()
  const toast = useUi((s) => s.showToast)
  return (
    <Screen>
      <Header title="Plan an appointment" back backTo="K3" />
      <section className="flex flex-col gap-2">
        <p className="text-sub font-bold">What for?</p>
        <div className="flex flex-wrap gap-2">
          {kinds.map((k) => (
            <Chip key={k} on={kind === k} onClick={() => setKind(k)}>
              {k}
            </Chip>
          ))}
        </div>
      </section>
      <section className="flex flex-col gap-2">
        <p className="text-sub font-bold">When?</p>
        <div className="flex flex-col gap-2">
          {dates.map((d) => (
            <Chip key={d} on={when === d} onClick={() => setWhen(d)}>
              {d}
            </Chip>
          ))}
        </div>
      </section>
      <p className="text-sub text-ink2">A doctor brief is prepared 48 hours before.</p>
      <div className="flex items-center justify-between gap-4 rounded-card border border-line bg-card p-3.5">
        <span className="text-body">I confirm adding this to my calendar.</span>
        <Toggle on={ok} onChange={setOk} label="Confirm adding to my calendar" />
      </div>
      <Footer>
        <Button disabled={!ok} icon={CalendarBlank} onClick={() => plan.mutate({ label: kind, when }, { onSuccess: () => { toast('Added to your calendar'); navigate(href('K3'), { replace: true }) } })}>
          Add to calendar
        </Button>
        <Button variant="secondary" icon={Download} onClick={() => toast('A calendar file (.ics) was saved')}>
          Download calendar file
        </Button>
      </Footer>
    </Screen>
  )
}

/* ------------------------------------ K8 data and account ------------------------------------ */
export function DataAccount() {
  const toast = useUi((s) => s.showToast)
  const [sure, setSure] = useState(false)
  return (
    <Screen>
      <Header title="Data and account" back backTo="K1" />
      <Card className="flex flex-col gap-3">
        <SectionTitle>Export my data</SectionTitle>
        <p className="text-body text-ink2">Get everything you have logged as a file you can keep or give to someone.</p>
        <Button variant="secondary" icon={Download} onClick={() => toast('Your export will be ready shortly')}>
          Export my data
        </Button>
      </Card>
      <Card className="flex flex-col gap-3 border-danger/40">
        <SectionTitle>Delete my account</SectionTitle>
        <p className="text-body text-ink2">This removes your logs and what Smart Health has learned. It cannot be undone.</p>
        {!sure ? (
          <Button variant="secondary" icon={Trash} onClick={() => setSure(true)}>
            Delete my account
          </Button>
        ) : (
          <div className="flex flex-col gap-2">
            <Alert tone="danger">Are you sure? Tap again to confirm.</Alert>
            <Button variant="danger" onClick={() => toast('Account deletion requested (prototype)')}>
              Yes, delete everything
            </Button>
            <Button variant="ghost" onClick={() => setSure(false)}>
              Keep my account
            </Button>
          </div>
        )}
      </Card>
      <p className="text-sub text-ink3">Edits and deletions are written to an activity log that cannot be changed.</p>
    </Screen>
  )
}
