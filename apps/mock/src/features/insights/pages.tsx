import { useDay, useInsights } from '@/data/hooks'
import { useGo } from '@/app/navigation'
import { useUi } from '@/state/store'
import { appConfig } from '@/config/app'
import { AdherenceTimeline, FoodBars, IntensityBars, MoodStress, Ring, TirBar, WeekGridView } from '@/charts/small'
import { TrendChart } from '@/charts/TrendChart'
import { WearableTrends } from '@/charts/WearableTrends'
import { clock, hm, signed, thousands } from '@/lib/format'
import { Header, Screen, Reveal } from '@/ui/layout'
import { Alert, Button, Card, EstimateBadge, SectionTitle, Skeleton, StatusPill, TextLink, UnverifiedTag } from '@/ui/primitives'
import { CaretRight, ChartLineUp, PersonSimpleWalk, Pill } from '@/ui/icons'
import { InsightsFrame, Summary, WhyLink, usePeriod } from './InsightsFrame'
import { useNavigate } from 'react-router-dom'
import { href } from '@/app/routeIds'

function Loading() {
  return (
    <InsightsFrame>
      <Skeleton className="h-48" />
      <Skeleton className="h-40" />
    </InsightsFrame>
  )
}

/* ----------------------------------- C1 Overview ----------------------------------- */
export function Overview() {
  const [period] = usePeriod()
  const { data } = useInsights(period)
  const go = useGo()
  if (!data) return <Loading />
  return (
    <InsightsFrame period={false}>
      <Reveal id="ov-week">
        <Card className="flex flex-col gap-3">
          <SectionTitle>Your week</SectionTitle>
          <Summary>Tap any day to see it hour by hour.</Summary>
          <WeekGridView grid={data.weekGrid} onDay={(date) => go('D1', { params: { date } })} />
          <WhyLink />
        </Card>
      </Reveal>
      <Reveal id="ov-changed" i={1}>
        <section className="flex flex-col gap-1">
          <SectionTitle>What changed</SectionTitle>
          <ul className="divide-y divide-line">
            {data.whatChanged.map((w) => (
              <li key={w.id}>
                <button type="button" onClick={() => go(w.to)} className="press flex w-full items-center gap-3 py-3.5 text-left">
                  <span className="flex-1 text-body">{w.text}</span>
                  <CaretRight size={20} className="text-ink3" aria-hidden />
                </button>
              </li>
            ))}
          </ul>
        </section>
      </Reveal>
      <TextLink onClick={() => go('D1', { params: { date: appConfig.demo.today } })} className="self-start" icon={ChartLineUp}>
        See your day
      </TextLink>
    </InsightsFrame>
  )
}

/* ------------------------------------ C2 Glucose ------------------------------------ */
export function GlucoseInsights() {
  const [period] = usePeriod()
  const { data } = useInsights(period)
  const go = useGo()
  if (!data) return <Loading />
  return (
    <InsightsFrame>
      <Alert tone="warn" title="Higher than your usual for about 3 weeks">
        Worth mentioning to your doctor.
      </Alert>
      <Card className="flex flex-col gap-2">
        <SectionTitle>Fasting glucose</SectionTitle>
        <Summary>{data.fasting.summary}</Summary>
        <TrendChart points={data.fasting.points} baseline={data.fasting.baseline} label="Fasting glucose in mmol per litre with your usual band" format={(v) => v.toFixed(1)} drawKey={`fast-${period}`} />
        <p className="text-sub text-ink3">The shaded band is your own usual (6.6 to 7.2 mmol/L), worked out from your last 28 days.</p>
        <WhyLink topic="glucose" />
      </Card>
      <Card className="flex flex-col gap-3">
        <SectionTitle>Time in range</SectionTitle>
        <Summary>
          Last 24 hours: <b>{data.timeInRange.last24h}%</b>. This week: <b>{data.timeInRange.week}%</b>. Your range is 3.9 to 10.0 mmol/L.
        </Summary>
        <TirBar segments={data.timeInRange.segments} />
      </Card>
      <Card className="flex flex-col gap-3">
        <SectionTitle>With your watch</SectionTitle>
        <Summary>{data.wearables.restingHr.summary}</Summary>
        <WearableTrends fasting={data.fasting} restingHr={data.wearables.restingHr} spo2={data.wearables.spo2} keyPrefix={`ins-${period}`} />
        <p className="text-sub text-ink3">Shown side by side so patterns are easy to see. Associated with, not proven. Heart rate and blood oxygen are simulated in this demo.</p>
        <WhyLink topic="pattern" />
      </Card>
      <Card onClick={() => go('C8')} className="flex items-center justify-between gap-3">
        <span>
          <span className="block text-body font-bold">Glucose sensor sprint</span>
          <span className="block text-sub text-ink2">
            Day {data.sprint.day} of {data.sprint.of}
          </span>
        </span>
        <CaretRight size={22} className="text-ink3" aria-hidden />
      </Card>
    </InsightsFrame>
  )
}

