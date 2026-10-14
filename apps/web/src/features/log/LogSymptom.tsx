/**
 * E4 — Log a symptom.
 *
 * Built to take about 30 seconds, laid out as the approved mock: the symptom choices in six groups, the strength and the
 * details for the chosen symptom, the red-flag card, the sensor reading and the three most recent symptoms beside them.
 * "How long did you feel it?" is a key field: its minutes are saved with the entry and stretch the symptom across that
 * many 5-minute buckets of the Gold timeline. The sensor reading is shown only when the sensor has one.
 *
 * Red-flag symptoms are saved and then go straight to J1 (urgent tier 2).
 */
import { useState } from 'react'
import { Trans, useTranslation } from 'react-i18next'
import { useFinishLog } from './useFinishLog'
import { useDay, useLogContext, useRecent } from '@/data/hooks'
import { useBack } from '@/app/navigation'
import { Screen } from '@/ui/layout'
import { Alert, Button, Field, TextLink } from '@/ui/primitives'
import { ArrowLeft } from '@/ui/icons'
import { cn } from '@/lib/cn'
import { CHOICES, DIZZY_FEELS, DURATIONS, RED_FLAGS, RED_VALUES, RELATIONS, SIDE_SYMPTOMS, SIDES, STRENGTH, SYMPTOM_GROUPS } from './symptom/data'
import { GroupBlock, Panel, Pill, RecentCard, RedFlagCard, SensorCard, StrengthTiles } from './symptom/parts'

