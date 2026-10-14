/**
 * E9 — Meal suggestions: a menu of dishes for one meal, like a food-delivery app. Each dish has a picture (made once by an AI model and kept,
 * so opening this page never makes a new one), the numbers, why it is suggested and its glucose rise: measured on the person for their own meals,
 * an estimate for the rest. Up to three dishes can be added to "Your picks"; "Log when I eat" opens the meal log.
 */
import { useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useMenu, usePickMenuItem } from '@/data/hooks'
import type { Menu, MenuItem, MenuMeal } from '@/data/types'
import { useGo } from '@/app/navigation'
import { appConfig } from '@/config/app'
import { cn } from '@/lib/cn'
import { Header, Screen } from '@/ui/layout'
import { Alert, Button, Card, EmptyState, Skeleton } from '@/ui/primitives'
import { Check, ForkKnife, Plus, X } from '@/ui/icons'

const MEALS: { id: MenuMeal | 'all'; key: string; label: string }[] = [
  { id: 'all', key: 'log.menu.all', label: 'All' },
  { id: 'breakfast', key: 'log.menu.breakfast', label: 'Breakfast' },
  { id: 'lunch', key: 'log.menu.lunch', label: 'Lunch' },
  { id: 'dinner', key: 'log.menu.dinner', label: 'Dinner' },
  { id: 'snack', key: 'log.menu.snack', label: 'Snack' },
]
const FILTERS = [
  { id: 'lowSalt', key: 'log.menu.f.lowSalt', label: 'Lower salt' },
  { id: 'lowCarb', key: 'log.menu.f.lowCarb', label: 'Lower carbs' },
  { id: 'hawker', key: 'log.menu.f.hawker', label: 'Hawker stall' },
  { id: 'home', key: 'log.menu.f.home', label: 'Home cooked' },
]
const MAX_PICKS = 3

/** The meal that fits the time of day in Singapore: the first tab the person sees. */
export const mealNow = (): MenuMeal => {
  const h = Number(new Date().toLocaleString('en-GB', { hour: 'numeric', hour12: false, timeZone: 'Asia/Singapore' }))
  // breakfast to 10, lunch to 3 pm, an afternoon snack to 5, dinner to 10 pm, then a late snack
  return h < 10 ? 'breakfast' : h < 15 ? 'lunch' : h < 17 ? 'snack' : h < 22 ? 'dinner' : 'snack'
}

const fmt = (n: number) => n.toLocaleString('en-US')

function Picture({ item }: { item: MenuItem }) {
  const { t } = useTranslation()
  if (item.image.url) {
    return <img src={`${appConfig.apiBaseUrl}${item.image.url}`} alt="" loading="lazy" className="h-full w-full object-cover" />
  }
  const waiting = item.image.status === 'pending' || item.image.status === 'generating'
  return (
    <div className={cn('flex h-full w-full flex-col items-center justify-center gap-1 bg-well text-ink3', waiting && 'animate-pulse')}>
      <ForkKnife size={28} aria-hidden />
      <span className="text-micro">{waiting ? t('log.menu.pictureSoon', 'Picture on its way') : t('log.menu.noPicture', 'No picture yet')}</span>
    </div>
  )
}

function RiseChip({ item }: { item: MenuItem }) {
  const { t } = useTranslation()
  if (item.riseKind === 'none') return <span className="text-micro text-ink3">{t('log.menu.noRise', 'Glucose rise not known yet')}</span>
  const measured = item.riseKind === 'measured'
  const text = measured ? `+${item.rise!.toFixed(1)}` : `≈ +${item.riseLow!.toFixed(1)} ${t('log.menu.to', 'to')} +${item.riseHigh!.toFixed(1)}`
  return (
    <span
      className={cn(
        'num inline-flex items-center gap-1 whitespace-nowrap rounded-chip px-2.5 py-0.5 text-sub font-bold',
        measured ? 'bg-ok-soft text-ok' : 'bg-brass-soft text-brass',
      )}
    >
      {text}
      <span className="text-micro font-normal">mmol/L</span>
    </span>
  )
}

