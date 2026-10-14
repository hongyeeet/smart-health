/**
 * L1 — Doctor brief, the in-depth one. Pick the period (7, 14, 30 or 90 days) and see the patient record, the analysis (six health numbers
 * graded against the person's own baseline and the key findings), the four Overview charts for the period (glucose, heart rate, SpO2,
 * blood pressure) each with a reasoning line, what the app has learnt, medicines and symptoms, the questions for the doctor, what is worth
 * discussing and the next appointment. Everything shown is what the server computed, so the person sees what the doctor will see.
 */
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useQueryClient } from '@tanstack/react-query'
import { useDoctorReport, useInsightsTimeline, useLearned } from '@/data/hooks'
import type { DoctorReport, InsightsTimeline, ReportDays } from '@/data/types'
import { href } from '@/app/routeIds'
import { useGo } from '@/app/navigation'
import { cn } from '@/lib/cn'
import { Header, Screen } from '@/ui/layout'
import { Alert, Button, Card, Skeleton, StatusPill, TextLink, type Tone } from '@/ui/primitives'
import { Segmented } from '@/ui/controls'
import { FilePdf, Info, ShareNetwork, Warning, WarningCircle, type IconType } from '@/ui/icons'
import { PILL_COLOR, Pill, Plot, type PillKey } from '@/features/insights/Timeline'
import { GradeTile } from '@/features/insights/HealthOverview'
import { Gate } from '@/features/insights/shared'
import { TONE, statusWords, grade, NEUTRAL, type Level } from '@/features/insights/healthGrade'
import { useAddQuestion, useRemoveQuestion } from '@/features/me/care/api'
import { APPOINTMENT_KIND, formatWhen, useShareContext } from './shareApi'
import { healthTiles, learnedRows, plotReasons, type PlotKey } from './analysis'

const ALERT_TAG: Record<DoctorReport['alerts'][number]['priority'], { tone: Tone; icon: IconType }> = {
  urgent: { tone: 'danger', icon: WarningCircle },
  interaction: { tone: 'warn', icon: Warning },
  review: { tone: 'neutral', icon: Info },
}

const ALL_ON: Record<PillKey, boolean> = {
  glucose: true,
  heart: true,
  spo2: true,
  bp: true,
  meals: true,
  exercise: true,
  symptoms: true,
  missed: true,
  work: true,
}

/** One card's chart, with the log lanes the person has switched on; the marker, the stats for the day and the legend come with it. */
const forChart = (k: PlotKey, on: Record<PillKey, boolean>): Record<PillKey, boolean> => ({
  ...on,
  glucose: k === 'glucose',
  heart: k === 'heart',
  spo2: k === 'spo2',
  bp: k === 'bp',
})

/** The day shown as a short month and day in the clinic's time zone (Singapore), e.g. OCT and 28. */
const PILLS: [PillKey, string, string][] = [
  ['glucose', 'insights.tl.glucose', 'Glucose'],
  ['heart', 'insights.tl.heart', 'Heart rate'],
  ['spo2', 'insights.tl.spo2', 'SpO2'],
  ['bp', 'insights.tl.bp', 'Blood pressure'],
  ['meals', 'insights.tl.lane.meals', 'Meals'],
  ['exercise', 'insights.tl.lane.exercise', 'Exercise'],
  ['symptoms', 'insights.tl.lane.symptoms', 'Symptoms'],
  ['missed', 'insights.tl.lane.missedDoses', 'Missed doses'],
  ['work', 'insights.tl.lane.workDays', 'Work days'],
]

const dayParts = (iso: string) => {
  const d = new Date(iso)
  return {
    month: d.toLocaleDateString('en-GB', { month: 'short', timeZone: 'Asia/Singapore' }).toUpperCase(),
    day: d.toLocaleDateString('en-GB', { day: 'numeric', timeZone: 'Asia/Singapore' }),
  }
}