/* ------------------------------------- C3 Food ------------------------------------- */
export function FoodInsights() {
  const [period] = usePeriod()
  const { data } = useInsights(period)
  const today = useDay(appConfig.demo.today)
  const yesterday = useDay('2026-09-30')
  const go = useGo()
  if (!data) return <Loading />
  const meals = [...(today.data?.meals ?? []).map((m) => ({ ...m, date: '2026-10-01', dayLabel: 'Today' })), ...(yesterday.data?.meals ?? []).map((m) => ({ ...m, date: '2026-09-30', dayLabel: 'Yesterday' }))].sort((a, b) => (a.date === b.date ? b.t - a.t : a.date < b.date ? 1 : -1))
  return (
    <InsightsFrame>
      <Card className="flex flex-col gap-3">
        <SectionTitle>Recent meals</SectionTitle>
        <ul className="divide-y divide-line">
          {meals.slice(0, 5).map((m) => (
            <li key={m.id}>
              <button type="button" onClick={() => go('D1', { params: { date: m.date } })} className="press flex w-full flex-col gap-1.5 py-3 text-left">
                <span className="flex flex-wrap items-baseline justify-between gap-x-3">
                  <span className="text-body font-bold leading-snug">{m.name}</span>
                  <span className="flex-none text-sub text-ink3">
                    {m.dayLabel}, {clock(m.t)}
                  </span>
                </span>
                <span className="flex flex-wrap items-center gap-2 text-sub text-ink2">
                  {m.carbsG} g carbs
                  {m.estimated && <EstimateBadge />}
                  {m.flags.includes('high_salt') && <StatusPill tone="warn">High salt</StatusPill>}
                  {m.flags.includes('high_sugar') && <StatusPill tone="warn">High sugar</StatusPill>}
                </span>
              </button>
            </li>
          ))}
        </ul>
      </Card>
      <Card className="flex flex-col gap-3">
        <SectionTitle>Your meal responses</SectionTitle>
        <Summary>From gentlest to spikiest, measured by your glucose sensor. White-rice lunches raise your glucose the most.</Summary>
        <FoodBars foods={data.foods} />
        <p className="text-sub text-ink3">The rise is measured. Nutrients in each meal are estimates until you confirm them.</p>
        <WhyLink />
      </Card>
    </InsightsFrame>
  )
}