function DishCard({ item, picked, full, showMeal, onToggle }: { item: MenuItem; picked: boolean; full: boolean; showMeal: boolean; onToggle: () => void }) {
  const { t } = useTranslation()
  const measured = item.riseKind === 'measured'
  const badge = measured ? t('log.menu.measured', 'Measured on you') : t('log.menu.estimate', 'Estimate')
  const disabled = !picked && full
  return (
    <Card className={cn('flex flex-col overflow-hidden !p-0', picked && 'border-brand')}>
      <div className="relative h-[9.5rem] flex-none bg-well">
        <Picture item={item} />
        <span
          className={cn(
            'absolute left-2.5 top-2.5 max-w-[calc(100%-4rem)] truncate rounded-chip px-2.5 py-0.5 text-micro font-bold',
            measured ? 'bg-ok-soft text-ok' : 'bg-brass-soft text-brass',
          )}
        >
          {badge}
        </span>
        <button
          type="button"
          onClick={onToggle}
          disabled={disabled}
          aria-pressed={picked}
          aria-label={
            picked
              ? t('log.menu.removePick', 'Remove {{name}} from your picks', { name: item.name })
              : t('log.menu.addPick', 'Add {{name}} to your picks', { name: item.name })
          }
          className={cn(
            'press absolute bottom-2.5 right-2.5 flex h-10 w-10 items-center justify-center rounded-full shadow-lift disabled:opacity-40',
            picked ? 'bg-brand text-on-brand' : 'bg-card text-brand',
          )}
        >
          {picked ? <Check size={20} weight="bold" aria-hidden /> : <Plus size={20} weight="bold" aria-hidden />}
        </button>
      </div>
      <div className="flex min-w-0 flex-1 flex-col gap-1.5 p-3.5">
        {showMeal && <p className="text-micro font-bold uppercase tracking-wide text-ink3">{t(`log.menu.${item.meal}`, item.meal)}</p>}
        <h3 className="break-words text-body font-bold leading-snug">{item.name}</h3>
        <p className="num text-micro text-ink3">
          {[
            item.serving,
            item.kcal != null ? `${fmt(item.kcal)} kcal` : null,
            item.carbs != null ? t('log.menu.carbs', '{{n}} g carbs', { n: Math.round(item.carbs) }) : null,
            item.sodium != null ? t('log.menu.salt', '{{n}} mg salt', { n: fmt(Math.round(item.sodium)) }) : null,
          ]
            .filter(Boolean)
            .join(' · ')}
        </p>
        <p className="break-words text-sub text-ink2">{item.why}</p>
        <div className="mt-auto pt-1.5">
          <RiseChip item={item} />
        </div>
      </div>
    </Card>
  )
}

function Section({
  title,
  sub,
  items,
  picks,
  showMeal,
  onToggle,
}: {
  title: string
  sub: string
  items: MenuItem[]
  picks: string[]
  showMeal: boolean
  onToggle: (k: string) => void
}) {
  return (
    <section className="flex flex-col gap-2.5">
      <div className="flex flex-wrap items-baseline gap-x-3">
        <h2 className="text-h2 font-bold leading-tight">{title}</h2>
        <p className="text-sub text-ink2">{sub}</p>
      </div>
      <div className="grid grid-cols-1 gap-3.5 sm:grid-cols-2 xl:grid-cols-3">
        {items.map((it) => (
          <DishCard
            key={`${it.meal}:${it.key}`}
            item={it}
            picked={picks.includes(it.key)}
            full={picks.length >= MAX_PICKS}
            showMeal={showMeal}
            onToggle={() => onToggle(it.key)}
          />
        ))}
      </div>
    </section>
  )
}

function Picks({ menu, picks, onToggle }: { menu: Menu; picks: string[]; onToggle: (k: string) => void }) {
  const { t } = useTranslation()
  const go = useGo()
  const pick = usePickMenuItem()
  const all = useMemo(() => menu.sections.flatMap((s) => s.items), [menu])
  const chosen = picks.map((k) => all.find((i) => i.key === k)).filter((i): i is MenuItem => !!i)
  const logIt = () => {
    chosen.forEach((i) => pick.mutate({ meal: i.meal, key: i.key }))
    go('E2')
  }
  return (
    <Card className="flex flex-col gap-2.5">
      <div className="flex items-baseline justify-between">
        <h2 className="text-body font-bold">{t('log.menu.picks', 'Your picks')}</h2>
        <span className="text-sub text-ink3">{t('log.menu.picksCount', '{{n}} of {{max}}', { n: chosen.length, max: MAX_PICKS })}</span>
      </div>
      {chosen.length === 0 && <p className="text-sub text-ink2">{t('log.menu.picksEmpty', 'Tap + on a dish to add it. We remember what was useful.')}</p>}
      {chosen.map((i) => (
        <div key={i.key} className="flex items-center gap-2.5">
          <div className="h-11 w-14 flex-none overflow-hidden rounded-[10px] bg-well">
            {i.image.url && <img src={`${appConfig.apiBaseUrl}${i.image.url}`} alt="" className="h-full w-full object-cover" />}
          </div>
          <div className="min-w-0 flex-1">
            <p className="break-words text-sub font-bold leading-tight">{i.name}</p>
            {i.kcal != null && <p className="num text-micro text-ink3">{fmt(i.kcal)} kcal</p>}
          </div>
          <button
            type="button"
            onClick={() => onToggle(i.key)}
            aria-label={t('log.menu.removePick', 'Remove {{name}} from your picks', { name: i.name })}
            className="press flex h-8 w-8 flex-none items-center justify-center rounded-full border border-line text-ink2"
          >
            <X size={14} aria-hidden />
          </button>
        </div>
      ))}
      {chosen.length > 0 && (
        <Button size="md" onClick={logIt}>
          {t('log.menu.logWhenEat', 'Log when I eat')}
        </Button>
      )}
    </Card>
  )
}

