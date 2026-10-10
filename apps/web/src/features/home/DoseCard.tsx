import { Trans, useTranslation } from 'react-i18next'
import { useDoses, useMarkTaken } from '@/data/hooks'
import { useGo } from '@/app/navigation'
import { Alert, Button, Card, SectionTitle, StatusPill, TextLink } from '@/ui/primitives'
import { CheckCircle, Pill } from '@/ui/icons'

/**
 * Medicines on Home (prd F4): what to take now, what was not confirmed, and the next dose.
 *
 *  - A dose is "due now" from 2 hours before its time to 2 hours after, and shows a Taken button.
 *  - Past that, with no answer, it is "not confirmed" and offers "Tell us why" (sheet H7). Nothing is shown when no dose is unconfirmed.
 *  - With nothing due, the next dose is named with its day and time ("Next: CRESTOR, 1 Tab, tomorrow at 8:00 am").
 * The amount shown is the person's own label ("Metformin, 1 Tab"), never a suggestion.
 */
export function DoseCard() {
  const { t } = useTranslation()
  const { data, isError, refetch } = useDoses()
  const mark = useMarkTaken()
  const go = useGo()

  if (isError)
    return (
      <Alert tone="warn" onClick={() => void refetch()}>
        {t('home.dose.loadError', 'We could not load your medicines. Tap to try again.')}
      </Alert>
    )
  if (!data) return null
  if (!data.hasMedicines)
    return (
      <Card onClick={() => go('H1')} className="flex items-center gap-3">
        <span className="flex h-12 w-12 flex-none items-center justify-center rounded-full bg-brand-soft text-brand">
          <Pill size={24} aria-hidden />
        </span>
        <span className="min-w-0 flex-1">
          <span className="block text-body font-bold">{t('home.dose.addTitle', 'Add your medicines')}</span>
          <span className="block text-sub text-ink2">{t('home.dose.addSub', 'Then we can show you what to take and when.')}</span>
        </span>
      </Card>
    )

  const nothingDue = data.due.length === 0
  return (
    <Card tone="hero" className="flex flex-col gap-3">
      <div className="flex items-center justify-between gap-2">
        <SectionTitle>{nothingDue ? t('home.dose.yourMeds', 'Your medicines') : t('home.dose.dueNow', 'Due now')}</SectionTitle>
        {nothingDue && data.takenToday > 0 && <StatusPill tone="ok">{t('home.dose.allDone', 'All done for now')}</StatusPill>}
      </div>

      {data.due.map((d) => (
        <div key={d.id} className="flex flex-col gap-3">
          <div>
            <p className="break-words text-h2 font-bold leading-tight">{d.title}</p>
            <p className="text-sub text-ink2">
              {d.time}
              {d.withFood && t('home.dose.withFood', ', with food')}
            </p>
          </div>
          <Button icon={CheckCircle} onClick={() => mark.mutate(d.id)} disabled={mark.isPending}>
            {t('home.dose.taken', 'Taken')}
          </Button>
        </div>
      ))}
      {mark.isError && <Alert tone="warn">{t('home.dose.saveError', 'We could not save that just now. Please try again.')}</Alert>}

      {nothingDue && data.next && (
        <p className="text-body text-ink2">
          <Trans i18nKey="home.dose.next" defaults="Next: <0>{{title}}</0>, {{when}}." values={{ title: data.next.title, when: data.next.when }} components={[<b key="0" className="text-ink" />]} />
        </p>
      )}
      {nothingDue && !data.next && <p className="text-body text-ink2">{t('home.hero.nothingDue', 'Nothing more is due for now.')}</p>}
      {!nothingDue && data.next && (
        <p className="text-sub text-ink3">
          {t('home.dose.after', 'After this: {{title}}, {{when}}.', { title: data.next.title, when: data.next.when })}
        </p>
      )}

      {data.unconfirmed.length > 0 && (
        <div className="flex flex-col gap-3 rounded-card bg-well p-3.5">
          {data.unconfirmed.map((u) => (
            <div key={u.id} className="flex flex-col gap-1">
              <p className="text-body">{t('home.dose.notConfirmed', '{{when}} is not confirmed.', { when: u.whenLabel })}</p>
              <p className="text-sub text-ink3">{u.title}</p>
              <TextLink onClick={() => go('H7', { sheet: { doseId: u.id } })} className="self-start">
                {t('home.dose.tellUs', 'Tell us why')}
              </TextLink>
            </div>
          ))}
        </div>
      )}
    </Card>
  )
}
