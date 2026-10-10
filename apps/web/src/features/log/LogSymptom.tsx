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
import { Trans, useTranslation } from 'react-i18next'
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
  const { t } = useTranslation()
  /* display text only: the English name is what is saved and checked, so each choice keeps its English value */
  const txt: Record<string, string> = {
    'More thirsty than usual': t('log.sym.thirsty', 'More thirsty than usual'),
    'Passing more urine': t('log.sym.urine', 'Passing more urine'),
    'Numbness': t('log.sym.numbness', 'Numbness'),
    'Tingling': t('log.sym.tingling', 'Tingling'),
    'Foot pain': t('log.sym.footPain', 'Foot pain'),
    'Blurry vision': t('log.sym.blurry', 'Blurry vision'),
    'Tired more than usual': t('log.sym.tired', 'Tired more than usual'),
    'Dizzy': t('log.sym.dizzy', 'Dizzy'),
    'Headache': t('log.sym.headache', 'Headache'),
    'Upset stomach': t('log.sym.stomach', 'Upset stomach'),
    'Vomiting': t('log.sym.vomiting', 'Vomiting'),
    'Night sweats': t('log.sym.nightSweats', 'Night sweats'),
    'Slow-healing wound': t('log.sym.wound', 'Slow-healing wound'),
    'Something else': t('log.sym.other', 'Something else'),
    'Chest pain': t('log.sym.chestPain', 'Chest pain'),
    'Confusion': t('log.sym.confusion', 'Confusion'),
    'Fainting': t('log.sym.fainting', 'Fainting'),
    'Breathlessness at rest': t('log.sym.breathless', 'Breathlessness at rest'),
    'Sudden vision loss or a curtain across my vision': t('log.sym.visionLoss', 'Sudden vision loss or a curtain across my vision'),
    'Left foot': t('log.sym.leftFoot', 'Left foot'),
    'Right foot': t('log.sym.rightFoot', 'Right foot'),
    'Both feet': t('log.sym.bothFeet', 'Both feet'),
    'Hands': t('log.sym.hands', 'Hands'),
    'Somewhere else': t('log.sym.elsewhere', 'Somewhere else'),
    'Before a meal': t('log.sym.beforeMeal', 'Before a meal'),
    'After a meal': t('log.sym.afterMeal', 'After a meal'),
    'After exercise': t('log.sym.afterExercise', 'After exercise'),
    'At rest': t('log.sym.atRest', 'At rest'),
    'While asleep': t('log.sym.asleep', 'While asleep'),
    'When I stand up': t('log.sym.standUp', 'When I stand up'),
    'Shaky or sweaty': t('log.sym.shaky', 'Shaky or sweaty'),
    'Spinning': t('log.sym.spinning', 'Spinning'),
  }
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
      <Header title={t('log.sym.title', 'Log a symptom')} back backTo="E1" sub={t('log.sym.sub', 'About 30 seconds. Say what it was, how strong, and for how long.')} />
      {ctx?.glucose && (
        <Alert tone="info" icon={Info} title={t('log.sym.filled', 'Filled in for you')}>
          <Trans i18nKey="log.sym.glucoseNow" defaults="Glucose now: <0>{{value}} mmol/L</0>, {{trend}} (from your sensor)." values={{ value: ctx.glucose.v.toFixed(1), trend: ctx.glucose.trend }} components={[<b key="0" />]} />
        </Alert>
      )}
      <div className="flex flex-wrap gap-2" role="radiogroup" aria-label={t('log.sym.label', 'Symptom')}>
        {symptoms.map((s) => (
          <Chip key={s} on={label === s} onClick={() => pick(s)}>
            {txt[s]}
          </Chip>
        ))}
      </div>
      <Card tone="soft" className="flex flex-col gap-2">
        <p className="text-sub font-bold text-ink2">{t('log.sym.needHelp', 'Need help right now?')}</p>
        <div className="flex flex-wrap gap-2">
          {redFlags.map((s) => (
            <Chip key={s} on={label === s} onClick={() => pick(s)}>
              {txt[s]}
            </Chip>
          ))}
        </div>
      </Card>
      {label === 'Vomiting' && <Alert tone="warn">{t('log.sym.vomitWarn', 'If you are vomiting and your glucose is high, get care today. Tell your clinic.')}</Alert>}

      {!red && label && (
        <>
          <Rating label={t('log.sym.strong', 'How strong')} value={sev} onChange={setSev} lowLabel={t('log.sym.weak', 'Barely noticeable')} highLabel={t('log.sym.severe', 'Severe')} />

          <section className="flex flex-col gap-2">
            <p className="flex items-center gap-2 text-body font-bold">
              <Clock size={20} aria-hidden /> {t('log.sym.howLong', 'How long did you feel it?')}
            </p>
            <div className="flex flex-wrap gap-2" role="radiogroup" aria-label={t('log.sym.howLongLabel', 'How long you felt it')}>
              {durationChips.map((d) => (
                <Chip key={d.min} on={dur === d.min && custom === ''} onClick={() => pickDur(d.min)}>
                  {d.min === 60 ? t('log.sym.oneHour', '1 hour') : d.min === 120 ? t('log.sym.twoHours', '2 hours') : d.label}
                </Chip>
              ))}
              <Chip on={dur === 'unknown'} onClick={() => pickDur('unknown')}>
                {t('log.sym.unknown', 'Still going or not sure')}
              </Chip>
            </div>
            <Field label={t('log.sym.typeMinutes', 'Or type the minutes')} inputMode="numeric" value={custom} onChange={onCustom} placeholder={t('log.sym.minutesPh', 'For example, 45')} hint={dur === null ? t('log.sym.chooseOne', 'Choose one to continue.') : undefined} />
          </section>

          <section className="flex flex-col gap-2">
            <p className="text-body font-bold">{t('log.sym.whenStart', 'When did it start?')}</p>
            <div className="flex flex-wrap gap-2" role="radiogroup" aria-label={t('log.sym.whenLabel', 'When it started')}>
              <Chip on={when === 'now'} onClick={() => setWhen('now')}>
                {t('log.sym.justNow', 'Just now')}
              </Chip>
              <Chip on={when === 'at'} onClick={() => setWhen('at')}>
                {t('log.sym.pickTime', 'Pick a time')}
              </Chip>
            </div>
            {when === 'at' && (
              <div className="flex flex-wrap items-center gap-2">
                <Chip on={day === 'today'} onClick={() => setDay('today')}>
                  {t('log.sym.today', 'Today')}
                </Chip>
                <Chip on={day === 'yesterday'} onClick={() => setDay('yesterday')}>
                  {t('log.sym.yesterday', 'Yesterday')}
                </Chip>
                <input
                  type="time"
                  value={time}
                  onChange={(e) => setTime(e.target.value)}
                  aria-label={t('log.sym.timeLabel', 'Time it started')}
                  className="min-h-12 rounded-field border-[1.5px] border-line bg-card px-3.5 text-body text-ink focus:border-brand focus:outline-none"
                />
              </div>
            )}
          </section>

          <TextLink onClick={() => setMore((m) => !m)} className="self-start">
            {more ? t('log.sym.hideDetail', 'Hide detail') : t('log.sym.addDetail', 'Add detail (optional)')}
          </TextLink>
          {more && (
            <Card className="flex flex-col gap-4">
              {sideSymptoms.includes(label) && (
                <section className="flex flex-col gap-2">
                  <p className="text-sub font-bold">{t('log.sym.where', 'Where?')}</p>
                  <div className="flex flex-wrap gap-2">
                    {sides.map((d) => (
                      <Chip key={d} on={side === d} onClick={() => setSide(side === d ? null : d)}>
                        {txt[d]}
                      </Chip>
                    ))}
                  </div>
                </section>
              )}
              {label === 'Dizzy' && (
                <section className="flex flex-col gap-2">
                  <p className="text-sub font-bold">{t('log.sym.feltLike', 'It felt like')}</p>
                  <div className="flex flex-wrap gap-2">
                    {dizzyFeels.map((d) => (
                      <Chip key={d} on={feel === d} onClick={() => setFeel(feel === d ? null : d)}>
                        {txt[d]}
                      </Chip>
                    ))}
                  </div>
                </section>
              )}
              <section className="flex flex-col gap-2">
                <p className="text-sub font-bold">{t('log.sym.around', 'Around a meal or exercise?')}</p>
                <div className="flex flex-wrap gap-2">
                  {relations.map((d) => (
                    <Chip key={d} on={relation === d} onClick={() => setRelation(relation === d ? null : d)}>
                      {txt[d]}
                    </Chip>
                  ))}
                </div>
              </section>
              <Field label={t('log.sym.note', 'Add a note (optional)')} value={note} onChange={setNote} multiline />
            </Card>
          )}
        </>
      )}
      {error && <Alert tone="danger">{error}</Alert>}

      <Footer>
        <Button variant={red ? 'danger' : 'primary'} disabled={!ready || pending} onClick={submit}>
          {red ? t('log.getHelp', 'Get help now') : t('log.sym.save', 'Save symptom')}
        </Button>
      </Footer>
    </Screen>
  )
}