const pad = (n: number) => String(n).padStart(2, '0')
const hhmm = (d: Date) => `${pad(d.getHours())}:${pad(d.getMinutes())}`
/** The local calendar day as YYYY-MM-DD, the form the day hook takes. */
const isoOf = (d: Date) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`

export function LogSymptom() {
  const { t } = useTranslation()
  const goBack = useBack('E1')
  const [label, setLabel] = useState<string | null>(null)
  const [sev, setSev] = useState(2)
  const [when, setWhen] = useState<'now' | 'at'>('now')
  const [day, setDay] = useState<'today' | 'yesterday'>('today')
  const [time, setTime] = useState(() => hhmm(new Date()))
  /** a number of minutes, 'unknown' (still going or not sure), or null (not answered yet) */
  const [dur, setDur] = useState<number | 'unknown' | null>(null)
  const [custom, setCustom] = useState('')
  const [more, setMore] = useState(true)
  const [side, setSide] = useState<string | null>(null)
  const [relation, setRelation] = useState<string | null>(null)
  const [feel, setFeel] = useState<string | null>(null)
  const [note, setNote] = useState('')
  const { save, pending, error } = useFinishLog()
  const { data: ctx } = useLogContext()
  const { data: recent } = useRecent()
  const nowDate = new Date()
  const { data: todayLine } = useDay(isoOf(nowDate))
  const red = label ? RED_VALUES.includes(label) : false
  const hasSide = !!label && SIDE_SYMPTOMS.includes(label)
  const isDizzy = label === 'Dizzy'

  /* the words on screen for a saved value; the English value itself is what is saved and checked */
  const say = (v: string | null) => {
    const c = CHOICES.find((x) => x.value === v)
    return c ? t(c.key, c.text) : (v ?? '')
  }
  const durText = (v: number | 'unknown') =>
    v === 'unknown'
      ? t('log.sym.stillGoing', 'Still going')
      : v === 60
        ? t('log.sym.oneHour', '1 hour')
        : v === 120
          ? t('log.sym.twoHours', '2 hours')
          : t('log.sym.minutes', '{{n}} min', { n: v })

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

  /* the one-line summary under the detail, built from the answers so far */
  const strength = STRENGTH.find((s) => s.n === sev)!
  const summary = [
    say(label),
    hasSide && side ? say(side) : null,
    t('log.sym.strengthOf', 'strength {{n}} of 5 ({{word}})', { n: sev, word: t(strength.key, strength.word) }),
    dur === null ? t('log.sym.durationOpen', 'how long not chosen yet') : durText(dur),
    relation ? say(relation) : null,
  ]
    .filter(Boolean)
    .join(', ')

  /* the segment for "when": Just now, or Earlier today / Another day with a time */
  const whenValue = when === 'now' ? 'now' : day
  const pickWhen = (v: 'now' | 'today' | 'yesterday') => {
    if (v === 'now') setWhen('now')
    else {
      setWhen('at')
      setDay(v)
    }
  }
  const segment = (v: 'now' | 'today' | 'yesterday', text: string) => (
    <button
      type="button"
      aria-pressed={whenValue === v}
      onClick={() => pickWhen(v)}
      className={cn(
        'press min-h-12 min-w-0 whitespace-nowrap rounded-chip px-4 text-sub',
        whenValue === v ? 'bg-card font-bold text-ink shadow-lift' : 'text-ink2',
      )}
    >
      {text}
    </button>
  )

  return (
    <Screen wide>
      <header className="flex flex-col gap-1 pb-1 pt-1">
        <div className="flex items-center gap-4">
          <button
            type="button"
            onClick={goBack}
            className="press inline-flex min-h-12 flex-none items-center gap-1.5 rounded-chip border border-line bg-card px-4 text-sub font-bold text-ink shadow-lift"
          >
            <ArrowLeft size={18} aria-hidden />
            {t('log.sym.backToLog', 'Back to Log')}
          </button>
          <h1 className="min-w-0 break-words font-serif text-h1 font-medium tracking-tight text-ink">{t('log.sym.title', 'Log a symptom')}</h1>
        </div>
        <p className="text-sub text-ink2">{t('log.sym.sub', 'About 30 seconds. Say what it was, how strong, and for how long.')}</p>
      </header>

      <div className="grid gap-4 [&>*]:min-w-0 lg:grid-cols-[minmax(0,1fr)_19rem] lg:items-start lg:gap-6 xl:grid-cols-[minmax(0,1fr)_20.75rem]">
        {/* red flags come first on a phone so help is never far down the page; on a laptop they sit top right, as in the mock */}
        <div className="lg:col-start-2 lg:row-start-1">
          <RedFlagCard title={t('log.sym.needHelp', 'Need help right now?')} sub={t('log.sym.tapHelp', 'Tap one and we take you to help straight away.')}>
            {RED_FLAGS.map((c) => (
              <Pill key={c.value} text={say(c.value)} on={label === c.value} onClick={() => pick(c.value)} red />
            ))}
          </RedFlagCard>
        </div>

        <div className="flex min-w-0 flex-col gap-4 lg:col-start-1 lg:row-span-3 lg:row-start-1">
          <Panel>
            <div className="mb-3 flex items-baseline justify-between gap-3">
              <h2 className="min-w-0 text-body font-bold">{t('log.sym.feeling', 'What are you feeling?')}</h2>
              <span className="flex-none text-micro text-ink2">{t('log.sym.pickOne', 'Pick one')}</span>
            </div>
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
              {SYMPTOM_GROUPS.map((g) => (
                <GroupBlock key={g.key} name={t(g.key, g.name)}>
                  {g.items.map((c) => (
                    <Pill key={c.value} text={say(c.value)} on={label === c.value} onClick={() => pick(c.value)} />
                  ))}
                </GroupBlock>
              ))}
            </div>
          </Panel>

          {red && (
            <Panel>
              <Button variant="danger" disabled={pending} onClick={submit}>
                {t('log.getHelp', 'Get help now')}
              </Button>
            </Panel>
          )}

          {!red && label && (
            <Panel className="flex flex-col gap-5">
              <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
                <h2 className="min-w-0 break-words text-body font-bold">
                  {t('log.sym.tellMore', 'Tell us a bit more about: {{symptom}}', { symptom: say(label) })}
                </h2>
                <TextLink onClick={() => setMore((m) => !m)} className="min-h-0">
                  {more ? t('log.sym.hideDetail', 'Hide detail') : t('log.sym.addDetail', 'Add detail (optional)')}
                </TextLink>
              </div>
              {label === 'Vomiting' && (
                <Alert tone="warn">{t('log.sym.vomitWarn', 'If you are vomiting and your glucose is high, get care today. Tell your clinic.')}</Alert>
              )}

              <div className="grid gap-5 2xl:grid-cols-[1.1fr_1fr] 2xl:gap-x-8">
                <section className="flex min-w-0 flex-col gap-2">
                  <h3 className="text-sub font-bold">{t('log.sym.strong', 'How strong was it?')}</h3>
                  <StrengthTiles value={sev} onChange={setSev} label={t('log.sym.strengthLabel', 'How strong it was')} />
                </section>

                <section className="flex min-w-0 flex-col gap-2">
                  <h3 className="text-sub font-bold">{t('log.sym.howLong', 'How long did you feel it?')}</h3>
                  <div className="flex flex-wrap gap-1.5">
                    {DURATIONS.map((d) => (
                      <Pill key={String(d)} text={durText(d)} on={dur === d && custom === ''} onClick={() => pickDur(d)} />
                    ))}
                  </div>
                  <Field
                    label={t('log.sym.typeMinutes', 'Or type the minutes')}
                    inputMode="numeric"
                    value={custom}
                    onChange={onCustom}
                    placeholder={t('log.sym.minutesPh', 'For example, 45')}
                    hint={dur === null ? t('log.sym.chooseOne', 'Choose one to continue.') : undefined}
                  />
                </section>

                {more && (hasSide || isDizzy) ? (
                  <section className="flex min-w-0 flex-col gap-2">
                    <h3 className="text-sub font-bold">{hasSide ? t('log.sym.where', 'Where?') : t('log.sym.feltLike', 'It felt like')}</h3>
                    <div className="flex flex-wrap gap-1.5">
                      {hasSide
                        ? SIDES.map((c) => (
                            <Pill key={c.value} text={say(c.value)} on={side === c.value} onClick={() => setSide(side === c.value ? null : c.value)} />
                          ))
                        : DIZZY_FEELS.map((c) => (
                            <Pill key={c.value} text={say(c.value)} on={feel === c.value} onClick={() => setFeel(feel === c.value ? null : c.value)} />
                          ))}
                    </div>
                  </section>
                ) : (
                  <div aria-hidden className="hidden 2xl:block" />
                )}

                <section className="flex min-w-0 flex-col gap-2">
                  <h3 className="text-sub font-bold">{t('log.sym.whenStart', 'When did it start?')}</h3>
                  <div
                    role="group"
                    aria-label={t('log.sym.whenLabel', 'When it started')}
                    className="flex max-w-full flex-wrap items-center gap-1 self-start rounded-chip bg-well p-1"
                  >
                    {segment('now', t('log.sym.justNow', 'Just now'))}
                    {segment('today', t('log.sym.earlierToday', 'Earlier today'))}
                    {segment('yesterday', t('log.sym.anotherDay', 'Another day'))}
                  </div>
                  {when === 'at' && (
                    <input
                      type="time"
                      value={time}
                      onChange={(e) => setTime(e.target.value)}
                      aria-label={t('log.sym.timeLabel', 'Time it started')}
                      className="min-h-12 w-full max-w-40 rounded-field border-[1.5px] border-line bg-card px-3.5 text-body text-ink focus:border-brand focus:outline-none"
                    />
                  )}
                </section>

                {more && (
                  <>
                    <section className="flex min-w-0 flex-col gap-2 2xl:col-span-2">
                      <h3 className="text-sub font-bold">{t('log.sym.around', 'Around what?')}</h3>
                      <div className="flex flex-wrap gap-1.5">
                        {RELATIONS.map((c) => (
                          <Pill
                            key={c.value}
                            text={say(c.value)}
                            on={relation === c.value}
                            onClick={() => setRelation(relation === c.value ? null : c.value)}
                          />
                        ))}
                      </div>
                    </section>
                    <div className="2xl:col-span-2">
                      <Field label={t('log.sym.note', 'Add a note (optional)')} value={note} onChange={setNote} multiline />
                    </div>
                  </>
                )}
              </div>

              <div className="flex flex-col gap-3 border-t border-line pt-4 sm:flex-row sm:items-center sm:gap-4">
                <div className="min-w-0 flex-1">
                  <p className="break-words text-sub font-bold">{summary}</p>
                  <p className="text-micro text-ink2">
                    {dur === null ? t('log.sym.chooseOne', 'Choose one to continue.') : t('log.sym.brief', 'It goes into your day and your doctor brief.')}
                  </p>
                </div>
                <div className="flex-none">
                  <Button className="sm:w-auto sm:px-7" disabled={!ready || pending} onClick={submit}>
                    {t('log.sym.save', 'Save symptom')}
                  </Button>
                </div>
              </div>
            </Panel>
          )}

          {error && <Alert tone="danger">{error}</Alert>}
        </div>

        {ctx?.glucose && (
          <div className="lg:col-start-2 lg:row-start-2">
            <SensorCard
              title={t('log.sym.filled', 'Filled in for you')}
              from={t('log.sym.fromSensor', 'from your sensor')}
              value={ctx.glucose.v}
              points={todayLine?.glucose}
              now={nowDate.getHours() * 60 + nowDate.getMinutes()}
              footer={
                <Trans
                  i18nKey="log.sym.glucoseNow"
                  defaults="Glucose now: <0>{{value}} mmol/L</0>, {{trend}} (from your sensor)."
                  values={{ value: ctx.glucose.v.toFixed(1), trend: ctx.glucose.trend }}
                  components={[<b key="0" />]}
                />
              }
            />
          </div>
        )}

        {recent && (
          <div className="lg:col-start-2 lg:row-start-3">
            <RecentCard
              title={t('log.sym.recent', 'Recent symptoms')}
              empty={t('log.sym.noRecent', 'No symptoms logged yet.')}
              entries={recent.filter((e) => e.kind === 'symptom').slice(0, 3)}
              detailOf={(e) => `${e.when} · ${e.detail}`}
            />
          </div>
        )}
      </div>
    </Screen>
  )
}