/* ----------------------------------- C4 Activity ----------------------------------- */
export function ActivityInsights() {
  const [period] = usePeriod()
  const { data } = useInsights(period)
  const typical = useDay('2026-09-30')
  const go = useGo()
  const toast = useUi((s) => s.showToast)
  if (!data) return <Loading />
  const a = data.activity
  return (
    <InsightsFrame>
      <Reveal id="act-rings">
        <Card className="flex flex-col gap-4">
          <SectionTitle>This week</SectionTitle>
          <div className="grid grid-cols-2 gap-3 [[data-ts='2']_&]:grid-cols-1">
            <Ring value={a.moderateMin} goal={a.moderateGoal} label="Moderate or vigorous minutes" unit="minutes" caption="Moderate or vigorous minutes" />
            <Ring value={a.strength} goal={a.strengthGoal} label="Strength sessions" unit="sessions" caption="Strength sessions" />
          </div>
          <p className="text-sub text-ink3">
            Goal: {appConfig.goals.moderateMinutes} minutes and {appConfig.goals.strengthSessions} strength sessions. {appConfig.goals.source}
          </p>
          <TextLink onClick={() => toast('Goals are set with your doctor. We will add editing once they confirm.')} className="self-start">
            Edit goal
          </TextLink>
        </Card>
      </Reveal>
      <Card className="flex flex-col gap-3">
        <SectionTitle>Last 4 weeks</SectionTitle>
        <Summary>Moderate minutes fell from 140 to 70 a week.</Summary>
        <IntensityBars weeks={a.weeks} />
        <WhyLink />
      </Card>
      <Card className="flex flex-col gap-3">
        <SectionTitle>Mix</SectionTitle>
        <ul className="flex flex-col gap-2.5">
          {a.mix.map((m) => (
            <li key={m.label} className="flex items-center gap-3">
              <span className="w-28 flex-none text-sub">{m.label}</span>
              <span className="h-3 flex-1 overflow-hidden rounded-full bg-well" aria-hidden>
                <span className="block h-full rounded-full bg-brand" style={{ width: `${(m.count / 10) * 100}%` }} />
              </span>
              <span className="num w-6 text-right text-body">{m.count}</span>
            </li>
          ))}
        </ul>
        <p className="text-sub text-ink3">Sessions in the last 8 weeks.</p>
      </Card>
      <Card className="flex flex-col gap-1">
        <SectionTitle>Workouts</SectionTitle>
        <ul className="divide-y divide-line">
          {a.workouts.map((w) => (
            <li key={w.id} className="flex items-center gap-3 py-3">
              <span className="flex h-11 w-11 flex-none items-center justify-center rounded-full bg-brand-soft text-brand">
                <PersonSimpleWalk size={22} aria-hidden />
              </span>
              <span className="min-w-0 flex-1">
                <span className="block text-body font-bold">{w.label}</span>
                <span className="block text-sub text-ink2">
                  {w.date}, {w.minutes} min, {w.intensity}
                </span>
              </span>
              {w.glucoseChange2h != null && (
                <span className="text-right">
                  <span className="num block text-h2">{signed(w.glucoseChange2h)}</span>
                  <span className="block text-sub text-ink3">in 2 h</span>
                </span>
              )}
            </li>
          ))}
        </ul>
        <p className="text-sub text-ink3">Glucose change is shown where you wore the sensor.</p>
      </Card>
      {typical.data && (
        <Card className="flex flex-col gap-3">
          <SectionTitle>Timing</SectionTitle>
          <TimingStrip meals={typical.data.meals.map((m) => m.t)} walks={typical.data.workouts.map((w) => w.t)} />
          <Summary>You walk after dinner on about 3 evenings a week.</Summary>
        </Card>
      )}
      <Card className="flex flex-col gap-3">
        <SectionTitle>Exercise and glucose</SectionTitle>
        <Summary>{data.patterns[0]!.text}</Summary>
        <UnverifiedTag />
        <p className="text-sub text-ink2">Worth mentioning to your doctor.</p>
        <WhyLink topic="pattern" />
      </Card>
      <Card className="flex flex-col gap-2">
        <SectionTitle>Steps</SectionTitle>
        <Summary>
          Your 7-day average is <b>{thousands(a.stepsAvg7)}</b> steps. Your usual is about {thousands(a.stepsBaseline)}.
        </Summary>
        <TrendChart points={data.steps.points} baseline={data.steps.baseline} label="Steps each day with your usual band" format={(v) => thousands(Math.round(v / 100) * 100)} drawKey={`steps-${period}`} color="var(--c-s2)" />
      </Card>
      <Card tone="soft" className="flex flex-col gap-3">
        <p className="text-h2 font-bold">Plan this week's next session</p>
        <Button onClick={() => go('F1')}>Log a workout</Button>
        <Button variant="secondary" onClick={() => toast('Reminder set for Friday at 7:30 pm')}>
          Remind me on Friday at 7:30 pm
        </Button>
      </Card>
    </InsightsFrame>
  )
}

