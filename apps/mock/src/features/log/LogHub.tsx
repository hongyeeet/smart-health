import { useRecent } from '@/data/hooks'
import { useGo } from '@/app/navigation'
import type { RecentEntry } from '@/data/types'
import type { RouteId } from '@/app/routeIds'
import { Header, Screen, Reveal } from '@/ui/layout'
import { Card, SectionTitle, Skeleton } from '@/ui/primitives'
import { Barbell, CaretRight, Drop, ForkKnife, PersonSimpleWalk, Smiley, Thermometer, type IconType } from '@/ui/icons'

const tiles: { id: RouteId; title: string; sub: string; icon: IconType; wide?: boolean }[] = [
  { id: 'F1', title: 'Workout', sub: 'Walk, strength, yoga', icon: PersonSimpleWalk },
  { id: 'E2', title: 'Meal', sub: 'Photo or words', icon: ForkKnife },
  { id: 'E3', title: 'Glucose', sub: 'A reading', icon: Drop },
  { id: 'E4', title: 'Symptom', sub: 'How you feel', icon: Thermometer },
  { id: 'E5', title: 'Mood and sleep check-in', sub: 'Thirty seconds', icon: Smiley, wide: true },
]

const kindIcon: Record<RecentEntry['kind'], IconType> = { meal: ForkKnife, glucose: Drop, workout: Barbell, symptom: Thermometer, checkin: Smiley }

export function LogHub() {
  const go = useGo()
  const { data } = useRecent()
  return (
    <Screen tabs>
      <Header title="Log" sub="Add what happened. It all lands on one timeline." />
      <Reveal id="log-tiles">
        <div className="grid grid-cols-2 gap-3 [[data-ts='2']_&]:grid-cols-1">
          {tiles.map((t) => (
            <Card key={t.id} onClick={() => go(t.id)} className={`flex min-h-[124px] flex-col justify-between ${t.wide ? 'col-span-2 [[data-ts="2"]_&]:col-span-1' : ''}`}>
              <span className="flex h-11 w-11 items-center justify-center rounded-full bg-brand-soft text-brand">
                <t.icon size={24} aria-hidden />
              </span>
              <span>
                <span className="block text-body font-bold">{t.title}</span>
                <span className="block text-sub text-ink2">{t.sub}</span>
              </span>
            </Card>
          ))}
        </div>
      </Reveal>
      <section className="flex flex-col gap-1">
        <SectionTitle>Recent entries</SectionTitle>
        {!data ? (
          <Skeleton className="h-40" />
        ) : (
          <ul className="divide-y divide-line">
            {data.map((e) => {
              const Icon = kindIcon[e.kind]
              return (
                <li key={e.id}>
                  <button type="button" onClick={() => go('E7', { sheet: { entry: e } })} className="press flex w-full items-center gap-3 py-3 text-left">
                    <span className="flex h-11 w-11 flex-none items-center justify-center rounded-full bg-well text-ink2">
                      <Icon size={22} aria-hidden />
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="block text-body font-bold leading-snug">{e.title}</span>
                      <span className="block text-sub text-ink2">{e.detail}</span>
                    </span>
                    <span className="flex-none text-sub text-ink3">{e.when}</span>
                    <CaretRight size={18} className="flex-none text-ink3" aria-hidden />
                  </button>
                </li>
              )
            })}
          </ul>
        )}
      </section>
    </Screen>
  )
}