const clockNow = () => new Date().toLocaleTimeString('en-GB', { hour: 'numeric', minute: '2-digit', hour12: true, timeZone: 'Asia/Singapore' }).toLowerCase()
new Date()
  .toLocaleTimeString('en-GB', { hour: 'numeric', minute: '2-digit', hour12: true, timeZone: 'Asia/Singapore' })
  .replace(/\s?(am|pm)/i, (m) => ` ${m.trim().toLowerCase()}`)

/** Changes with the time of day: which meal it is time for, when this person usually has it, and what they usually eat then. */
function RightNow({ nowMeal }: { nowMeal: MenuMeal }) {
  const { t } = useTranslation()
  const { data } = useMenu(nowMeal)
  const name = t(`log.menu.${nowMeal}`, nowMeal).toLowerCase()
  const usual = data?.usual
  return (
    <Card className="flex flex-col gap-2">
      <p className="num text-micro font-bold tracking-wide text-ink3">{clockNow()}</p>
      <h2 className="text-body font-bold">{t('log.menu.timeFor', 'Time for {{meal}}', { meal: name })}</h2>
      {data?.time && (
        <p className="text-sub text-ink2">{t('log.menu.usuallyAt', 'You usually have {{meal}} around {{time}}.', { meal: name, time: data.time })}</p>
      )}
      {usual ? (
        <div className="flex flex-col gap-1.5 border-t border-line pt-2.5">
          <p className="text-sub font-bold">{t('log.menu.usual', 'Your usual {{meal}}', { meal: name })}</p>
          <p className="break-words text-sub text-ink2">{usual.name}</p>
          <div className="flex gap-6">
            {usual.kcal != null && (
              <div>
                <p className="num text-h2 font-bold">{fmt(usual.kcal)}</p>
                <p className="text-micro text-ink3">kcal</p>
              </div>
            )}
            {usual.rise != null && (
              <div>
                <p className="num text-h2 font-bold">+{usual.rise.toFixed(1)}</p>
                <p className="text-micro text-ink3">{t('log.menu.riseUnit', 'mmol/L rise')}</p>
              </div>
            )}
          </div>
        </div>
      ) : (
        <p className="text-sub text-ink3">{t('log.menu.noUsual', 'Log a few {{meal}}s and your usual shows here.', { meal: name })}</p>
      )}
    </Card>
  )
}

/** How the dishes on screen were chosen, with the real counts for what is showing now. */
function HowWeChoose({ menu }: { menu: Menu | undefined }) {
  const { t } = useTranslation()
  const n = (k: MenuItem['section']) => menu?.sections.find((s) => s.key === k)?.items.length ?? 0
  const rows: [string, string, number][] = [
    [t('log.menu.how1b', 'Your own meals first.'), t('log.menu.how1', 'The ones with the smallest rise on your sensor.'), n('own')],
    [t('log.menu.how2b', 'Lighter versions of what you eat,'), t('log.menu.how2', 'from the Singapore food database.'), n('swap')],
    [t('log.menu.how3b', 'General ideas'), t('log.menu.how3', 'only when there is not enough history yet.'), n('general')],
  ]
  return (
    <Card className="flex flex-col gap-2.5">
      <h2 className="text-body font-bold">{t('log.menu.how', 'How we choose')}</h2>
      {rows.map(([b, rest, count], i) => (
        <p key={i} className="flex items-start gap-2.5 text-sub">
          <span className="num flex h-[1.4rem] min-w-[1.4rem] flex-none items-center justify-center rounded-full bg-brand-soft px-1 text-micro font-bold text-brand">
            {count}
          </span>
          <span>
            <b>{b}</b> {rest}
          </span>
        </p>
      ))}
    </Card>
  )
}

