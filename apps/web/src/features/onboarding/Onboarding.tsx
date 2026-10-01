import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { appConfig } from '@/config/app'
import { href } from '@/app/routeIds'
import { useGo } from '@/app/navigation'
import { useUi } from '@/state/store'
import type { Locale } from '@/data/types'
import { Header, Footer, Screen } from '@/ui/layout'
import { Segmented } from '@/ui/controls'
import { Alert, Button, Card, Chip, Field, StatusPill, TextLink, Toggle } from '@/ui/primitives'
import { Camera, CheckCircle, Drop, ShieldCheck, Watch, Prohibit, Leaf } from '@/ui/icons'

function Progress({ step }: { step: number }) {
  return (
    <div className="flex gap-1.5" role="img" aria-label={`Step ${step} of 5`}>
      {[1, 2, 3, 4, 5].map((i) => (
        <span key={i} className={`h-1.5 flex-1 rounded-full ${i <= step ? 'bg-brand' : 'bg-line'}`} />
      ))}
    </div>
  )
}

/* ------------------------------------- A1 welcome ------------------------------------- */
export function Welcome() {
  const navigate = useNavigate()
  const { locale, setLocale, consentData, consentShare, setConsent } = useUi()
  return (
    <Screen>
      <div className="flex items-center gap-2.5 pt-2">
        <span className="flex h-10 w-10 items-center justify-center rounded-full bg-brand text-on-brand">
          <Leaf size={22} aria-hidden />
        </span>
        <span className="font-serif text-h2 font-medium tracking-tight">Smart Health</span>
      </div>
      <Progress step={1} />
      <h1 className="font-serif text-xl font-medium leading-tight tracking-tight">The everyday companion for your health, and the notes your doctor always wished they had.</h1>
      <Card className="flex flex-col gap-3">
        <p className="flex gap-3 text-body"><CheckCircle size={24} className="mt-0.5 flex-none text-ok" aria-hidden />It explains your medicines, tracks your days and prepares a clear summary for your doctor.</p>
        <p className="flex gap-3 text-body"><Prohibit size={24} className="mt-0.5 flex-none text-danger" aria-hidden />It never gives medical advice, never changes your medicines and never diagnoses.</p>
      </Card>
      <section className="flex flex-col gap-2">
        <p className="text-sub font-bold">Language</p>
        <div className="flex flex-wrap gap-2" role="radiogroup" aria-label="Language">
          {appConfig.locales.map((l) => (
            <Chip key={l.code} on={locale === l.code} onClick={() => setLocale(l.code as Locale)}>
              {l.native}
            </Chip>
          ))}
        </div>
      </section>
      <Card className="flex flex-col divide-y divide-line !py-1">
        <div className="flex items-start justify-between gap-4 py-3">
          <div>
            <p className="text-body font-bold">Use my health data</p>
            <p className="text-sub text-ink2">Required, so Smart Health can read what you log.</p>
          </div>
          <Toggle on={consentData} onChange={(v) => setConsent('consentData', v)} label="Use my health data" />
        </div>
        <div className="flex items-start justify-between gap-4 py-3">
          <div>
            <p className="text-body font-bold">Share a doctor brief</p>
            <p className="text-sub text-ink2">Optional. You decide each time.</p>
          </div>
          <Toggle on={consentShare} onChange={(v) => setConsent('consentShare', v)} label="Share a doctor brief" />
        </div>
      </Card>
      <Footer>
        <Button disabled={!consentData} onClick={() => navigate(href('A2'))}>
          Next
        </Button>
        <TextLink onClick={() => navigate(href('B1'))} className="self-center">
          Skip to Home
        </TextLink>
      </Footer>
    </Screen>
  )
}

/* ----------------------------------- A2 eligibility ----------------------------------- */
type YN = 'yes' | 'no'
export function Eligibility() {
  const navigate = useNavigate()
  const [t2, setT2] = useState<'yes' | 'no' | 'unsure'>('yes')
  const [adult, setAdult] = useState<YN>('yes')
  const [pregnant, setPregnant] = useState<YN>('no')
  const out = t2 === 'no' || adult === 'no' || pregnant === 'yes'
  return (
    <Screen>
      <Header title="Is this app right for you?" back backTo="A1" />
      <Progress step={2} />
      <div className="flex flex-col gap-2">
        <p className="text-body font-bold">Do you have type 2 diabetes?</p>
        <Segmented label="Type 2 diabetes" value={t2} onChange={setT2} options={[{ value: 'yes', label: 'Yes' }, { value: 'no', label: 'No' }, { value: 'unsure', label: 'Not sure' }]} />
      </div>
      <div className="flex flex-col gap-2">
        <p className="text-body font-bold">Are you 18 or older?</p>
        <Segmented label="Age 18 or older" value={adult} onChange={setAdult} options={[{ value: 'yes', label: 'Yes' }, { value: 'no', label: 'No' }]} />
      </div>
      <div className="flex flex-col gap-2">
        <p className="text-body font-bold">Are you pregnant?</p>
        <Segmented label="Pregnant" value={pregnant} onChange={setPregnant} options={[{ value: 'no', label: 'No' }, { value: 'yes', label: 'Yes' }]} />
      </div>
      {out ? (
        <Alert tone="info" icon={ShieldCheck} title="Smart Health is not built for this yet">
          It is made for adults living with type 2 diabetes. Please talk to your care team, who can support you better. You have not been enrolled and nothing was saved.
        </Alert>
      ) : t2 === 'unsure' ? (
        <Alert tone="info">If you are not sure, ask your doctor first. You can still carry on and look around.</Alert>
      ) : null}
      <Footer>
        <Button disabled={out} onClick={() => navigate(href('A3'))}>
          Continue
        </Button>
      </Footer>
    </Screen>
  )
}

