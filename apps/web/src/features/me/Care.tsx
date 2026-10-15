/**
 * K3. Track appointments (it was called Care plan): the upcoming visits (with Cancel), the form to add a visit, earlier visits, and the checks and screenings on record. Dates only, nothing here says what to do about a check.
 * The questions for the doctor (K12) and the doctor brief (L1) have their own cards on Me, so they are not repeated here.
 */
import { useTranslation } from 'react-i18next'
import { Header, Screen } from '@/ui/layout'
import { Alert, Card, SectionTitle, Skeleton, StatusPill } from '@/ui/primitives'
import { useCarePlan, type Appointment } from './care/api'
import { AddVisit, PlannedVisit } from './care/AddVisit'
import { PreventiveStatusPill } from './care/parts'

export function Care() {
  const { t } = useTranslation()
  const { data, isError, isLoading } = useCarePlan()
  return (
    <Screen>
      <Header title={t('me.care.titleV2', 'Track appointments')} back backTo="K1" />

      {isError && <Alert tone="warn">{t('me.care.loadError', 'We could not load your care plan just now. Please try again in a moment.')}</Alert>}
      {isLoading && !data && <Skeleton className="h-40" />}

      {data && (
        <>
          {/* the visits on the left and the checks on the right from a laptop up; one column below that, in the same order */}
          <div className="grid gap-4 lg:grid-cols-2 lg:items-start lg:gap-6 [&>*]:min-w-0">
          <div className="flex flex-col gap-4">
          <Visits upcoming={data.upcoming.filter((a) => a.status === 'planned')} />

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
        </>
      )}
    </Screen>
  )
}

/** The planned visits (each can be cancelled) and the form to add one. Suggested visits are not shown. */
function Visits({ upcoming }: { upcoming: Appointment[] }) {
  const { t } = useTranslation()
  return (
    <>
      <section className="flex flex-col gap-2">
        <SectionTitle>{t('me.care.upcomingV2', 'Upcoming visits')}</SectionTitle>
        {upcoming.length === 0 ? (
          <p className="text-body text-ink2">{t('me.care.noVisitV2', 'No visit is planned yet. Add one below when you have a date.')}</p>
        ) : (
          <ul className="flex flex-col gap-3">
            {upcoming.map((a) => (
              <li key={a.id}>
                <PlannedVisit appt={a} />
              </li>
            ))}
          </ul>
        )}
      </section>
      <section className="flex flex-col gap-2">
        <SectionTitle>{t('me.appt.addTitle', 'Add a visit')}</SectionTitle>
        <AddVisit />
      </section>
    </>
  )
}
