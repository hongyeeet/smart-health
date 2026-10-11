/**
 * Home for a first-time person: nothing logged yet and no medicines added. Instead of an empty page, it names the two first things
 * that help most. It replaces the dose card for that person only; once anything is logged or a medicine is added, Home is the usual one.
 */
import { useTranslation } from 'react-i18next'
import { useGo } from '@/app/navigation'
import { ForkKnife, Pill } from '@/ui/icons'
import { Button, Card, SectionTitle } from '@/ui/primitives'

export function StartHere() {
  const { t } = useTranslation()
  const go = useGo()
  return (
    <Card tone="hero" className="flex flex-col gap-4">
      <SectionTitle>{t('home.start.title', 'Start here')}</SectionTitle>
      <p className="text-body text-ink2">{t('home.start.body', 'Two things help most at the start. You can do them in any order.')}</p>
      <div className="flex flex-col gap-3 sm:flex-row">
        <Button icon={ForkKnife} onClick={() => go('E2')}>
          {t('home.action.meal', 'Log a meal')}
        </Button>
        <Button variant="secondary" icon={Pill} onClick={() => go('H1')}>
          {t('home.start.medicine', 'Add a medicine')}
        </Button>
      </div>
    </Card>
  )
}
