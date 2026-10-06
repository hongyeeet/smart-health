/**
 * E4 — Log a symptom.
 *
 * Built to take about 30 seconds. "How long did you feel it?" is a key field: its minutes are saved with the entry and
 * stretch the symptom across that many 5-minute buckets of the Gold timeline. The sensor reading is shown only when
 * the sensor has one.
 *
 * Red-flag symptoms are saved and then go straight to J1 (urgent tier 2).
 */
import { useState } from 'react'
import { useFinishLog } from './useFinishLog'
import { useLogContext } from '@/data/hooks'
import { Header, Footer, Screen } from '@/ui/layout'
import { Rating } from '@/ui/controls'
import { Alert, Button, Card, Chip, Field, TextLink } from '@/ui/primitives'
import { Clock, Info } from '@/ui/icons'

const symptoms = [
  'More thirsty than usual', 'Passing more urine', 'Numbness', 'Tingling',
  'Foot pain', 'Blurry vision', 'Tired more than usual', 'Dizzy',
  'Headache', 'Upset stomach', 'Vomiting', 'Night sweats', 'Slow-healing wound', 'Something else',
]
const redFlags = [
  'Chest pain', 'Confusion', 'Fainting', 'Breathlessness at rest',
  'Sudden vision loss or a curtain across my vision',
]
const sideSymptoms = ['Numbness', 'Tingling', 'Foot pain']
const durationChips: { min: number; label: string }[] = [
  { min: 5, label: '5 min' }, { min: 10, label: '10 min' }, { min: 15, label: '15 min' },
  { min: 30, label: '30 min' }, { min: 60, label: '1 hour' }, { min: 120, label: '2 hours' },
]
const sides = ['Left foot', 'Right foot', 'Both feet', 'Hands', 'Somewhere else']
const relations = ['Before a meal', 'After a meal', 'After exercise', 'At rest', 'While asleep']
const dizzyFeels = ['When I stand up', 'Shaky or sweaty', 'Spinning']

const pad = (n: number) => String(n).padStart(2, '0')
const hhmm = (d: Date) => `${pad(d.getHours())}:${pad(d.getMinutes())}`