export function MealMenu() {
  const { t } = useTranslation()
  const [meal, setMeal] = useState<MenuMeal | 'all'>(mealNow)
  const [filters, setFilters] = useState<string[]>([])
  const [picks, setPicks] = useState<string[]>([])
  const nowMeal = mealNow()
  const { data, isError, isLoading } = useMenu(meal)
  const toggle = (k: string) => setPicks((p) => (p.includes(k) ? p.filter((x) => x !== k) : p.length < MAX_PICKS ? [...p, k] : p))
  const sections = (data?.sections ?? [])
    .map((s) => ({ ...s, items: s.items.filter((i) => filters.every((f) => i.tags.includes(f))) }))
    .filter((s) => s.items.length > 0)
  const SEC: Record<MenuItem['section'], { title: string; sub: string }> = {
    own: { title: t('log.menu.sec.own', 'From your own meals'), sub: t('log.menu.sec.ownSub', 'Measured on you: the smallest rise after eating') },
    swap: { title: t('log.menu.sec.swap', 'Lighter than your usual'), sub: t('log.menu.sec.swapSub', 'The same kind of dish with less carbohydrate or salt') },
    general: { title: t('log.menu.sec.general', 'Worth a try'), sub: t('log.menu.sec.generalSub', 'General ideas for a steady day') },
  }
  return (
    <Screen wide>
      <Header
        title={t('log.menu.title', 'Meal suggestions')}
        back
        backTo="E1"
        sub={t('log.menu.sub', 'Ideas that fit you, picked from your own meals first. It is always your choice.')}
      />
      <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,1fr)_332px] [&>*]:min-w-0">
        <div className="flex flex-col gap-4">
          <div
            className="hide-scroll flex w-full items-center gap-2 overflow-x-auto sm:overflow-visible"
            role="tablist"
            aria-label={t('log.menu.mealLabel', 'Meal')}
          >
            {MEALS.map((m) => {
              const on = m.id === meal
              return (
                <button
                  key={m.id}
                  type="button"
                  role="tab"
                  aria-selected={on}
                  onClick={() => {
                    setMeal(m.id)
                    setPicks([])
                  }}
                  className={cn(
                    'press flex min-h-[2.9rem] min-w-[5.6rem] flex-none flex-col items-center justify-center rounded-[14px] border-[1.5px] px-3 text-center leading-tight sm:min-w-0 sm:flex-1 sm:basis-0',
                    on ? 'border-brand bg-brand text-on-brand' : 'border-line bg-card text-ink',
                  )}
                >
                  <span className="text-btn-sm font-bold">{t(m.key, m.label)}</span>
                  {on && data?.time && <span className="num text-micro opacity-80">{data.time}</span>}
                </button>
              )
            })}
          </div>
          <div className="flex flex-wrap items-center gap-2" role="group" aria-label={t('log.menu.filterLabel', 'Show only')}>
            {FILTERS.map((f) => {
              const on = filters.includes(f.id)
              return (
                <button
                  key={f.id}
                  type="button"
                  aria-pressed={on}
                  onClick={() => setFilters((x) => (on ? x.filter((y) => y !== f.id) : [...x, f.id]))}
                  className={cn(
                    'press min-h-9 whitespace-nowrap rounded-chip border-[1.5px] px-3.5 text-sub',
                    on ? 'border-brand bg-brand font-bold text-on-brand' : 'border-line bg-card text-ink',
                  )}
                >
                  {t(f.key, f.label)}
                </button>
              )
            })}
            <span className="ml-auto hidden items-center gap-1.5 text-micro text-ink2 sm:flex">
              <span className="h-2 w-2 rounded-full bg-ok" aria-hidden />
              {t('log.menu.legendMeasured', 'Measured on you')}
              <span className="ml-2 h-2 w-2 rounded-full bg-brass" aria-hidden />
              {t('log.menu.legendEstimate', 'Estimate')}
            </span>
          </div>
          {isError && <Alert tone="warn">{t('log.menu.loadError', 'We could not load the suggestions just now.')}</Alert>}
          {isLoading && <Skeleton className="h-72" />}
          {data && sections.length === 0 && (
            <EmptyState icon={ForkKnife}>
              {filters.length
                ? t('log.menu.noMatch', 'No dish matches these filters. Try turning one off.')
                : t('log.menu.empty', 'No ideas yet. Log a few meals and they will appear here.')}
            </EmptyState>
          )}
          {sections.map((s) => (
            <Section key={s.key} title={SEC[s.key].title} sub={SEC[s.key].sub} items={s.items} picks={picks} showMeal={meal === 'all'} onToggle={toggle} />
          ))}
          {data && sections.length > 0 && (
            <p className="text-center text-micro text-ink3">
              {t(
                'log.menu.aiNote',
                'Pictures are made by AI to show the dish and are only a guide. Rises marked Measured come from your sensor. These are ideas, not instructions.',
              )}
            </p>
          )}
        </div>
        <aside className="flex flex-col gap-4 lg:sticky lg:top-2 lg:max-h-[calc(100dvh-1rem)] lg:overflow-y-auto">
          {data && <Picks menu={data} picks={picks} onToggle={toggle} />}
          <RightNow nowMeal={nowMeal} />
          <HowWeChoose menu={data} />
        </aside>
      </div>
    </Screen>
  )
}
