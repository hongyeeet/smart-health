/**
 * K10 — Diet tracking (formerly "How it is going").
 *
 * The baseline is the first two full weeks the person logged (calories and salt per meal, and the share of doses taken on time),
 * on its own in one card. Below it, a calendar of the meals logged each day, with the day's totals. This is what the person did. It does
 * not claim the app caused any change.
 */
import { useTranslation } from 'react-i18next'
import { useProgress } from '@/data/hooks'
import { Header, Screen } from '@/ui/layout'
import { Alert, Skeleton } from '@/ui/primitives'
import { BaselineCard } from './progress/BaselineCard'
import { DietCalendar } from './progress/DietCalendar'

export function Progress() {
  const { t } = useTranslation()
  const { data, isError } = useProgress()
  return (
    <Screen>
      <Header title={t('me.diet.title', 'Diet tracking')} back backTo="K1" sub={t('me.diet.sub', 'Your starting point, and what you logged each day.')} />
      {isError && <Alert tone="warn">{t('me.progress.loadError', 'We could not load this just now.')}</Alert>}
      {!data && !isError && <Skeleton className="h-56" />}
      {data && <BaselineCard progress={data} />}
      <DietCalendar />
    </Screen>
  )
}