function TimingStrip({ meals, walks }: { meals: number[]; walks: number[] }) {
  const pos = (t: number) => `${(t / 1440) * 100}%`
  return (
    <div>
      <div className="relative h-14 rounded-field bg-well" role="img" aria-label="When you eat and when you walk in a typical day">
        {meals.map((t) => (
          <span key={`m${t}`} className="absolute top-2 h-4 w-1.5 -translate-x-1/2 rounded-full bg-brass" style={{ left: pos(t) }} />
        ))}
        {walks.map((t) => (
          <span key={`w${t}`} className="absolute bottom-2 h-4 w-6 -translate-x-1/4 rounded-full bg-brand" style={{ left: pos(t) }} />
        ))}
      </div>
      <div className="mt-1 flex justify-between text-sub text-ink3">
        <span>12 am</span>
        <span>6 am</span>
        <span>12 pm</span>
        <span>6 pm</span>
      </div>
      <ul className="mt-2 flex gap-5 text-sub text-ink2">
        <li className="flex items-center gap-1.5"><span className="h-3 w-1.5 rounded-full bg-brass" aria-hidden />Meals</li>
        <li className="flex items-center gap-1.5"><span className="h-3 w-5 rounded-full bg-brand" aria-hidden />Walks</li>
      </ul>
    </div>
  )
}

/* ------------------------------- C5 Sleep and stress ------------------------------- */
export function SleepInsights() {
  const [period] = usePeriod()
  const { data } = useInsights(period)
  if (!data) return <Loading />
  const last7 = data.sleep.points.slice(-7).map((p) => p.v ?? 0)
  const under6 = last7.filter((v) => v < 360).length
  return (
    <InsightsFrame>
      <Card className="flex flex-col gap-2">
        <SectionTitle>Sleep</SectionTitle>
        <Summary>{data.sleep.summary}</Summary>
        <TrendChart points={data.sleep.points} baseline={data.sleep.baseline} label="Sleep in hours with your usual band" format={(v) => `${(v / 60).toFixed(1)} h`} drawKey={`sleep-${period}`} color="var(--c-s3)" />
        <p className="text-sub text-ink3">
          Last night {hm(350)}. Nights under 6 hours this week: {under6} of 7.
        </p>
        <WhyLink />
      </Card>
      <Card className="flex flex-col gap-2">
        <SectionTitle>Mood and stress</SectionTitle>
        <Summary>Your check-ins over the last 2 weeks. Stress has been 4 of 5 on most evenings lately.</Summary>
        <MoodStress data={data.mood} />
      </Card>
      <Card className="flex flex-col gap-3">
        <SectionTitle>Sleep and fasting glucose</SectionTitle>
        <Summary>{data.patterns[1]!.text}</Summary>
        <UnverifiedTag />
        <p className="text-sub text-ink2">Worth mentioning to your doctor.</p>
        <WhyLink topic="pattern" />
      </Card>
    </InsightsFrame>
  )
}

