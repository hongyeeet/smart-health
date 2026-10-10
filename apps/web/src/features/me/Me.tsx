/**
 * K1 — Me.
 *
 * The person's own corner: what Smart Health has learned about them (and the things waiting for a yes), how it is going, their care plan,
 * doctor brief and reminders, then their settings (sources, emergency contact, language, privacy, data). Plan an appointment (K7) opens from the care plan.
 */
import { useLearned } from '@/data/hooks'
import { useGo } from '@/app/navigation'
import type { RouteId } from '@/app/routeIds'
import { Header, Screen } from '@/ui/layout'
import { Card } from '@/ui/primitives'
import { Bell, Brain, CalendarCheck, CaretRight, ChartLineUp, ClipboardText, Globe, Lock, Phone, Stethoscope, UserCircle, Watch, type IconType } from '@/ui/icons'
import { UserSwitch } from '@/features/home/UserSwitch'

export function Me() {
  const go = useGo()
  const { data } = useLearned()
  const rows: { id: RouteId; title: string; sub: string; icon: IconType; badge?: number }[] = [
    { id: 'K2', title: 'What Smart Health has learned', sub: 'Everything it noticed about you, and why. You decide what stays.', icon: Brain, badge: data?.toConfirm },
    { id: 'K10', title: 'How it is going', sub: 'Week by week, what you logged and did.', icon: ChartLineUp },
    { id: 'K3', title: 'Care plan', sub: 'Your next visit, checks that are due, and the questions you want to ask.', icon: CalendarCheck },
    { id: 'L1', title: 'Doctor brief', sub: 'A printable report of your readings, symptoms and medicines for your next visit.', icon: Stethoscope },
    { id: 'B2', title: 'Reminders', sub: 'What is due and what you have opened.', icon: Bell },
    { id: 'K4', title: 'Connected sources', sub: 'Where your glucose and watch data come from, and how fresh it is.', icon: Watch },
    { id: 'K9', title: 'Emergency contact', sub: 'Who we tell if your glucose looks very low and you do not answer.', icon: Phone },
    { id: 'K5', title: 'Language and display', sub: 'Language, text size and light or dark.', icon: Globe },
    { id: 'K6', title: 'Privacy and consent', sub: 'What you have agreed to, and your reminder emails.', icon: Lock },
    { id: 'K8', title: 'Data and account', sub: 'Download your data, or ask us to delete it.', icon: UserCircle },
    { id: 'A1', title: 'Set up again', sub: 'Go through the welcome questions and change your answers.', icon: ClipboardText },
  ]
  return (
    <Screen tabs>
      <Header title="Me" trailing={<UserSwitch />} />
      <ul className="flex flex-col gap-3">
        {rows.map((r) => (
          <li key={r.id}>
            <Card onClick={() => go(r.id)} className="flex items-center gap-3">
              <span className="flex h-12 w-12 flex-none items-center justify-center rounded-full bg-brand-soft text-brand">
                <r.icon size={24} aria-hidden />
              </span>
              <span className="min-w-0 flex-1">
                <span className="block text-body font-bold">{r.title}</span>
                <span className="block text-sub text-ink2">{r.sub}</span>
              </span>
              {r.badge ? <span className="flex h-7 min-w-7 items-center justify-center rounded-full bg-brass px-2 text-sub font-bold text-on-brand">{r.badge}</span> : null}
              <CaretRight size={20} className="flex-none text-ink3" aria-hidden />
            </Card>
          </li>
        ))}
      </ul>
    </Screen>
  )
}
