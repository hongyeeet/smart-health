/**
 * K1 — Me.
 *
 * The person's own corner: what Equinox has learned about them (and the things waiting for a yes), their appointments, questions for
 * the doctor, doctor brief and reminders, then their settings (sources, language, and Data and account, which holds their details,
 * emergency contacts and consents). Adding a visit is on Track appointments (K3).
 */
import { useTranslation } from 'react-i18next'
import { useLearned } from '@/data/hooks'
import { useCarePlan } from './care/api'
import { useGo } from '@/app/navigation'
import type { RouteId } from '@/app/routeIds'
import { Header, Screen } from '@/ui/layout'
import { Card } from '@/ui/primitives'
import { Bell, Brain, CalendarCheck, CaretRight, ChatCircleDots, Globe, Stethoscope, UserCircle, Watch, type IconType } from '@/ui/icons'
import { UserSwitch } from '@/features/home/UserSwitch'

export function Me() {
  const { t } = useTranslation()
  const go = useGo()
  const { data } = useLearned()
  const care = useCarePlan()
  const openQuestions = care.data?.questions.filter((q) => q.status === 'open').length
  const rows: { id: RouteId; title: string; sub: string; icon: IconType; badge?: number }[] = [
    { id: 'K2', title: t('me.learned.title', 'What Equinox has learned'), sub: t('me.menu.learnedSub', 'Everything it noticed about you, and why. You decide what stays.'), icon: Brain, badge: data?.toConfirm },
    { id: 'K3', title: t('me.care.titleV2', 'Track appointments'), sub: t('me.menu.careSubV2', 'Add and cancel visits, and see which checks are due.'), icon: CalendarCheck },
    { id: 'K12', title: t('me.questions.title', 'Questions for your doctor'), sub: t('me.menu.questionsSub', 'What you want to ask at your next visit, and what is done.'), icon: ChatCircleDots, badge: openQuestions },
    { id: 'L1', title: t('me.menu.brief', 'Doctor brief'), sub: t('me.menu.briefSub', 'A printable report of your readings, symptoms and medicines for your next visit.'), icon: Stethoscope },
    { id: 'B2', title: t('me.menu.reminders', 'Reminders'), sub: t('me.menu.remindersSub', 'What is due and what you have opened.'), icon: Bell },
    { id: 'K4', title: t('me.sources.title', 'Connected sources'), sub: t('me.menu.sourcesSub', 'Where your glucose and watch data come from, and how fresh it is.'), icon: Watch },
    { id: 'K5', title: t('me.language.title', 'Language and display'), sub: t('me.menu.languageSub', 'Language, text size and light or dark.'), icon: Globe },
    { id: 'K8', title: t('me.data.title', 'Data and account'), sub: t('me.menu.dataSubV2', 'Your details, emergency contacts and consents, and your data.'), icon: UserCircle },
  ]
  return (
    <Screen tabs>
      <Header title={t('me.title', 'Me')} trailing={<UserSwitch />} />
      {/* One column on a phone; two equal-height columns from a tablet up, so the rows are not 700 or 976 px bars. An odd last row takes the full width instead of sitting alone. */}
      <ul className="grid grid-cols-1 gap-3 md:grid-cols-2 md:[&>li:last-child:nth-child(odd)]:col-span-2">
        {rows.map((r) => (
          <li key={r.id} className="flex">
            <Card onClick={() => go(r.id)} className="flex h-full w-full items-center gap-3">
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
