/**
 * K3. Care plan: the next visit, the checks and screenings on record, and a link to the questions for the doctor (K12).
 * Dates only, nothing here says what to do about a check. The doctor brief is one tap away (L1).
 */
import { useTranslation } from 'react-i18next'
import { useGo } from '@/app/navigation'
import { Header, Screen } from '@/ui/layout'
import { Alert, Button, Card, SectionTitle, Skeleton, StatusPill, TextLink } from '@/ui/primitives'
import { CalendarBlank, ChatCircleDots, Stethoscope } from '@/ui/icons'
import { useCarePlan, type Appointment } from './care/api'
import { PreventiveStatusPill } from './care/parts'

export function Care() {
  const { t } = useTranslation()
  const go = useGo()
  const { data, isError, isLoading } = useCarePlan()
  return (
    <Screen>
      <Header title={t('me.care.title', 'Care plan')} back backTo="K1" />

      {isError && <Alert tone="warn">{t('me.care.loadError', 'We could not load your care plan just now. Please try again in a moment.')}</Alert>}
      {isLoading && !data && <Skeleton className="h-40" />}

      {data && (
        <>
          {/* the visits on the left and the checks on the right from a laptop up; one column below that, in the same order */}
          <div className="grid gap-4 lg:grid-cols-2 lg:items-start lg:gap-6 [&>*]:min-w-0">
          <div className="flex flex-col gap-4">
          <NextVisit next={data.nextAppointment} suggested={data.upcoming.filter((a) => a.status === 'suggested')} />

          {data.earlier.length > 0 && (
            <section className="flex flex-col gap-2">
              <SectionTitle>{t('me.care.earlier', 'Earlier visits')}</SectionTitle>
              <ul className="flex flex-col gap-3">
                {data.earlier.map((a) => (
                  <li key={a.id}>
                    <Card className="flex flex-col gap-2">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <span className="text-body font-bold">{a.kindLabel}</span>
                        <StatusPill tone="neutral">{t('me.care.past', 'Past')}</StatusPill>
                      </div>
                      {a.scheduledLabel && <p className="text-sub text-ink2">{a.scheduledLabel}</p>}
                    </Card>
                  </li>
                ))}
              </ul>
            </section>
          )}
          </div>

          <section className="flex flex-col gap-2">
            <SectionTitle>{t('me.care.checks', 'Checks and screenings')}</SectionTitle>
            <p className="text-sub text-ink3">{t('me.care.basedOnDates', 'Based only on the dates on record.')}</p>
            <ul className="flex flex-col gap-3">
              {data.preventive.map((p) => (
                <li key={p.kind}>
                  <Card className="flex flex-col gap-2">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <span className="text-body font-bold">{p.label}</span>
                      <PreventiveStatusPill status={p.status} />
                    </div>
                    <p className="text-sub text-ink2">{p.detail}</p>
                  </Card>
                </li>
              ))}
            </ul>
          </section>
          </div>

          <div>
            <TextLink icon={ChatCircleDots} onClick={() => go('K12')}>
              {t('me.care.questionsLink', 'Questions for your doctor')}
            </TextLink>
          </div>

          <Card tone="soft" className="flex flex-col gap-3 lg:max-w-xl">
            <p className="text-sub text-ink2">{t('me.menu.briefSub', 'A printable report of your readings, symptoms and medicines for your next visit.')}</p>
            <Button icon={Stethoscope} onClick={() => go('L1')}>
              {t('me.care.brief', 'Generate my doctor brief')}
            </Button>
          </Card>
        </>
      )}
    </Screen>
  )
}

function NextVisit({ next, suggested }: { next: Appointment | null; suggested: Appointment[] }) {
  const { t } = useTranslation()
  const go = useGo()
  return (
    <section className="flex flex-col gap-2">
      <SectionTitle>{t('me.care.nextVisit', 'Next visit')}</SectionTitle>
      <Card className="flex flex-col gap-3">
        {next ? (
          <>
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="text-body font-bold">{next.kindLabel}</span>
              <StatusPill tone="ok">{t('me.care.planned', 'Planned')}</StatusPill>
            </div>
            <p className="text-body text-ink">{next.scheduledLabel}</p>
          </>
        ) : (
          <p className="text-body text-ink2">{t('me.care.noVisit', 'No visit is planned yet. Log one when you have a date.')}</p>
        )}
        {suggested.length > 0 && (
          <p className="text-sub text-ink2">
            {suggested.length === 1
              ? t('me.care.suggestedOne', 'Smart Health has suggested a visit. You can confirm it when you log an appointment.')
              : t('me.care.suggestedMany', 'Smart Health has suggested {{n}} visits. You can confirm them when you log an appointment.', { n: suggested.length })}
          </p>
        )}
        <Button variant="secondary" size="md" icon={CalendarBlank} onClick={() => go('K7')}>
          {t('me.care.logAppointment', 'Log an appointment')}
        </Button>
      </Card>
    </section>
  )
}