export function LogSymptom() {
  const [label, setLabel] = useState<string | null>(null)
  const [sev, setSev] = useState(2)
  const [when, setWhen] = useState<'now' | 'at'>('now')
  const [day, setDay] = useState<'today' | 'yesterday'>('today')
  const [time, setTime] = useState(() => hhmm(new Date()))
  /** a number of minutes, 'unknown' (still going or not sure), or null (not answered yet) */
  const [dur, setDur] = useState<number | 'unknown' | null>(null)
  const [custom, setCustom] = useState('')
  const [more, setMore] = useState(false)
  const [side, setSide] = useState<string | null>(null)
  const [relation, setRelation] = useState<string | null>(null)
  const [feel, setFeel] = useState<string | null>(null)
  const [note, setNote] = useState('')
  const { save, pending, error } = useFinishLog()
  const { data: ctx } = useLogContext()
  const red = label ? redFlags.includes(label) : false

  const pick = (l: string) => {
    setLabel(l)
    setSide(null)
    setFeel(null)
  }
  const pickDur = (v: number | 'unknown') => {
    setDur(dur === v ? null : v)
    setCustom('')
  }
  const onCustom = (v: string) => {
    const digits = v.replace(/\D/g, '').slice(0, 4)
    setCustom(digits)
    setDur(digits ? Math.min(1440, Math.max(1, Number(digits))) : null)
  }

  const occurredAt = () => {
    if (when === 'now') return new Date()
    const [h, m] = time.split(':').map(Number)
    const d = new Date()
    if (day === 'yesterday') d.setDate(d.getDate() - 1)
    d.setHours(h ?? 0, m ?? 0, 0, 0)
    return d
  }
  const ready = !!label && (red || dur !== null)

  const submit = () => {
    if (!label) return
    if (red) {
      save({ kind: 'symptom', label, severity: 5, occurredAt: new Date().toISOString() })
      return
    }
    save({
      kind: 'symptom',
      label,
      severity: sev,
      occurredAt: occurredAt().toISOString(),
      durationMin: typeof dur === 'number' ? dur : undefined,
      side: side ?? undefined,
      relation: relation ?? undefined,
      feel: feel ?? undefined,
      note: note.trim() || undefined,
    })
  }

  return (
    <Screen>
      <Header title="Log a symptom" back backTo="E1" sub="About 30 seconds. Say what it was, how strong, and for how long." />
      {ctx?.glucose && (
        <Alert tone="info" icon={Info} title="Filled in for you">
          Glucose now: <b>{ctx.glucose.v.toFixed(1)} mmol/L</b>, {ctx.glucose.trend} (from your sensor).
        </Alert>
      )}
      <div className="flex flex-wrap gap-2" role="radiogroup" aria-label="Symptom">
        {symptoms.map((s) => (
          <Chip key={s} on={label === s} onClick={() => pick(s)}>
            {s}
          </Chip>
        ))}
      </div>
      <Card tone="soft" className="flex flex-col gap-2">
        <p className="text-sub font-bold text-ink2">Need help right now?</p>
        <div className="flex flex-wrap gap-2">
          {redFlags.map((s) => (
            <Chip key={s} on={label === s} onClick={() => pick(s)}>
              {s}
            </Chip>
          ))}
        </div>
      </Card>
      {label === 'Vomiting' && <Alert tone="warn">If you are vomiting and your glucose is high, get care today. Tell your clinic.</Alert>}

      {!red && label && (
        <>
          <Rating label="How strong" value={sev} onChange={setSev} lowLabel="Barely noticeable" highLabel="Severe" />

          <section className="flex flex-col gap-2">
            <p className="flex items-center gap-2 text-body font-bold">
              <Clock size={20} aria-hidden /> How long did you feel it?
            </p>
            <div className="flex flex-wrap gap-2" role="radiogroup" aria-label="How long you felt it">
              {durationChips.map((d) => (
                <Chip key={d.min} on={dur === d.min && custom === ''} onClick={() => pickDur(d.min)}>
                  {d.label}
                </Chip>
              ))}
              <Chip on={dur === 'unknown'} onClick={() => pickDur('unknown')}>
                Still going or not sure
              </Chip>
            </div>
            <Field label="Or type the minutes" inputMode="numeric" value={custom} onChange={onCustom} placeholder="For example, 45" hint={dur === null ? 'Choose one to continue.' : undefined} />
          </section>

          <section className="flex flex-col gap-2">
            <p className="text-body font-bold">When did it start?</p>
            <div className="flex flex-wrap gap-2" role="radiogroup" aria-label="When it started">
              <Chip on={when === 'now'} onClick={() => setWhen('now')}>
                Just now
              </Chip>
              <Chip on={when === 'at'} onClick={() => setWhen('at')}>
                Pick a time
              </Chip>
            </div>
            {when === 'at' && (
              <div className="flex flex-wrap items-center gap-2">
                <Chip on={day === 'today'} onClick={() => setDay('today')}>
                  Today
                </Chip>
                <Chip on={day === 'yesterday'} onClick={() => setDay('yesterday')}>
                  Yesterday
                </Chip>
                <input
                  type="time"
                  value={time}
                  onChange={(e) => setTime(e.target.value)}
                  aria-label="Time it started"
                  className="min-h-12 rounded-field border-[1.5px] border-line bg-card px-3.5 text-body text-ink focus:border-brand focus:outline-none"
                />
              </div>
            )}
          </section>

          <TextLink onClick={() => setMore((m) => !m)} className="self-start">
            {more ? 'Hide detail' : 'Add detail (optional)'}
          </TextLink>
          {more && (
            <Card className="flex flex-col gap-4">
              {sideSymptoms.includes(label) && (
                <section className="flex flex-col gap-2">
                  <p className="text-sub font-bold">Where?</p>
                  <div className="flex flex-wrap gap-2">
                    {sides.map((d) => (
                      <Chip key={d} on={side === d} onClick={() => setSide(side === d ? null : d)}>
                        {d}
                      </Chip>
                    ))}
                  </div>
                </section>
              )}
              {label === 'Dizzy' && (
                <section className="flex flex-col gap-2">
                  <p className="text-sub font-bold">It felt like</p>
                  <div className="flex flex-wrap gap-2">
                    {dizzyFeels.map((d) => (
                      <Chip key={d} on={feel === d} onClick={() => setFeel(feel === d ? null : d)}>
                        {d}
                      </Chip>
                    ))}
                  </div>
                </section>
              )}
              <section className="flex flex-col gap-2">
                <p className="text-sub font-bold">Around a meal or exercise?</p>
                <div className="flex flex-wrap gap-2">
                  {relations.map((d) => (
                    <Chip key={d} on={relation === d} onClick={() => setRelation(relation === d ? null : d)}>
                      {d}
                    </Chip>
                  ))}
                </div>
              </section>
              <Field label="Add a note (optional)" value={note} onChange={setNote} multiline />
            </Card>
          )}
        </>
      )}
      {error && <Alert tone="danger">{error}</Alert>}

      <Footer>
        <Button variant={red ? 'danger' : 'primary'} disabled={!ready || pending} onClick={submit}>
          {red ? 'Get help now' : 'Save symptom'}
        </Button>
      </Footer>
    </Screen>
  )
}