/* ------------------------------------- A3 about you ------------------------------------- */
const work = ['Desk', 'Shifts', 'On my feet']
const remind = ['7:00 am', '8:00 am', '7:30 pm', '8:00 pm', '10:00 pm']
export function AboutYou() {
  const navigate = useNavigate()
  const go = useGo()
  const [age, setAge] = useState('58')
  const [year, setYear] = useState('2020')
  const [w, setW] = useState('Desk')
  const [times, setTimes] = useState(['8:00 am', '8:00 pm'])
  return (
    <Screen>
      <Header title="About you" back backTo="A2" />
      <Progress step={3} />
      <div className="grid grid-cols-2 gap-3">
        <Field label="Your age" inputMode="numeric" value={age} onChange={setAge} />
        <Field label="Year of diagnosis" inputMode="numeric" value={year} onChange={setYear} />
      </div>
      <section className="flex flex-col gap-2">
        <p className="text-sub font-bold">A typical work week</p>
        <div className="flex flex-wrap gap-2" role="radiogroup" aria-label="Work week">
          {work.map((x) => (
            <Chip key={x} on={w === x} onClick={() => setW(x)}>
              {x}
            </Chip>
          ))}
        </div>
      </section>
      <section className="flex flex-col gap-2">
        <p className="text-sub font-bold">Your medicines</p>
        <Button variant="secondary" icon={Camera} onClick={() => go('H2')}>
          Scan a label
        </Button>
        <Button variant="secondary" onClick={() => go('H8')}>
          Add by hand
        </Button>
      </section>
      <section className="flex flex-col gap-2">
        <p className="text-sub font-bold">Reminder times</p>
        <div className="flex flex-wrap gap-2">
          {remind.map((x) => (
            <Chip key={x} on={times.includes(x)} onClick={() => setTimes(times.includes(x) ? times.filter((y) => y !== x) : [...times, x])}>
              {x}
            </Chip>
          ))}
        </div>
      </section>
      <Footer>
        <Button onClick={() => navigate(href('A5'))}>Next</Button>
        <TextLink onClick={() => navigate(href('A4'))} className="self-center">
          Chat instead
        </TextLink>
      </Footer>
    </Screen>
  )
}

/* ------------------------------------- A4 chat setup ------------------------------------- */
const script = [
  { q: 'Hello. I will ask a few short questions. First, how old are you?', chips: ['Under 45', '45 to 54', '55 to 64', '65 or over'], field: 'Age' },
  { q: 'Thank you. How long have you had type 2 diabetes?', chips: ['Less than a year', '1 to 5 years', '6 to 10 years', 'More than 10 years'], field: 'Diagnosed' },
  { q: 'And what do your days look like?', chips: ['Desk work', 'Shift work', 'On my feet'], field: 'Work week' },
]
export function ChatSetup() {
  const navigate = useNavigate()
  const [i, setI] = useState(0)
  const [got, setGot] = useState<{ field: string; v: string }[]>([])
  const done = i >= script.length
  return (
    <Screen>
      <Header title="Set up by chat" back backTo="A3" />
      <Progress step={3} />
      <div className="flex flex-col gap-3">
        {script.slice(0, i + 1).map((s, k) => (
          <div key={s.field} className="flex flex-col gap-2">
            <p className="max-w-[90%] rounded-card rounded-bl-md bg-well px-4 py-3 text-body">{s.q}</p>
            {got[k] && <p className="ml-auto max-w-[85%] rounded-card rounded-br-md bg-brand px-4 py-3 text-body text-on-brand">{got[k]!.v}</p>}
          </div>
        ))}
        {!done && (
          <div className="flex flex-wrap gap-2">
            {script[i]!.chips.map((c) => (
              <Chip key={c} onClick={() => { setGot([...got, { field: script[i]!.field, v: c }]); setI(i + 1) }}>
                {c}
              </Chip>
            ))}
          </div>
        )}
      </div>
      <Card tone="soft" className="flex flex-col gap-2">
        <p className="text-sub font-bold text-ink2">Captured so far</p>
        {got.length === 0 ? <p className="text-body text-ink3">Nothing yet.</p> : got.map((g) => (
          <p key={g.field} className="flex justify-between gap-3 text-body"><span className="text-ink2">{g.field}</span><b>{g.v}</b></p>
        ))}
      </Card>
      <Footer>
        <Button disabled={!done} onClick={() => navigate(href('A5'))}>
          Next
        </Button>
        <TextLink onClick={() => navigate(href('A3'))} className="self-center">
          Use the form instead
        </TextLink>
      </Footer>
    </Screen>
  )
}

/* ------------------------------------ A5 connect data ------------------------------------ */
export function ConnectData() {
  const navigate = useNavigate()
  return (
    <Screen>
      <Header title="Connect your data" back backTo="A3" sub="These only send data to Smart Health." />
      <Progress step={5} />
      <ul className="flex flex-col gap-3">
        {[
          { icon: Watch, label: 'Smart watch', st: 'Connected' },
          { icon: Drop, label: 'Glucose sensor', st: 'Connected' },
          { icon: Camera, label: 'Phone camera', st: 'Allowed' },
        ].map((r) => (
          <li key={r.label}>
            <Card className="flex items-center gap-3">
              <span className="flex h-12 w-12 flex-none items-center justify-center rounded-full bg-brand-soft text-brand">
                <r.icon size={24} aria-hidden />
              </span>
              <span className="flex-1 text-body font-bold">{r.label}</span>
              <StatusPill tone="ok">{r.st}</StatusPill>
            </Card>
          </li>
        ))}
      </ul>
      <Footer>
        <Button onClick={() => navigate(href('B1'))}>Finish</Button>
      </Footer>
    </Screen>
  )
}
