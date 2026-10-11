/**
 * K1 — Me.
 *
 * The person's own corner: what Smart Health has learned about them (and the things waiting for a yes), how it is going, their care plan,
 * doctor brief and reminders, then their settings (sources, emergency contact, language, privacy, data). Plan an appointment (K7) opens from the care plan.
 */
import { useTranslation } from 'react-i18next'
import { useLearned } from '@/data/hooks'
import { useCarePlan } from './care/api'
import { useGo } from '@/app/navigation'
import type { RouteId } from '@/app/routeIds'
import { Header, Screen } from '@/ui/layout'
import { Card } from '@/ui/primitives'
import { Bell, Brain, CalendarCheck, CaretRight, ChartLineUp, ChatCircleDots, ClipboardText, Globe, ListChecks, Lock, Phone, Stethoscope, UserCircle, Watch, type IconType } from '@/ui/icons'
import { UserSwitch } from '@/features/home/UserSwitch'

export function Me() {
  const { t } = useTranslation()
  const go = useGo()
  const { data } = useLearned()
  const care = useCarePlan()
  const openQuestions = care.data?.questions.filter((q) => q.status === 'open').length
  const rows: { id: RouteId; title: string; sub: string; icon: IconType; badge?: number }[] = [
    { id: 'K2', title: t('me.learned.title', 'What Smart Health has learned'), sub: t('me.menu.learnedSub', 'Everything it noticed about you, and why. You decide what stays.'), icon: Brain, badge: data?.toConfirm },
    { id: 'K10', title: t('me.diet.title', 'Diet tracking'), sub: t('me.menu.dietSub', 'Your baseline and a calendar of what you ate.'), icon: ChartLineUp },
    { id: 'K3', title: t('me.care.title', 'Care plan'), sub: t('me.menu.careSub', 'Your next visit, checks that are due, and the questions you want to ask.'), icon: CalendarCheck },
    { id: 'K12', title: t('me.questions.title', 'Questions for your doctor'), sub: t('me.menu.questionsSub', 'What you want to ask at your next visit, and what is done.'), icon: ChatCircleDots, badge: openQuestions },
    { id: 'L1', title: t('me.menu.brief', 'Doctor brief'), sub: t('me.menu.briefSub', 'A printable report of your readings, symptoms and medicines for your next visit.'), icon: Stethoscope },
    { id: 'B2', title: t('me.menu.reminders', 'Reminders'), sub: t('me.menu.remindersSub', 'What is due and what you have opened.'), icon: Bell },
    { id: 'K4', title: t('me.sources.title', 'Connected sources'), sub: t('me.menu.sourcesSub', 'Where your glucose and watch data come from, and how fresh it is.'), icon: Watch },
    { id: 'K9', title: t('me.contact.title', 'Emergency contact'), sub: t('me.menu.contactSub', 'Who we tell if your glucose looks very low and you do not answer.'), icon: Phone },
    { id: 'K5', title: t('me.language.title', 'Language and display'), sub: t('me.menu.languageSub', 'Language, text size and light or dark.'), icon: Globe },
    { id: 'K6', title: t('me.privacy.title', 'Privacy and consent'), sub: t('me.menu.privacySub', 'What you have agreed to, and your reminder emails.'), icon: Lock },
    { id: 'K8', title: t('me.data.title', 'Data and account'), sub: t('me.menu.dataSub', 'Download your data, or ask us to delete it.'), icon: UserCircle },
    { id: 'K11', title: t('me.menu.review', 'Review suggestions'), sub: t('me.menu.reviewSub', 'For reviewers: rate the suggestions Smart Health made.'), icon: ListChecks },
    { id: 'A1', title: t('me.menu.setupAgain', 'Set up again'), sub: t('me.menu.setupAgainSub', 'Go through the welcome questions and change your answers.'), icon: ClipboardText },
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
