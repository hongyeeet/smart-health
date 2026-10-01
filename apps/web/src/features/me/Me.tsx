import { useQuery } from '@tanstack/react-query'
import { api } from '@/data/repositories'
import { useGo } from '@/app/navigation'
import type { RouteId } from '@/app/routeIds'
import { Header, Screen } from '@/ui/layout'
import { Card } from '@/ui/primitives'
import { Brain, CalendarCheck, CaretRight, FilePdf, Globe, Lock, ShieldCheck, SignOut, Watch, ArrowCounterClockwise, type IconType } from '@/ui/icons'

const rows: { id: RouteId; title: string; sub: string; icon: IconType }[] = [
  { id: 'K2', title: 'What Smart Health has learned about you', sub: 'Your routines, preferences and food responses', icon: Brain },
  { id: 'L1', title: 'Doctor brief', sub: 'A clear summary for your visit', icon: FilePdf },
  { id: 'K3', title: 'Care plan', sub: 'Appointments, check-ups and your questions', icon: CalendarCheck },
  { id: 'K4', title: 'Connected sources', sub: 'Watch, glucose sensor, camera', icon: Watch },
  { id: 'K5', title: 'Language and display', sub: 'Language, dark mode, text size', icon: Globe },
  { id: 'K6', title: 'Privacy and consent', sub: 'What you share, and who can see it', icon: Lock },
  { id: 'K8', title: 'Data and account', sub: 'Export your data or delete your account', icon: ShieldCheck },
]

export function Me() {
  const go = useGo()
  const { data: p } = useQuery({ queryKey: ['patient'], queryFn: () => api.getPatient() })
  return (
    <Screen tabs>
      <Header title="Me" />
      <Card tone="hero" className="flex items-center gap-4">
        <span className="flex h-16 w-16 flex-none items-center justify-center rounded-full bg-brand font-serif text-xl text-on-brand" aria-hidden>
          T
        </span>
        <div>
          <p className="text-h2 font-bold">{p?.name ?? 'Mr Tan'}</p>
          <p className="text-sub text-ink2">
            {p ? `${p.age}, type 2 diabetes for ${p.diagnosedYearsAgo} years` : ''}
          </p>
          <p className="text-sub text-ink3">{p ? `Last HbA1c ${p.lastHba1c.value}%, ${p.lastHba1c.monthsAgo} months ago` : ''}</p>
        </div>
      </Card>
      <ul className="flex flex-col overflow-hidden rounded-card border border-line bg-card">
        {rows.map((r, i) => (
          <li key={r.id} className={i ? 'border-t border-line' : ''}>
            <button type="button" onClick={() => go(r.id)} className="press flex w-full items-center gap-3 px-4 py-3.5 text-left">
              <span className="flex h-11 w-11 flex-none items-center justify-center rounded-full bg-brand-soft text-brand">
                <r.icon size={22} aria-hidden />
              </span>
              <span className="min-w-0 flex-1">
                <span className="block text-body font-bold leading-snug">{r.title}</span>
                <span className="block text-sub text-ink2">{r.sub}</span>
              </span>
              <CaretRight size={20} className="flex-none text-ink3" aria-hidden />
            </button>
          </li>
        ))}
      </ul>
      <button type="button" onClick={() => go('A1')} className="press flex min-h-12 items-center justify-center gap-2 text-sub font-bold text-ink2">
        <ArrowCounterClockwise size={20} aria-hidden /> Replay onboarding
      </button>
      <p className="flex items-center justify-center gap-2 pb-2 text-center text-sub text-ink3">
        <SignOut size={18} aria-hidden /> Demo data. No real person.
      </p>
    </Screen>
  )
}
