import { useMemo, type ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { useDietDays, useLunchIdeas, useRecent } from '@/data/hooks'
import type { Macros, RecentEntry } from '@/data/types'
import { useGo } from '@/app/navigation'
import { sgToday } from '@/features/me/progress/calendarMath'
import { Skeleton, TextLink } from '@/ui/primitives'
import { addDays, fmtAmount, fmtShown, mean } from './mealMath'
import type { ManualPrefill } from './MealManualForm'

/** The boxes of the manual form filled in from a recent meal. A value that was not known stays blank. */
export function prefillFrom(r: RecentEntry): ManualPrefill {
  const m = r.meal
  return {
    name: m?.name ?? r.title,
    kcal: fmtAmount(m?.kcal ?? null),
    carbs: fmtAmount(m?.carbsG ?? null),
    protein: fmtAmount(m?.proteinG ?? null),
    fat: fmtAmount(m?.fatG ?? null),
    salt: fmtAmount(m?.sodiumMg ?? null),
  }
}

/** A card of the right-hand column. Its own surface, so the colour is set once here and never fights a card background. */
function SideCard({ children, tint = false }: { children: ReactNode; tint?: boolean }) {
  return (
    <div
      className={
        tint
          ? 'flex flex-col gap-2 rounded-card border border-transparent bg-brand-soft p-4'
          : 'flex flex-col gap-2 rounded-card border border-line bg-card p-4'
      }
    >
      {children}
    </div>
  )
}

/**
 * The right-hand column on the photo step: meals to log again in one tap (the recent list, filled into the manual form), and
 * today so far against the usual day (the average of the last week's days that had meals, not counting today).
 */
export function PhotoSide({ onLogAgain }: { onLogAgain: (p: ManualPrefill) => void }) {
  const { t } = useTranslation()
  const recent = useRecent()
  const today = useMemo(() => sgToday(), [])
  const diet = useDietDays(addDays(today, -7), today)
  const meals = (recent.data ?? []).filter((r) => r.kind === 'meal' && r.meal).slice(0, 3)

  const todayDay = diet.data?.days.find((d) => d.date === today)
  const prior = (diet.data?.days ?? []).filter((d) => d.date !== today && d.meals > 0)
  const lines = [
    { label: t('log.meal.calories', 'Calories'), unit: 'kcal', now: todayDay?.totals.kcal ?? null, usual: mean(prior.map((d) => d.totals.kcal)) },
    { label: t('log.meal.carbs', 'Carbs'), unit: 'g', now: todayDay?.totals.carbsG ?? null, usual: mean(prior.map((d) => d.totals.carbsG)) },
    { label: t('log.meal.salt', 'Salt'), unit: 'mg', now: todayDay?.totals.sodiumMg ?? null, usual: mean(prior.map((d) => d.totals.sodiumMg)) },
  ]

  return (
    <>
      <SideCard>
        <p className="text-body font-bold text-ink">{t('log.meal.again', 'Eat this again?')}</p>
        <p className="text-sub text-ink2">{t('log.meal.againSub', 'Log a recent meal in one tap.')}</p>
        {recent.isLoading ? (
          <Skeleton className="h-24" />
        ) : recent.isError ? (
          <p className="text-sub text-ink2">{t('log.meal.recentError', 'Recent meals are not available right now.')}</p>
        ) : meals.length === 0 ? (
          <p className="text-sub text-ink2">{t('log.meal.noRecent', 'Meals you log will appear here.')}</p>
        ) : (
          <ul className="flex flex-col">
            {meals.map((r) => (
              <li key={r.id} className="flex items-center gap-3 border-t border-line py-3">
                <div className="min-w-0 flex-1">
                  <p className="break-words text-sub font-bold text-ink">{r.meal?.name ?? r.title}</p>
                  <p className="text-micro text-ink3">
                    {r.when}
                    {' · '}
                    <span className="num whitespace-nowrap">
                      {r.meal?.kcal != null ? t('log.meal.kcalShort', '{{n}} kcal', { n: fmtShown(r.meal.kcal) }) : t('log.meal.notJudged', 'Not judged')}
                    </span>
                  </p>
                </div>
                <div className="w-28 flex-none">
                  <button
                    type="button"
                    onClick={() => onLogAgain(prefillFrom(r))}
                    className="press flex min-h-12 w-full items-center justify-center rounded-[14px] border-2 border-brand bg-card px-3 text-btn-sm font-bold text-brand hover:bg-brand-soft"
                  >
                    {t('log.meal.logAgain', 'Log again')}
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </SideCard>

      <SideCard>
        <p className="text-body font-bold text-ink">{t('log.meal.today', 'Today so far')}</p>
        <p className="text-sub text-ink2">{t('log.meal.todaySub', 'Compared with your usual day')}</p>
        {diet.isLoading ? (
          <Skeleton className="h-28" />
        ) : diet.isError ? (
          <p className="text-sub text-ink2">{t('log.meal.todayError', "Today's numbers are not available right now.")}</p>
        ) : !todayDay || todayDay.meals === 0 ? (
          <p className="text-sub text-ink2">{t('log.meal.nothingToday', 'Nothing logged yet today.')}</p>
        ) : (
          <div className="flex flex-col gap-3 pt-1">
            {lines.map((l) => (
              <UsageBar key={l.unit} label={l.label} unit={l.unit} now={l.now} usual={l.usual} />
            ))}
            <p className="text-micro text-ink3">{t('log.meal.todayLine', 'The line is your usual for the whole day.')}</p>
          </div>
        )}
      </SideCard>
    </>
  )
}

/** One total for today: the amount so far, a bar, and a line at the usual amount for the whole day (no line when the usual is not known). */
function UsageBar({ label, unit, now, usual }: { label: string; unit: string; now: number | null; usual: number | null }) {
  const { t } = useTranslation()
  const top = Math.max(now ?? 0, usual ?? 0)
  const width = now != null && top > 0 ? (now / top) * 100 : 0
  const line = usual != null && top > 0 ? (usual / top) * 100 : null
  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-baseline justify-between gap-3 text-sub">
        <span className="min-w-0 break-words text-ink2">{label}</span>
        <span className="num whitespace-nowrap font-bold text-ink">{now == null ? t('log.meal.notJudged', 'Not judged') : `${fmtShown(now)} ${unit}`}</span>
      </div>
      <div className="relative h-2 rounded-chip bg-line">
        <div className="absolute inset-y-0 left-0 rounded-chip bg-brand" style={{ width: `${width}%` }} />
        {line != null && <div className="absolute -bottom-0.5 -top-0.5 w-0.5 bg-ink" style={{ left: `calc(${line}% - 1px)` }} />}
      </div>
    </div>
  )
}

/**
 * The right-hand column on the check-the-numbers step: this meal against the usual meal (the average of the meals of the last
 * week, not counting today), and a lighter idea from the lunch ideas.
 */
export function ResultSide({ shown }: { shown: Macros }) {
  const { t } = useTranslation()
  const go = useGo()
  const today = useMemo(() => sgToday(), [])
  const diet = useDietDays(addDays(today, -7), today)
  const ideas = useLunchIdeas()
  const past = (diet.data?.days ?? []).filter((d) => d.date !== today).flatMap((d) => d.mealList)
  const usual = { kcal: mean(past.map((m) => m.kcal)), carbs: mean(past.map((m) => m.carbsG)), salt: mean(past.map((m) => m.sodiumMg)) }
  const pick = ideas.data?.options.find((o) => o.source === 'swap') ?? ideas.data?.options[0]
  const rows = [
    { label: t('log.meal.calories', 'Calories'), now: shown.kcal, usual: usual.kcal, unit: 'kcal' },
    { label: t('log.meal.carbs', 'Carbs'), now: shown.carbsG, usual: usual.carbs, unit: 'g' },
    { label: t('log.meal.salt', 'Salt'), now: shown.sodiumMg, usual: usual.salt, unit: 'mg' },
  ]
  const noneYet = !diet.isLoading && !diet.isError && rows.every((r) => r.usual == null)

  return (
    <>
      <SideCard>
        <p className="text-body font-bold text-ink">{t('log.meal.against', 'Against your usual meal')}</p>
        {rows.map((r) => (
          <div key={r.unit} className="flex items-baseline justify-between gap-3 text-sub">
            <span className="min-w-0 break-words text-ink2">{r.label}</span>
            <span className="num whitespace-nowrap">
              <b className="text-ink">{r.now == null ? t('log.meal.notJudged', 'Not judged') : `${fmtShown(r.now)} ${r.unit}`}</b>
              {r.usual != null && (
                <span className="text-micro text-ink2"> {t('log.meal.vsUnit', 'vs {{n}} {{unit}}', { n: fmtShown(r.usual), unit: r.unit })}</span>
              )}
            </span>
          </div>
        ))}
        {noneYet && <p className="text-micro text-ink2">{t('log.meal.noUsual', 'Not enough past meals yet to compare.')}</p>}
        <p className="text-micro text-ink2">{t('log.meal.sensorNote', 'The glucose rise after eating comes from your sensor in about 2 hours.')}</p>
      </SideCard>

      <SideCard tint>
        <p className="text-body font-bold text-ink">{t('log.meal.lighter', 'A lighter idea for next time')}</p>
        {pick ? (
          <>
            <p className="break-words text-body font-bold text-ink">{pick.name}</p>
            <p className="break-words text-sub text-ink2">{pick.why}</p>
          </>
        ) : (
          <p className="text-sub text-ink2">{t('log.meal.noIdea', 'Ideas appear once a few meals are logged.')}</p>
        )}
        <TextLink onClick={() => go('E8')} className="self-start">
          {t('log.meal.seeMenu', 'See more in the menu')}
        </TextLink>
      </SideCard>
    </>
  )
}
