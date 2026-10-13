/**
 * "Your numbers" on Home: four cards of the same size (Glucose, Steps, Calories, Heart and oxygen), two across on a phone, four on a laptop.
 * Each ends with a status line that compares the person with THEIR OWN usual range (wording in status.ts). A card shows a dash
 * for anything the server could not work out; it never shows a 0 for "unknown". The card height is a minimum, so text can wrap at 200%.
 */
import type { ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import type { HomeOverview, Nutrient } from '@/data/types'
import { dateLocale } from '@/lib/locale'
import { cn } from '@/lib/cn'
import { ArrowDown, ArrowUp, Drop, Footprints, Heartbeat, Smiley } from '@/ui/icons'
import { Skeleton } from '@/ui/primitives'
import { barScale, caloriesLine, heartLine, meterFill, rangeLine, sparkRuns, stepsLine, type StatusLine, type StatusTone } from './status'

const TONE_TEXT: Record<StatusTone, string> = { ok: 'text-ok', warn: 'text-warn', info: 'text-info', neutral: 'text-ink2' }

function Status({ line }: { line: StatusLine }) {
  const Icon = line.icon === 'smiley' ? Smiley : line.icon === 'up' ? ArrowUp : line.icon === 'down' ? ArrowDown : null
  return (
    <p className={cn('flex items-start gap-1.5 text-micro font-bold', TONE_TEXT[line.tone])}>
      {Icon && <Icon size={18} weight="bold" aria-hidden className="mt-px flex-none" />}
      <span className="min-w-0 break-words">{line.text}</span>
    </p>
  )
}

/** a flame (the Calories card icon); drawn here because the icon set has no plain flame in the shape of the design */
function Flame({ size = 18 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <path d="M12 3c1 3 5 5 5 10a5 5 0 0 1-10 0c0-2 1-3 2-4 0 2 1 3 2 3 0-3-1-6 1-9Z" />
    </svg>
  )
}

type CardTone = 'info' | 'brand' | 'warn' | 'danger'
const ICON_TONE: Record<CardTone, string> = { info: 'bg-info-soft text-info', brand: 'bg-brand-soft text-brand', warn: 'bg-warn-soft text-warn', danger: 'bg-danger-soft text-danger' }

function Kpi({ label, tone, icon, children, status }: { label: string; tone: CardTone; icon: ReactNode; children: ReactNode; status: StatusLine }) {
  return (
    <li className="flex min-h-[196px] min-w-0 flex-col justify-between gap-3 rounded-card border border-line bg-card p-3.5 shadow-lift">
      <div className="flex items-center gap-2 text-sub text-ink2">
        <span className={cn('flex h-8 w-8 flex-none items-center justify-center rounded-full', ICON_TONE[tone])}>{icon}</span>
        <span className="min-w-0 break-words">{label}</span>
      </div>
      <div className="flex flex-col gap-2">{children}</div>
      <Status line={status} />
    </li>
  )
}

/** the big number with its unit; a missing number is a dash */
function Big({ value, unit, size = 'lg' }: { value: string | null; unit?: string; size?: 'lg' | 'md' }) {
  const { t } = useTranslation()
  return (
    <p className={cn('num break-words font-bold leading-none tracking-tight', size === 'lg' ? 'text-[calc(34px*var(--ts,1))]' : 'text-[calc(30px*var(--ts,1))]')}>
      {value ?? <span aria-label={t('home.kpi.noData', 'No data')}>&ndash;</span>}
      {value != null && unit && <span className="ml-1 text-sub font-normal tracking-normal text-ink3">{unit}</span>}
    </p>
  )
}

function Line({ values, label }: { values: (number | null)[]; label: string }) {
  const runs = sparkRuns(values, 140, 20)
  if (runs.length === 0) return <div className="h-5" />
  return (
    <svg width="100%" height="20" viewBox="0 0 140 20" preserveAspectRatio="none" role="img" aria-label={label} className="text-brand">
      {runs.map((p, i) =>
        p.includes(' ') ? (
          <polyline key={i} points={p} fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" vectorEffect="non-scaling-stroke" />
        ) : (
          <circle key={i} cx={p.split(',')[0]} cy={p.split(',')[1]} r="2" fill="currentColor" />
        ),
      )}
    </svg>
  )
}

function MiniBars({ values, label }: { values: (number | null)[]; label: string }) {
  const h = barScale(values)
  if (h.every((v) => v == null)) return <div className="h-[22px]" />
  return (
    <svg width="100%" height="22" viewBox="0 0 140 22" preserveAspectRatio="none" role="img" aria-label={label}>
      {h.map((v, i) =>
        v == null ? null : <rect key={i} x={2 + i * 20} y={22 - Math.max(2, v * 22)} width={14} height={Math.max(2, v * 22)} rx={Math.min(5, Math.max(1, v * 11))} className={i === h.length - 1 ? 'fill-brand' : 'fill-line'} />,
      )}
    </svg>
  )
}

function Meter({ label, n }: { label: string; n: Nutrient }) {
  const { t } = useTranslation()
  const f = meterFill(n)
  const aria = f.pct == null ? t('home.kpi.noData', 'No data') : t('home.kpi.meterHigh', '{{n}} of {{m}} meals high', { n: n.highMeals ?? 0, m: n.meals })
  return (
    <div className="flex items-center gap-2 text-micro text-ink2">
      <span className="w-12 flex-none">{label}</span>
      <span className="h-1.5 min-w-0 flex-1 overflow-hidden rounded-[3px] bg-well" role="img" aria-label={`${label}: ${aria}`}>
        {f.pct != null && <span className={cn('block h-1.5 rounded-[3px]', f.high ? 'bg-warn' : 'bg-ok')} style={{ width: `${f.pct}%` }} />}
      </span>
      {f.pct == null && <span aria-hidden>&ndash;</span>}
    </div>
  )
}

export function KpiCards({ data }: { data: HomeOverview }) {
  const { t } = useTranslation()
  const { glucose, steps, calories, heart } = data
  /** a metric the person has no data for at all (the server sends null) */
  const none: StatusLine = { tone: 'neutral', icon: null, text: t('home.status.noData', 'No data yet') }
  const fmt = (n: number | null | undefined, digits = 0) => (n == null ? null : n.toLocaleString('en-US', { minimumFractionDigits: digits, maximumFractionDigits: digits }))
  const day = glucose?.day ? new Date(`${glucose.day}T00:00:00`).toLocaleDateString(dateLocale('en-SG'), { day: 'numeric', month: 'short' }) : null

  return (
    <ul className="grid grid-cols-2 gap-3 lg:grid-cols-4 lg:gap-4 [&>li]:min-w-0">
      <Kpi label={t('home.kpi.glucose', 'Glucose')} tone="info" icon={<Drop size={18} aria-hidden />} status={glucose ? rangeLine(t, glucose.status) : none}>
        <Big value={fmt(glucose?.value, 1)} unit="mmol/L" />
        <p className="text-micro text-ink2">{day ? t('home.kpi.glucoseDay', 'Daily average, {{day}}', { day }) : t('home.kpi.glucoseNone', 'Daily average')}</p>
        <Line values={glucose?.spark ?? []} label={t('home.kpi.glucoseSpark', 'Daily average glucose, 7 days')} />
      </Kpi>

      <Kpi label={t('home.kpi.steps', 'Steps')} tone="brand" icon={<Footprints size={18} aria-hidden />} status={steps ? stepsLine(t, steps.status) : none}>
        <Big value={fmt(steps?.avg)} unit={t('home.kpi.aDay', 'a day')} />
        <p className="text-micro text-ink2">{t('home.kpi.stepsAvg', 'Average, last 7 days')}</p>
        <MiniBars values={steps?.spark ?? []} label={t('home.kpi.stepsSpark', 'Steps, 7 days')} />
      </Kpi>

      <Kpi label={t('home.kpi.calories', 'Calories')} tone="warn" icon={<Flame />} status={calories ? caloriesLine(t, calories.status, calories.sugar, calories.salt) : none}>
        <Big value={fmt(calories?.avgKcal)} unit="kcal" />
        <p className="text-micro text-ink2">{t('home.kpi.caloriesAvg', 'A day, last 7 days')}</p>
        {calories && (
          <div className="flex flex-col gap-1.5">
            <Meter label={t('home.kpi.sugar', 'Sugar')} n={calories.sugar} />
            <Meter label={t('home.kpi.salt', 'Salt')} n={calories.salt} />
          </div>
        )}
      </Kpi>

      <Kpi label={t('home.kpi.heart', 'Heart, oxygen')} tone="danger" icon={<Heartbeat size={18} aria-hidden />} status={heart ? heartLine(t, heart.status, heart.spo2Status) : none}>
        <div className="flex items-end gap-3">
          <div className="min-w-0 flex-1">
            <Big value={fmt(heart?.bpm)} size="md" />
            <p className="text-micro text-ink2">bpm</p>
          </div>
          <span className="h-11 w-px flex-none bg-line" aria-hidden />
          <div className="min-w-0 flex-1">
            <Big value={fmt(heart?.spo2)} unit={heart?.spo2 != null ? '%' : undefined} size="md" />
            <p className="text-micro text-ink2">SpO2</p>
          </div>
        </div>
        <p className="text-micro text-ink2">{t('home.kpi.sevenDayAvg', '7-day averages')}</p>
      </Kpi>
    </ul>
  )
}

export function KpiCardsSkeleton() {
  return (
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-4 lg:gap-4">
      {[0, 1, 2, 3].map((i) => (
        <Skeleton key={i} className="h-[196px]" />
      ))}
    </div>
  )
}