/** Two letters of the name for the round avatar, e.g. "MT" for Mr Tan. */
const initials = (name: string) =>
  name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w.charAt(0).toUpperCase())
    .join('')

export function BriefHome() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const go = useGo()
  const qc = useQueryClient()
  const [days, setDays] = useState<ReportDays>(14)
  const report = useDoctorReport(days)
  const tl = useInsightsTimeline(days)
  const learned = useLearned()
  const context = useShareContext()
  const add = useAddQuestion()
  const remove = useRemoveQuestion()
  const [draft, setDraft] = useState('')
  const [show, setShow] = useState<Record<PillKey, boolean>>(ALL_ON)
  const data = report.data
  const tlData: InsightsTimeline | undefined = tl.data

  const KIND: Record<DoctorReport['worthDiscussing'][number]['kind'], string> = {
    clash: t('brief.kind.clash', 'Medicines'),
    adherence: t('brief.kind.adherence', 'Missed doses'),
    pattern: t('brief.kind.pattern', 'Pattern'),
    fact: t('brief.kind.fact', 'Your note'),
  }
  const ALERT_WORD: Record<DoctorReport['alerts'][number]['priority'], string> = {
    urgent: t('brief.tag.urgent', 'Urgent'),
    interaction: t('brief.tag.interaction', 'Interaction'),
    review: t('brief.tag.review', 'Review'),
  }

  const latest = data ? new Date(`${data.period.end}T12:00:00`).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' }) : ''
  const careTeam = data?.summary.find((r) => /care team|doctor|clinic/i.test(r.label))?.value ?? t('brief.careTeamNone', 'Not on record')
  const medicines = data?.medicines ?? []
  const facts = learnedRows(learned.data?.groups.flatMap((g) => g.facts) ?? []).slice(0, 6)
  const nextAppt = context.data?.nextAppointment ?? null
  const addQuestion = () => {
    const text = draft.trim()
    if (text.length < 3) return
    add.mutate(
      { text },
      {
        onSuccess: () => {
          setDraft('')
          void qc.invalidateQueries({ queryKey: ['shareContext'] })
        },
      },
    )
  }

  return (
    <Screen wide>
      <Header
        title={t('brief.title', 'Doctor brief')}
        back
        backTo="K1"
        sub={t('brief.sub', 'A report of your readings, symptoms and medicines to take to your next visit. You see exactly what your doctor sees.')}
      />
      <div className="flex flex-wrap items-center gap-2">
        <Button
          variant="secondary"
          size="md"
          className="!w-auto"
          icon={FilePdf}
          disabled={!data}
          onClick={() => navigate(`${href('L3')}?days=${days}`, { state: { from: 'L1' } })}
        >
          {t('brief.open', 'Open the printable report')}
        </Button>
        <Button size="md" className="!w-auto" icon={ShareNetwork} disabled={!data} onClick={() => go('L2', { sheet: { days } })}>
          {t('brief.share', 'Share with my doctor')}
        </Button>
        {data && (
          <span aria-hidden className="ml-auto flex h-11 w-11 flex-none items-center justify-center rounded-full bg-brand text-sub font-bold text-on-brand">
            {initials(data.patient.name)}
          </span>
        )}
      </div>

      {report.isLoading && <Skeleton className="h-64" />}
      {report.isError && <Alert tone="warn">{t('brief.error', 'We could not prepare your report just now. Please try again in a moment.')}</Alert>}

      {data && (
        <>
          {/* the patient record and the analysis side by side from a laptop up, one column on a phone */}
          <div className="grid gap-4 lg:grid-cols-[minmax(0,2fr)_minmax(0,3fr)] lg:items-start [&>*]:min-w-0">
            <Card as="section" className="flex flex-col gap-3">
              <h2 className="font-serif text-h2 font-medium tracking-tight">{t('brief.patient', 'Patient record')}</h2>
              <dl className="flex flex-col divide-y divide-line text-body">
                <div className="flex flex-col gap-0.5 py-2 first:pt-0">
                  <dt className="text-sub text-ink2">{t('brief.name', 'Name')}</dt>
                  <dd className="font-bold">{data.patient.name}</dd>
                </div>
                <div className="flex flex-col gap-0.5 py-2">
                  <dt className="text-sub text-ink2">{t('brief.sexAge', 'Sex and age')}</dt>
                  <dd>{data.patient.sexAge}</dd>
                </div>
                <div className="flex flex-col gap-0.5 py-2">
                  <dt className="text-sub text-ink2">{t('brief.conditions', 'Conditions')}</dt>
                  <dd>{data.patient.diagnosis}</dd>
                </div>
                <div className="flex flex-col gap-0.5 py-2">
                  <dt className="text-sub text-ink2">{t('brief.medicinesLabel', 'Medicines')}</dt>
                  <dd>{medicines.length ? medicines.map((m) => m.name).join(', ') : t('brief.noMedicines', 'None recorded')}</dd>
                </div>
                <div className="flex flex-col gap-0.5 py-2 last:pb-0">
                  <dt className="text-sub text-ink2">{t('brief.careTeam', 'Care team')}</dt>
                  <dd>{careTeam}</dd>
                </div>
              </dl>
            </Card>

            <Card as="section" tone="hero" className="flex flex-col gap-3">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0">
                  <h2 className="text-body font-bold">{data.period.label}</h2>
                  <p className="text-sub text-ink2">{t('brief.latestData', 'Latest data, {{end}}. From your readings, logs and devices.', { end: latest })}</p>
                </div>
                <div className="w-full sm:w-auto sm:min-w-[22rem]">
                  <Segmented<ReportDays>
                    label={t('brief.period', 'Period')}
                    value={days}
                    onChange={setDays}
                    options={[
                      { value: 7, label: t('brief.days7', '7 days') },
                      { value: 14, label: t('brief.days14', '14 days') },
                      { value: 30, label: t('brief.days30', '30 days') },
                      { value: 90, label: t('brief.days90', '90 days') },
                    ]}
                  />
                </div>
              </div>

              {tlData ? (
                <div className="grid grid-cols-2 gap-1.5 sm:grid-cols-3">
                  {healthTiles(t, tlData).map((x) => (
                    <GradeTile key={x.kind} kind={x.kind} label={x.label} value={x.value} unit={x.unit} graded={x.graded} />
                  ))}
                </div>
              ) : (
                <Skeleton className="h-24" />
              )}

              <div className="mt-1 flex items-center justify-between gap-2">
                <h3 className="text-body font-bold">{t('brief.findings', 'Key findings')}</h3>
                {data.keyFindingsSource === 'ai' && (
                  <span className="rounded-chip bg-info-soft px-2.5 py-0.5 text-micro font-bold text-info">{t('brief.aiTag', 'AI insight')}</span>
                )}
              </div>
              <ul className="flex flex-col gap-2 text-body">
                {data.keyFindings.map((f) => (
                  <li key={f} className="flex items-start gap-3">
                    <span aria-hidden className="mt-2 h-2 w-2 flex-none rounded-full bg-brand" />
                    <span className="min-w-0 break-words">{f}</span>
                  </li>
                ))}
              </ul>
              {data.keyFindingsSource === 'ai' && (
                <p className="text-micro text-ink3">
                  {t(
                    'brief.aiNote',
                    'Written by an AI from the numbers in this report. The numbers come from your data. Not medical advice: your doctor decides what they mean.',
                  )}
                </p>
              )}
            </Card>
          </div>

          <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_340px] lg:items-start [&>*]:min-w-0">
            <div className="flex flex-col gap-4">
              {/* the four Overview charts for the period, each with a reasoning line built from the numbers */}
              <Gate
                data={tlData}
                isError={tl.isError && !tlData}
                empty={!!tlData && !tlData.period.hasData}
                emptyText={t('brief.chartsEmpty', 'Log a few readings and your charts fill in here.')}
              >
                {tlData && (
                  <div role="group" aria-label={t('brief.filterLabel', 'Show on the charts')} className="flex flex-wrap gap-2">
                    {PILLS.map(([k, label, fb]) => (
                      <Pill key={k} on={show[k]} color={PILL_COLOR[k]} label={t(label, fb)} onClick={() => setShow((x) => ({ ...x, [k]: !x[k] }))} />
                    ))}
                  </div>
                )}
                {tlData &&
                  plotReasons(t, tlData)
                    .filter((r) => show[r.key])
                    .map((r) => (
                      <Card key={r.key} as="section" className="flex flex-col gap-2">
                        <h2 className="text-body font-bold">{r.title}</h2>
                        <p className="break-words text-sub text-ink2">
                          <span className="font-bold text-ink">{t('brief.whyMatters', 'Why this matters.')}</span> {r.why}{' '}
                          <span className="font-bold text-ink">{t('brief.sawLabel', 'What we saw.')}</span> {r.saw}
                        </p>
                        <Plot data={tlData} compact={r.key !== 'glucose'} show={forChart(r.key, show)} openDay={(date) => go('D1', { params: { date } })} />
                      </Card>
                    ))}
              </Gate>

              <Card as="section" className="flex flex-col gap-2">
                <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
                  <h2 className="text-body font-bold">{t('brief.medicines', 'Medicines adherence')}</h2>
                  <span className="text-sub text-ink2">{t('brief.medicinesSub', 'Doses taken against doses planned')}</span>
                </div>
                {medicines.length === 0 ? (
                  <p className="text-body text-ink2">{t('brief.noMedicinesLong', 'No medicines are recorded.')}</p>
                ) : (
                  <ul className="flex flex-col">
                    {medicines.map((m) => {
                      const g = grade('doses', m.adherencePct, null)
                      const tone = g.level == null ? NEUTRAL : TONE[g.level as Exclude<Level, null>]
                      return (
                        <li key={m.name} className="flex min-h-14 flex-wrap items-center gap-x-4 gap-y-1 border-t border-line py-2 first:border-t-0">
                          <div className="min-w-0 flex-1 basis-48">
                            <p className="truncate font-bold leading-tight">{m.name}</p>
                            <p className="truncate text-micro text-ink2">{m.regimen}</p>
                          </div>
                          <div className="h-2 w-40 max-w-full flex-1 overflow-hidden rounded-full bg-well sm:max-w-[12rem]">
                            <div className={cn('h-full rounded-full', tone.dot)} style={{ width: `${m.adherencePct ?? 0}%` }} />
                          </div>
                          <span className="num w-28 text-right text-sub font-bold">
                            {m.taken ?? '–'} {t('brief.of', 'of')} {m.scheduled ?? '–'}
                          </span>
                          <span className={cn('flex w-32 items-center gap-1.5 text-sub font-bold', tone.text)}>
                            <span className={cn('h-2 w-2 flex-none rounded-full', tone.dot)} aria-hidden />
                            {m.adherencePct == null ? t('brief.noPlanned', 'No doses planned') : statusWords(t, 'doses', g)}
                          </span>
                        </li>
                      )
                    })}
                  </ul>
                )}
                {data.medicinesNote && <p className="text-micro text-ink3">{data.medicinesNote}</p>}
              </Card>

              <Card as="section" className="flex flex-col gap-2">
                <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
                  <h2 className="text-body font-bold">{t('brief.symptoms', 'Symptoms')}</h2>
                  <span className="text-sub text-ink2">{t('brief.symptomsSub', 'Logged in this period')}</span>
                </div>
                {data.symptoms.length === 0 ? (
                  <p className="text-body text-ink2">{t('brief.noSymptoms', 'No symptoms were logged in this period.')}</p>
                ) : (
                  <ul className="flex flex-col">
                    {data.symptoms.map((s) => (
                      <li key={s.symptom} className="flex min-h-12 flex-wrap items-center gap-x-4 gap-y-0.5 border-t border-line py-2 first:border-t-0">
                        <span className="min-w-0 flex-1 basis-40 font-bold">{s.symptom}</span>
                        <span className="num text-sub font-bold">{t('brief.loggedTimes', '{{n}} logged', { n: s.logged })}</span>
                        <span className="min-w-0 basis-full text-micro text-ink2 sm:basis-auto sm:max-w-[16rem] sm:truncate">{s.note}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </Card>

              <Alert tone="info">
                {t(
                  'brief.note',
                  'The numbers are counts from what you and your devices recorded, worked out by fixed rules. Where the key findings say AI insight, an AI wrote the sentences from those numbers. They are for your doctor to interpret. Smart Health does not diagnose or advise on medicines.',
                )}
              </Alert>
            </div>

            <div className="flex flex-col gap-4">
              <Card as="section" className="flex flex-col gap-3">
                <div className="flex items-baseline justify-between gap-2">
                  <h2 className="text-body font-bold">{t('brief.questions', 'Questions for your doctor')}</h2>
                  <span className="text-sub text-ink2">{t('brief.qOpen', '{{n}} open', { n: context.data?.questions.length ?? 0 })}</span>
                </div>
                {context.data && context.data.questions.length > 0 ? (
                  <ul className="flex flex-col">
                    {context.data.questions.map((q, i) => (
                      <li key={q.id} className="flex items-start gap-2.5 border-t border-line py-2 first:border-t-0">
                        <span className="flex h-6 w-6 flex-none items-center justify-center rounded-full bg-well text-micro font-bold text-ink2">{i + 1}</span>
                        <span className="min-w-0 flex-1 break-words text-body">{q.text}</span>
                        <button
                          type="button"
                          aria-label={t('brief.removeQ', 'Remove this question')}
                          disabled={remove.isPending}
                          onClick={() => remove.mutate(q.id, { onSuccess: () => void qc.invalidateQueries({ queryKey: ['shareContext'] }) })}
                          className="press -mr-1 flex h-9 w-9 flex-none items-center justify-center rounded-full text-lg text-ink3 hover:bg-well"
                        >
                          ×
                        </button>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-body text-ink2">
                    {t('brief.noQuestions', 'You have no open questions yet. Add one below or from a medicine or your care plan.')}
                  </p>
                )}
                <form
                  className="flex gap-2"
                  onSubmit={(e) => {
                    e.preventDefault()
                    addQuestion()
                  }}
                >
                  <input
                    value={draft}
                    onChange={(e) => setDraft(e.target.value)}
                    maxLength={300}
                    aria-label={t('brief.addQ', 'Write a question for your doctor')}
                    placeholder={t('brief.addPlaceholder', 'Type a question')}
                    className="min-h-11 min-w-0 flex-1 rounded-[12px] border-[1.5px] border-line bg-card px-3 text-sub text-ink"
                  />
                  <Button size="md" className="!w-auto" type="submit" disabled={draft.trim().length < 3 || add.isPending}>
                    {t('brief.add', 'Add')}
                  </Button>
                </form>
                {add.isError && <Alert tone="warn">{t('brief.addFailed', 'That question did not save. Please try again.')}</Alert>}
                <div>
                  <TextLink onClick={() => go('K12')}>{t('brief.openQuestions', 'Open my questions')}</TextLink>
                </div>
              </Card>

              <Card as="section" className="flex flex-col gap-1">
                <div className="flex items-baseline justify-between gap-2">
                  <h2 className="text-body font-bold">{t('brief.patterns', 'Patterns the app has learnt')}</h2>
                  <span className="text-sub text-ink2">{t('brief.patternsSub', 'from what it has learnt')}</span>
                </div>
                {facts.length === 0 ? (
                  <p className="py-2 text-body text-ink2">{t('brief.noPatterns', 'Nothing learnt yet. This list fills in as you log.')}</p>
                ) : (
                  <ul className="flex flex-col">
                    {facts.map((f) => (
                      <li key={f.id} className="flex min-h-14 items-start gap-3 border-t border-line py-2 first:border-t-0">
                        <div className="min-w-0 flex-1">
                          <p className="break-words text-sub leading-snug">{f.statement}</p>
                          <p className="break-words text-micro text-ink3">{f.why}</p>
                        </div>
                        <span
                          className={cn(
                            'flex-none rounded-chip px-2 py-0.5 text-micro font-bold whitespace-nowrap',
                            f.confirmed ? 'bg-ok-soft text-ok' : 'bg-brass-soft text-brass',
                          )}
                        >
                          {f.confirmed ? t('brief.confirmed', 'Confirmed') : t('brief.notConfirmed', 'Not confirmed')}
                        </span>
                      </li>
                    ))}
                  </ul>
                )}
                <p className="pb-1 pt-1.5 text-micro text-ink3">
                  {t('brief.patternsNote', 'Patterns compare two things in your logs. They do not prove a cause.')}
                </p>
              </Card>

              <Card as="section" className="flex flex-col gap-2">
                <h2 className="text-body font-bold">{t('brief.worth', 'Worth discussing')}</h2>
                {data.alerts.length === 0 && data.worthDiscussing.length === 0 ? (
                  <p className="text-body text-ink2">{t('brief.worthEmpty', 'Nothing stands out yet. This list fills in as you log.')}</p>
                ) : (
                  <ul className="flex flex-col divide-y divide-line">
                    {data.alerts.map((a, i) => (
                      <li key={`a${i}`} className="flex flex-col gap-1 py-2.5 first:pt-0 last:pb-0">
                        <div>
                          <StatusPill tone={ALERT_TAG[a.priority].tone} icon={ALERT_TAG[a.priority].icon}>
                            {ALERT_WORD[a.priority]}
                          </StatusPill>
                        </div>
                        <p className="break-words text-body font-bold">{a.title}</p>
                        <p className="break-words text-sub text-ink2">{a.detail}</p>
                      </li>
                    ))}
                    {data.worthDiscussing.map((w, i) => (
                      <li key={`w${i}`} className="flex flex-col gap-1 py-2.5 first:pt-0 last:pb-0">
                        <div>
                          <StatusPill tone="neutral">{KIND[w.kind]}</StatusPill>
                        </div>
                        <p className="break-words text-body">{w.text}</p>
                        <p className="break-words text-sub text-ink2">{w.evidence}</p>
                      </li>
                    ))}
                  </ul>
                )}
              </Card>

              <Card as="section" className="flex flex-col gap-2">
                <h2 className="text-body font-bold">{t('brief.nextAppointment', 'Your next appointment')}</h2>
                {nextAppt ? (
                  <div className="flex items-center gap-3">
                    <span className="flex h-11 w-11 flex-none flex-col items-center justify-center rounded-[12px] bg-ok-soft font-bold leading-none text-brand">
                      <span className="text-[10px]">{dayParts(nextAppt.scheduledFor).month}</span>
                      <span className="text-base">{dayParts(nextAppt.scheduledFor).day}</span>
                    </span>
                    <div className="min-w-0">
                      <p className="font-bold leading-tight">{APPOINTMENT_KIND[nextAppt.kind] ?? nextAppt.kind}</p>
                      <p className="text-sub text-ink2">
                        {formatWhen(nextAppt.scheduledFor)}
                        {nextAppt.location ? ` · ${nextAppt.location}` : ''}
                      </p>
                    </div>
                  </div>
                ) : (
                  <p className="text-body text-ink2">{t('brief.noAppointment', 'No appointment is planned yet.')}</p>
                )}
                <div>
                  <TextLink onClick={() => go('K3')}>{t('brief.openCareV2', 'Track my appointments')}</TextLink>
                </div>
              </Card>
            </div>
          </div>
        </>
      )}
    </Screen>
  )
}
