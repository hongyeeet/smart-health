/**
 * K7. Log an appointment: save a visit the person has agreed, or confirm one Smart Health suggested. Cancelling keeps the row
 * (its status changes), so the history stays. No calendar is called from here.
 */
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useUi } from '@/state/store'
import { Header, Screen } from '@/ui/layout'
import { Alert, Button, Card, Field, SectionTitle, Skeleton, StatusPill, TextLink } from '@/ui/primitives'
import { CalendarCheck, Check, X } from '@/ui/icons'
import {
  APPOINTMENT_KINDS,
  RETIRED_KIND_LABELS,
  useAppointments,
  useCancelAppointment,
  useSaveAppointment,
  type Appointment,
  type StoredAppointmentKind,
} from './care/api'
import { singaporeInstant, singaporeStamp } from './care/parts'

const inputClass = 'min-h-12 w-full rounded-field border-[1.5px] border-line bg-card px-3.5 py-3 text-body text-ink focus:border-brand focus:outline-none'

export function Appointment() {
  const { t } = useTranslation()
  const { data, isError, isLoading } = useAppointments()
  const [suggestedId, setSuggestedId] = useState<string | null>(null)
  const [kind, setKind] = useState<StoredAppointmentKind>('diabetes_review')
  const [date, setDate] = useState('')
  const [time, setTime] = useState('')
  const [formError, setFormError] = useState<string | null>(null)
  const save = useSaveAppointment()
  const toast = useUi((s) => s.showToast)

  const confirmSuggested = (a: Appointment) => {
    setSuggestedId(a.id)
    setKind(a.kind)
    setDate(a.scheduledFor ? singaporeDay(a.scheduledFor) : '')
    setTime(a.scheduledFor ? singaporeClock(a.scheduledFor) : '')
    setFormError(null)
  }

  const clearForm = () => {
    setSuggestedId(null)
    setKind('diabetes_review')
    setDate('')
    setTime('')
    setFormError(null)
  }

  const submit = () => {
    setFormError(null)
    if (!date || !time) return setFormError(t('me.appt.pickDateTime', 'Pick a date and a time.'))
    if (singaporeInstant(date, time) <= Date.now()) return setFormError(t('me.appt.pickFuture', 'Pick a time in the future.'))
    save.mutate(
      { kind, scheduledFor: `${date}T${time}`, suggestedId },
      {
        onSuccess: () => {
          toast(t('me.appt.saved', 'Visit saved.'))
          clearForm()
        },
        onError: (e) => setFormError(e.message),
      },
    )
  }

  // A suggested visit may hold a kind the form no longer offers; it is shown as its old label so the person sees what they confirm.
  const retired = RETIRED_KIND_LABELS[kind]

  return (
    <Screen>
      <Header title={t('me.appt.title', 'Log an appointment')} back backTo="K3" />

      {/* the list of visits on the left and the form on the right from a laptop up */}
      <div className="grid gap-4 lg:grid-cols-2 lg:items-start lg:gap-6 [&>*]:min-w-0">
      <section className="flex flex-col gap-2">
        <SectionTitle>{t('me.appt.upcoming', 'Your upcoming visits')}</SectionTitle>
        {isError && <Alert tone="warn">{t('me.appt.loadError', 'We could not load your visits just now. Please try again in a moment.')}</Alert>}
        {isLoading && !data && <Skeleton className="h-28" />}
        {data && data.length === 0 && <p className="text-body text-ink2">{t('me.appt.noVisits', 'No visits yet. Log one below.')}</p>}
        {data && data.length > 0 && (
          <ul className="flex flex-col gap-3">
            {data.map((a) => (
              <li key={a.id}>
                <VisitCard appt={a} onConfirm={() => confirmSuggested(a)} />
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="flex flex-col gap-2">
        <SectionTitle>{suggestedId ? t('me.appt.confirmTitle', 'Confirm this visit') : t('me.appt.addTitle', 'Add a visit')}</SectionTitle>
        <Card className="flex flex-col gap-4">
          {suggestedId && (
            <Alert tone="warn" icon={CalendarCheck}>
              {t('me.appt.confirming', 'You are confirming a visit Smart Health suggested. Change the date or time if needed.')}{' '}
              <TextLink onClick={clearForm}>{t('me.appt.stopConfirming', 'Stop confirming')}</TextLink>
            </Alert>
          )}
          <div className="flex flex-col gap-1.5">
            <label htmlFor="visit-kind" className="text-sub font-bold text-ink">
              {t('me.appt.kindOfVisit', 'Kind of visit')}
            </label>
            <select id="visit-kind" className={inputClass} value={kind} onChange={(e) => setKind(e.target.value as StoredAppointmentKind)}>
              {APPOINTMENT_KINDS.map((k) => (
                <option key={k.value} value={k.value}>
                  {t(`me.appt.kind.${k.value}`, k.label)}
                </option>
              ))}
              {retired && <option value={kind}>{retired}</option>}
            </select>
          </div>
          <div className="grid gap-4 sm:grid-cols-2 [[data-ts='2']_&]:sm:grid-cols-1 [&>*]:min-w-0">
            <Field label={t('me.appt.date', 'Date')} type="date" value={date} onChange={setDate} hint={t('me.appt.singaporeTime', 'Singapore time.')} />
            <Field label={t('me.appt.time', 'Time')} type="time" value={time} onChange={setTime} />
          </div>
          {formError && <Alert tone="danger">{formError}</Alert>}
          <Button icon={Check} disabled={save.isPending} onClick={submit}>
            {save.isPending ? t('me.appt.saving', 'Saving') : suggestedId ? t('me.appt.confirmTitle', 'Confirm this visit') : t('me.appt.save', 'Save my visit')}
          </Button>
        </Card>
      </section>
      </div>
    </Screen>
  )
}

function VisitCard({ appt, onConfirm }: { appt: Appointment; onConfirm: () => void }) {
  const { t } = useTranslation()
  const [asking, setAsking] = useState(false)
  const cancel = useCancelAppointment()
  const toast = useUi((s) => s.showToast)
  const planned = appt.status === 'planned'

  return (
    <Card className="flex flex-col gap-2">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="text-body font-bold">{appt.kindLabel}</span>
        {planned ? (
          <StatusPill tone="ok" icon={CalendarCheck}>
            {t('me.care.planned', 'Planned')}
          </StatusPill>
        ) : (
          <StatusPill tone="brand">{t('me.appt.suggested', 'Suggested')}</StatusPill>
        )}
      </div>
      <p className="text-body text-ink">{appt.scheduledLabel ?? t('me.appt.noDateYet', 'No date yet')}</p>
      {appt.suggestedReason && <p className="text-sub text-ink2">{appt.suggestedReason}</p>}
      {appt.confirmedAt && <p className="text-sub text-ink3">{t('me.appt.confirmedOn', 'You confirmed this on {{when}}.', { when: singaporeStamp(appt.confirmedAt) })}</p>}

      {planned &&
        (asking ? (
          <div className="flex flex-col gap-2 sm:flex-row">
            <Button
              variant="danger"
              size="md"
              icon={X}
              disabled={cancel.isPending}
              onClick={() => cancel.mutate(appt.id, { onSuccess: () => toast(t('me.appt.cancelled', 'Visit cancelled.')) })}
            >
              {t('me.appt.yesCancel', 'Yes, cancel this visit')}
            </Button>
            <Button variant="secondary" size="md" onClick={() => setAsking(false)}>
              {t('me.care.keepIt', 'Keep it')}
            </Button>
          </div>
        ) : (
          <Button variant="ghost" size="md" icon={X} onClick={() => setAsking(true)} aria-label={t('me.appt.cancelAria', 'Cancel {{kind}} visit', { kind: appt.kindLabel })}>
            {t('me.appt.cancelThis', 'Cancel this visit')}
          </Button>
        ))}
      {!planned && (
        <Button
          variant="secondary"
          size="md"
          icon={Check}
          onClick={onConfirm}
          aria-label={t('me.appt.confirmAria', 'Confirm the suggested {{kind}} visit', { kind: appt.kindLabel })}
        >
          {t('me.appt.confirmTitle', 'Confirm this visit')}
        </Button>
      )}
    </Card>
  )
}

/** Singapore date and clock for a stored instant, to fill the form when confirming a suggested visit. */
function singaporeDay(iso: string): string {
  return new Intl.DateTimeFormat('sv-SE', { timeZone: 'Asia/Singapore' }).format(new Date(iso))
}

function singaporeClock(iso: string): string {
  return new Intl.DateTimeFormat('en-GB', { timeZone: 'Asia/Singapore', hour: '2-digit', minute: '2-digit', hour12: false }).format(new Date(iso))
}