/* ------------------------------------ C6 Medication ------------------------------------ */
export function MedicationInsights() {
  const [period] = usePeriod()
  const { data } = useInsights(period)
  const navigate = useNavigate()
  if (!data) return <Loading />
  const m = data.medication
  return (
    <InsightsFrame period={false}>
      <Card className="flex flex-col gap-3">
        <SectionTitle>This week</SectionTitle>
        <div className="flex items-baseline gap-3">
          <span className="num text-display">{m.adherencePct}%</span>
          <span className="text-body text-ink2">
            {m.taken} of {m.scheduled} doses taken
          </span>
        </div>
        <AdherenceTimeline days={m.days} rows={m.timeline} fasting={m.fastingOverlay} />
        <WhyLink />
      </Card>
      <Card className="flex flex-col gap-3">
        <SectionTitle>Reasons given</SectionTitle>
        <ul className="flex flex-col gap-2">
          {m.reasons.map((r) => (
            <li key={r.reason} className="flex items-center justify-between gap-3 text-body">
              {r.reason}
              <StatusPill tone="neutral" bare>
                {r.count} {r.count === 1 ? 'time' : 'times'}
              </StatusPill>
            </li>
          ))}
        </ul>
        <p className="text-sub text-ink3">A missed dose is information for your doctor, not a failure. Two more are not confirmed yet.</p>
      </Card>
      <Button variant="secondary" icon={Pill} onClick={() => navigate(href('H1'))}>
        Open my medicines
      </Button>
    </InsightsFrame>
  )
}

/* ------------------------------------ C8 Sprint ------------------------------------ */
export function SprintPage() {
  const { data } = useInsights(30)
  const go = useGo()
  const toast = useUi((s) => s.showToast)
  if (!data)
    return (
      <Screen>
        <Header title="Glucose sensor sprint" back backTo="C2" />
        <Skeleton className="h-48" />
      </Screen>
    )
  const s = data.sprint
  return (
    <Screen>
      <Header title="Glucose sensor sprint" back backTo="C2" sub="A short stretch of continuous monitoring, so we can see how your own body reacts to your own food." />
      <Card className="flex flex-col gap-3">
        <div className="flex items-baseline justify-between">
          <span className="num text-xl">
            Day {s.day} of {s.of}
          </span>
          <StatusPill tone="ok">Running</StatusPill>
        </div>
        <div className="h-2.5 w-full overflow-hidden rounded-full bg-well" aria-hidden>
          <div className="h-full rounded-full bg-brand" style={{ width: `${(s.day / s.of) * 100}%` }} />
        </div>
        <p className="text-sub text-ink2">{s.of - s.day} days to go. Wear the sensor as normal.</p>
      </Card>
      <Card className="flex flex-col gap-3">
        <SectionTitle>So far</SectionTitle>
        <dl className="grid grid-cols-3 gap-3 text-center [[data-ts='2']_&]:grid-cols-1">
          {[['Average', `${s.avgMmol}`, 'mmol/L'], ['Estimated HbA1c', `${s.gmi}`, '%'], ['Variability', `${s.cv}`, '%']].map(([k, v, u]) => (
            <div key={k}>
              <dt className="text-sub text-ink2">{k}</dt>
              <dd className="num text-xl">
                {v}
                <span className="ml-0.5 text-sub text-ink3">{u}</span>
              </dd>
            </div>
          ))}
        </dl>
        <p className="text-sub text-ink3">Calculated from your sensor readings. It is not a lab result.</p>
      </Card>
      <Card className="flex flex-col gap-3">
        <SectionTitle>Time in range</SectionTitle>
        <TirBar segments={data.timeInRange.segments} />
      </Card>
      <Button variant="secondary" onClick={() => go('C3')}>
        Your gentlest and spikiest foods
      </Button>
      <Card tone="soft" className="flex flex-col gap-2">
        <p className="text-body">
          What we learn in a sprint keeps working after the sensor comes off. You can start another before a review or after a medicine change.
        </p>
        <div className="flex flex-wrap gap-2">
          <Button variant="secondary" size="md" onClick={() => toast('Sprint ended. Your summary is ready.')}>
            End sprint early
          </Button>
          <Button variant="secondary" size="md" onClick={() => toast('A new sprint can start once this one ends.')}>
            Start a new sprint
          </Button>
        </div>
      </Card>
    </Screen>
  )
}
