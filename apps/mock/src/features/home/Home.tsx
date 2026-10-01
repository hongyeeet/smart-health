import { useTranslation } from 'react-i18next'
import { useAnswerCheckin, useHome, useMarkTaken, useSnooze } from '@/data/hooks'
import { useGo } from '@/app/navigation'
import { useUi } from '@/state/store'
import type { HomeData } from '@/data/types'
import { Screen, Reveal } from '@/ui/layout'
import { Alert, Button, Card, Chip, SectionTitle, Skeleton, StatusPill, TextLink } from '@/ui/primitives'
import { Bell, CalendarBlank, CaretRight, CheckCircle, Drop, Footprints, Moon, PersonSimpleWalk, Smiley, Thermometer, Watch, Camera, type IconType } from '@/ui/icons'
import { cn } from '@/lib/cn'
import { useState } from 'react'

const tileIcon: Record<HomeData['tiles'][number]['key'], IconType> = { glucose: Drop, activity: Footprints, sleep: Moon, mood: Smiley }

export function Home() {
  const { t } = useTranslation()
  const { data, isLoading } = useHome()
  const go = useGo()
  const taken = useMarkTaken()
  const snooze = useSnooze()
  const answer = useAnswerCheckin()
  const toast = useUi((s) => s.showToast)
  const [answered, setAnswered] = useState<string | null>(null)

  if (isLoading || !data)
    return (
      <Screen tabs>
        <Skeleton className="h-16" />
        <Skeleton className="h-24" />
        <Skeleton className="h-48" />
      </Screen>
    )

  return (
    <Screen tabs>
      <Reveal id="home-head">
        <header className="flex items-start justify-between gap-3 pt-1">
          <div className="min-w-0">
            <p className="text-sub font-bold text-ink3">{data.dateLabel}</p>
            <h1 className="font-serif text-h1 font-medium tracking-tight">{t('home.greeting', { defaultValue: data.greeting })}</h1>
          </div>
          <button type="button" onClick={() => go('B2')} aria-label={`Notifications, ${data.unreadNotices} new`} className="press relative flex h-12 w-12 flex-none items-center justify-center rounded-full border border-line bg-card">
            <Bell size={24} aria-hidden />
            {data.unreadNotices > 0 && <span className="absolute right-2.5 top-2.5 h-2.5 w-2.5 rounded-full bg-brass ring-2 ring-card" />}
          </button>
        </header>
      </Reveal>

      {data.alert && (
        <Reveal id="home-alert" i={1}>
          <Alert tone="warn" onClick={() => go(data.alert!.to)}>
            {t('home.alert', { defaultValue: data.alert.text })}
          </Alert>
        </Reveal>
      )}

      <Reveal id="home-tiles" i={2}>
        <section aria-labelledby="glance" className="flex flex-col gap-3">
          <SectionTitle>
            <span id="glance">{t('home.glance', 'Today at a glance')}</span>
          </SectionTitle>
          <div className="grid grid-cols-2 gap-3 [[data-ts='2']_&]:grid-cols-1">
            {data.tiles.map((tile) => {
              const Icon = tileIcon[tile.key]
              return (
                <Card key={tile.key} onClick={() => go(tile.to)} className="flex min-h-[132px] flex-col justify-between !p-3.5">
                  <span className="flex items-center gap-2 text-sub font-bold text-ink2">
                    <Icon size={20} aria-hidden className="text-brand" />
                    {tile.label}
                  </span>
                  <span className="flex flex-wrap items-baseline gap-x-1.5">
                    <span className="num text-h1 leading-none">{tile.value}</span>
                    {tile.unit && <span className="text-sub text-ink2">{tile.unit}</span>}
                  </span>
                  <span className="text-sub leading-snug text-ink3">{tile.sub}</span>
                </Card>
              )
            })}
          </div>
        </section>
      </Reveal>

      <Reveal id="home-doses" i={3}>
        <Card tone="hero" className="flex flex-col gap-3">
          <div className="flex items-center justify-between">
            <h2 className="font-serif text-h2 font-medium">{t('home.dosesDue', 'Due now')}</h2>
            {data.dosesDue.length === 0 && <StatusPill tone="ok">All done for now</StatusPill>}
          </div>
          {data.dosesDue.map((d) => (
            <div key={d.id} className="flex flex-col gap-3">
              <div>
                <p className="text-h2 font-bold">{d.label}</p>
                <p className="text-body text-ink2">
                  {d.time}
                  {d.withFood && ', with food'}
                </p>
              </div>
              <Button icon={CheckCircle} onClick={() => taken.mutate(d.id, { onSuccess: () => toast('Marked as taken') })}>
                Taken
              </Button>
            </div>
          ))}
          {data.dosesDue.length === 0 && <p className="text-body text-ink2">Next: Atorvastatin 20 mg at 10:00 pm.</p>}
          {data.unconfirmed && (
            <div className="flex flex-col gap-1 rounded-card bg-well p-3.5">
              <p className="text-body">Yesterday's evening dose is not confirmed.</p>
              <TextLink onClick={() => go('H7', { sheet: { doseId: data.unconfirmed!.id } })} className="self-start">
                Tell us why
              </TextLink>
            </div>
          )}
        </Card>
      </Reveal>

      {data.checkin && (
        <Reveal id="home-checkin" i={4}>
          <Card className="flex flex-col gap-3">
            <div className="flex items-center gap-2 text-sub font-bold text-ink2">
              <Thermometer size={20} className="text-brand" aria-hidden />
              {t('home.checkin', 'A quick question')}
            </div>
            <p className="text-body">{data.checkin.question}</p>
            {answered ? (
              <StatusPill tone="ok">Thanks. Added to your doctor brief.</StatusPill>
            ) : (
              <div className="flex flex-wrap gap-2">
                {(['yes', 'no', 'skip'] as const).map((a) => (
                  <Chip key={a} onClick={() => { setAnswered(a); answer.mutate({ id: data.checkin!.id, answer: a }) }}>
                    {a === 'yes' ? 'Yes' : a === 'no' ? 'No' : 'Skip'}
                  </Chip>
                ))}
              </div>
            )}
            <p className="text-sub text-ink3">One question a day at most. Not a diagnosis.</p>
          </Card>
        </Reveal>
      )}

      {data.exercisePrompt && (
        <Reveal id="home-walk" i={5}>
          <Card tone="soft" className="flex flex-col gap-3">
            <div className="flex items-center gap-2 text-sub font-bold text-brand">
              <PersonSimpleWalk size={22} aria-hidden />
              Your usual walk time
            </div>
            <p className="text-body">{data.exercisePrompt.text}</p>
            <Button onClick={() => go('F1')}>Log a walk</Button>
            <div className="flex flex-wrap gap-2">
              <Button variant="secondary" size="md" onClick={() => snooze.mutate(undefined, { onSuccess: () => toast('No problem. We will not ask again tonight.') })}>
                Not today
              </Button>
              <Button variant="secondary" size="md" onClick={() => toast('Reminder set for 8:20 pm')}>
                Remind me later
              </Button>
            </div>
          </Card>
        </Reveal>
      )}

      <Reveal id="home-changed" i={6}>
        <section className="flex flex-col gap-1">
          <SectionTitle>{t('home.changed', 'What changed this week')}</SectionTitle>
          <ul className="divide-y divide-line">
            {data.whatChanged.map((w) => (
              <li key={w.id}>
                <button type="button" onClick={() => go(w.to)} className="press flex w-full items-center gap-3 py-3.5 text-left">
                  <span className="flex-1 text-body">{w.text}</span>
                  <CaretRight size={20} className="flex-none text-ink3" aria-hidden />
                </button>
              </li>
            ))}
          </ul>
        </section>
      </Reveal>

      <Reveal id="home-next" i={7}>
        <Card className="flex flex-col gap-3">
          <div className="flex items-center gap-2 text-sub font-bold text-ink2">
            <CalendarBlank size={20} className="text-brand" aria-hidden />
            Next up
          </div>
          <div>
            <p className="text-h2 font-bold">{data.next.title}</p>
            <p className="text-body text-ink2">{data.next.detail}</p>
          </div>
          <Button variant="secondary" onClick={() => go('K3')}>
            Prepare for the visit
          </Button>
        </Card>
      </Reveal>

      <Reveal id="home-sources" i={8}>
        <section className="flex flex-col gap-3">
          <SectionTitle>Connected sources</SectionTitle>
          <button type="button" onClick={() => go('C8')} className="press flex flex-col gap-2 rounded-card border border-line bg-card p-3.5 text-left">
            <span className="flex items-center justify-between text-body font-bold">
              Glucose sensor sprint
              <span className="text-sub text-ink2">
                Day {data.sprintDay} of {data.sprintOf}
              </span>
            </span>
            <span className="h-2 w-full overflow-hidden rounded-full bg-well" aria-hidden>
              <span className="block h-full rounded-full bg-brand" style={{ width: `${(data.sprintDay / data.sprintOf) * 100}%` }} />
            </span>
          </button>
          <div className="flex flex-wrap gap-2">
            {data.sources.map((s) => {
              const Icon = s.id === 'watch' ? Watch : s.id === 'sensor' ? Drop : Camera
              return (
                <button key={s.id} type="button" onClick={() => go('K4')} className={cn('press inline-flex min-h-12 items-center gap-2 rounded-chip border border-line bg-card px-3.5 text-sub')}>
                  <Icon size={20} className="text-brand" aria-hidden />
                  <span className="font-bold">{s.label}</span>
                  <span className="text-ink3">{s.synced}</span>
                </button>
              )
            })}
          </div>
          <p className="text-sub text-ink3">These only send data to Smart Health.</p>
        </section>
      </Reveal>
    </Screen>
  )
}
