/**
 * K7. Plan an appointment: save a visit the person has agreed, or confirm one Smart Health suggested. Cancelling keeps the row
 * (its status changes), so the history stays. No calendar is called from here.
 */
import { useState } from 'react'
import { useUi } from '@/state/store'
import { Header, Screen } from '@/ui/layout'
import { Alert, Button, Card, Field, SectionTitle, Skeleton, StatusPill, TextLink } from '@/ui/primitives'
import { CalendarCheck, Check, X } from '@/ui/icons'
import { APPOINTMENT_KINDS, useAppointments, useCancelAppointment, useSaveAppointment, type Appointment, type AppointmentKind } from './care/api'
import { singaporeInstant, singaporeStamp } from './care/parts'

const inputClass = 'min-h-12 w-full rounded-field border-[1.5px] border-line bg-card px-3.5 py-3 text-body text-ink focus:border-brand focus:outline-none'

export function Appointment() {
  const { data, isError, isLoading } = useAppointments()
  const [suggestedId, setSuggestedId] = useState<string | null>(null)
  const [kind, setKind] = useState<AppointmentKind>('diabetes_review')
  const [date, setDate] = useState('')
  const [time, setTime] = useState('')
  const [place, setPlace] = useState('')
  const [formError, setFormError] = useState<string | null>(null)
  const save = useSaveAppointment()
  const toast = useUi((s) => s.showToast)

  const confirmSuggested = (a: Appointment) => {
    setSuggestedId(a.id)
    setKind(a.kind)
    setPlace(a.location ?? '')
    setDate(a.scheduledFor ? singaporeDay(a.scheduledFor) : '')
    setTime(a.scheduledFor ? singaporeClock(a.scheduledFor) : '')
    setFormError(null)
  }

  const clearForm = () => {
    setSuggestedId(null)
    setKind('diabetes_review')
    setDate('')
    setTime('')
    setPlace('')
    setFormError(null)
  }

  const submit = () => {
    setFormError(null)
    if (!date || !time) return setFormError('Pick a date and a time.')
    if (singaporeInstant(date, time) <= Date.now()) return setFormError('Pick a time in the future.')
    save.mutate(
      { kind, scheduledFor: `${date}T${time}`, location: place.trim() || null, suggestedId },
      {
        onSuccess: () => {
          toast('Visit saved.')
          clearForm()
        },
        onError: (e) => setFormError(e.message),
      },
    )
  }

  return (
    <Screen>
      <Header title="Plan an appointment" back backTo="K3" />

      <section className="flex flex-col gap-2">
        <SectionTitle>Your upcoming visits</SectionTitle>
        {isError && <Alert tone="warn">We could not load your visits just now. Please try again in a moment.</Alert>}
        {isLoading && !data && <Skeleton className="h-28" />}
        {data && data.length === 0 && <p className="text-body text-ink2">No visits yet. Save one below.</p>}
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
        <SectionTitle>{suggestedId ? 'Confirm this visit' : 'Add a visit'}</SectionTitle>
        <Card className="flex flex-col gap-4">
          {suggestedId && (
            <Alert tone="warn" icon={CalendarCheck}>
              You are confirming a visit Smart Health suggested. Change the date, time or place if needed.{' '}
              <TextLink onClick={clearForm}>Stop confirming</TextLink>
            </Alert>
          )}
          <div className="flex flex-col gap-1.5">
            <label htmlFor="visit-kind" className="text-sub font-bold text-ink">
              Kind of visit
            </label>
            <select id="visit-kind" className={inputClass} value={kind} onChange={(e) => setKind(e.target.value as AppointmentKind)}>
              {APPOINTMENT_KINDS.map((k) => (
                <option key={k.value} value={k.value}>
                  {k.label}
                </option>
              ))}
            </select>
          </div>
          <Field label="Date" type="date" value={date} onChange={setDate} hint="Singapore time." />
          <Field label="Time" type="time" value={time} onChange={setTime} />
          <Field label="Place (optional)" value={place} onChange={setPlace} placeholder="For example: Polyclinic, level 2" />
          {formError && <Alert tone="danger">{formError}</Alert>}
          <Button icon={Check} disabled={save.isPending} onClick={submit}>
            {save.isPending ? 'Saving' : suggestedId ? 'Confirm this visit' : 'Save my visit'}
          </Button>
        </Card>
      </section>
    </Screen>
  )
}

function VisitCard({ appt, onConfirm }: { appt: Appointment; onConfirm: () => void }) {
  const [asking, setAsking] = useState(false)
  const cancel = useCancelAppointment()
  const toast = useUi((s) => s.showToast)
  const planned = appt.status === 'planned'

  return (
    <Card className="flex flex-col gap-2">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="text-body font-bold">{appt.kindLabel}</span>
        {planned ? <StatusPill tone="ok" icon={CalendarCheck}>Planned</StatusPill> : <StatusPill tone="brand">Suggested</StatusPill>}
      </div>
      <p className="text-body text-ink">{appt.scheduledLabel ?? 'No date yet'}</p>
      {appt.location && <p className="text-sub text-ink2">{appt.location}</p>}
      {appt.suggestedReason && <p className="text-sub text-ink2">{appt.suggestedReason}</p>}
      {appt.confirmedAt && <p className="text-sub text-ink3">You confirmed this on {singaporeStamp(appt.confirmedAt)}.</p>}

      {planned &&
        (asking ? (
          <div className="flex flex-col gap-2 sm:flex-row">
            <Button
              variant="danger"
              size="md"
              icon={X}
              disabled={cancel.isPending}
              onClick={() => cancel.mutate(appt.id, { onSuccess: () => toast('Visit cancelled.') })}
            >
              Yes, cancel this visit
            </Button>
            <Button variant="secondary" size="md" onClick={() => setAsking(false)}>
              Keep it
            </Button>
          </div>
        ) : (
          <Button variant="ghost" size="md" icon={X} onClick={() => setAsking(true)} aria-label={`Cancel ${appt.kindLabel} visit`}>
            Cancel this visit
          </Button>
        ))}
      {!planned && (
        <Button variant="secondary" size="md" icon={Check} onClick={onConfirm} aria-label={`Confirm the suggested ${appt.kindLabel} visit`}>
          Confirm this visit
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
