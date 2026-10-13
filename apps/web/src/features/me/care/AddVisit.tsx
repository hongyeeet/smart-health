/**
 * The visit parts of the Care plan page (K3): the card for a planned visit (with Cancel) and the "Add a visit" form. A visit is saved
 * with a kind, a date and a time (Singapore time). Cancelling keeps the row (its status changes), so the history stays. No calendar is
 * called from here. Visits Smart Health once suggested are not offered any more: the person adds a visit themselves.
 */
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useUi } from '@/state/store'
import { Alert, Button, Card, Field, StatusPill } from '@/ui/primitives'
import { CalendarCheck, Check, X } from '@/ui/icons'
import { APPOINTMENT_KINDS, useCancelAppointment, useSaveAppointment, type Appointment, type StoredAppointmentKind } from './api'
import { singaporeInstant } from './parts'

const inputClass = 'min-h-12 w-full rounded-field border-[1.5px] border-line bg-card px-3.5 py-3 text-body text-ink focus:border-brand focus:outline-none'

export function AddVisit() {
  const { t } = useTranslation()
  const [kind, setKind] = useState<StoredAppointmentKind>('diabetes_review')
  const [date, setDate] = useState('')
  const [time, setTime] = useState('')
  const [formError, setFormError] = useState<string | null>(null)
  const save = useSaveAppointment()
  const toast = useUi((s) => s.showToast)

  const submit = () => {
    setFormError(null)
    if (!date || !time) return setFormError(t('me.appt.pickDateTime', 'Pick a date and a time.'))
    if (singaporeInstant(date, time) <= Date.now()) return setFormError(t('me.appt.pickFuture', 'Pick a time in the future.'))
    save.mutate(
      { kind, scheduledFor: `${date}T${time}`, suggestedId: null },
      {
        onSuccess: () => {
          toast(t('me.appt.saved', 'Visit saved.'))
          setKind('diabetes_review')
          setDate('')
          setTime('')
        },
        onError: (e) => setFormError(e.message),
      },
    )
  }

  return (
    <Card className="flex flex-col gap-4">
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
        </select>
      </div>
      <div className="grid gap-4 sm:grid-cols-2 [[data-ts='2']_&]:sm:grid-cols-1 [&>*]:min-w-0">
        <Field label={t('me.appt.date', 'Date')} type="date" value={date} onChange={setDate} hint={t('me.appt.singaporeTime', 'Singapore time.')} />
        <Field label={t('me.appt.time', 'Time')} type="time" value={time} onChange={setTime} />
      </div>
      {formError && <Alert tone="danger">{formError}</Alert>}
      <Button icon={Check} disabled={save.isPending} onClick={submit}>
        {save.isPending ? t('me.appt.saving', 'Saving') : t('me.appt.save', 'Save my visit')}
      </Button>
    </Card>
  )
}

export function PlannedVisit({ appt }: { appt: Appointment }) {
  const { t } = useTranslation()
  const [asking, setAsking] = useState(false)
  const cancel = useCancelAppointment()
  const toast = useUi((s) => s.showToast)

  return (
    <Card className="flex flex-col gap-2">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="text-body font-bold">{appt.kindLabel}</span>
        <StatusPill tone="ok" icon={CalendarCheck}>
          {t('me.care.planned', 'Planned')}
        </StatusPill>
      </div>
      <p className="text-body text-ink">{appt.scheduledLabel}</p>
      {asking ? (
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
      )}
    </Card>
  )
}
