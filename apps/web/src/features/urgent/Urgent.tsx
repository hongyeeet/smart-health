import { useEffect, useRef } from 'react'
import { useGo } from '@/app/navigation'
import { Header, Screen } from '@/ui/layout'
import { Alert, Button, Card, EmptyState, Skeleton, StatusPill } from '@/ui/primitives'
import { CheckCircle, Phone, Timer, Warning, WarningCircle } from '@/ui/icons'
import { useAcknowledge, useEscalate, useUrgentState, type UrgentState } from './api'
import { agoText, CallLink, clock, minutesAgo, secondsUntil, telHref, useNow } from './parts'

/** J1: the low-glucose alert. The wording is fixed on purpose: no doses, no food amounts, nothing beyond the two sentences below. */
export function Urgent() {
  const go = useGo()
  const { data, isError, refetch } = useUrgentState()

  if (isError && !data) {
    return (
      <Screen>
        <Header title="Low glucose alert" back backTo="B1" />
        <Alert tone="warn" onClick={() => void refetch()}>
          We could not check just now. If you feel unwell or confused, call 995 now. Tap here to try again.
        </Alert>
        <CallLink href="tel:995" primary>
          <Phone size={22} aria-hidden /> Call 995
        </CallLink>
      </Screen>
    )
  }
  if (!data) {
    return (
      <Screen>
        <Header title="Low glucose alert" back backTo="B1" />
        <Skeleton className="h-48" />
      </Screen>
    )
  }
  if (data.status === 'none') {
    return (
      <Screen>
        <Header title="Low glucose alert" back backTo="B1" />
        <EmptyState icon={CheckCircle} action={<Button onClick={() => go('B1')}>Back to Home</Button>}>
          No low glucose right now.
        </EmptyState>
        <Limits />
      </Screen>
    )
  }
  return <ActiveAlert s={data} />
}

function Limits() {
  return <p className="text-micro text-ink3">These limits are placeholders and have not had clinical review.</p>
}

function ActiveAlert({ s }: { s: UrgentState }) {
  const go = useGo()
  const now = useNow()
  const ack = useAcknowledge()
  const esc = useEscalate()
  const veryLow = s.tier === 'very_low'
  const acked = s.status === 'acknowledged'
  const age = minutesAgo(s.since, now)
  const untilContact = secondsUntil(s.contactAfter, now)
  const untilRecheck = secondsUntil(s.recheckAt, now)

  // The person has not answered in time: tell the contact once. The server also refuses to queue a second email.
  const auto = useRef<string | null>(null)
  useEffect(() => {
    if (s.status === 'active' && s.contactAfter && now >= new Date(s.contactAfter).getTime() && auto.current !== s.id && !esc.isPending) {
      auto.current = s.id
      esc.mutate()
    }
  })

  const sentence = `Your glucose looks ${veryLow ? 'very low' : 'low'}: ${s.value?.toFixed(1)} mmol/L, ${agoText(age)}`
  const emailable = s.channels.email

  return (
    <Screen tone="urgent">
      <Header title="Low glucose alert" back backTo="B1" />
      <div role="alert" className="flex flex-col gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <StatusPill tone="danger" icon={veryLow ? WarningCircle : Warning}>
            {veryLow ? 'Very low' : 'Low'}
          </StatusPill>
          {s.demo && <StatusPill tone="info">DEMO, not a real reading</StatusPill>}
        </div>
        <p className="num text-display font-bold" aria-hidden>
          {s.value?.toFixed(1)} <span className="text-h2 font-medium text-ink2">mmol/L</span>
        </p>
        <p className="text-h2 font-bold leading-snug">{sentence}</p>
        <p className="text-body">If you feel unwell or confused, call {s.emergencyNumber} now. Follow the plan your doctor gave you.</p>
      </div>

      {acked ? (
        <Card className="flex flex-col gap-2" aria-live="polite">
          <p className="flex items-center gap-2 text-body font-bold">
            <Timer size={22} aria-hidden /> Checking again in {clock(untilRecheck)}
          </p>
          <p className="text-sub text-ink2">You said you are okay. We will look at your sensor again in {s.recheckMinutes} minutes. If it is still low, we will alert you again.</p>
        </Card>
      ) : (
        <>
          {s.status === 'active' && s.hasContact && emailable && (
            <Alert tone="warn" icon={Timer}>
              {untilContact > 0
                ? `If you do not answer in ${clock(untilContact)}, we will email ${s.contactName ?? 'your emergency contact'}.`
                : `Telling ${s.contactName ?? 'your emergency contact'} now.`}
            </Alert>
          )}
          {s.status === 'active' && !emailable && (
            <Alert tone="warn">No emergency contact email is saved, so we cannot email anyone for you.</Alert>
          )}
        </>
      )}

      {s.escalated && (
        <Alert tone={s.emailQueued ? 'info' : 'warn'} title={s.emailQueued ? 'Your contact is being told' : 'No email could be sent'}>
          {s.emailQueued
            ? `We have asked to email ${s.contactName ?? 'your emergency contact'} that you may have low glucose.`
            : 'There is no emergency contact email saved, so nobody was emailed. Use the call buttons below.'}
        </Alert>
      )}

      <div className="flex flex-col gap-3" aria-label="What you can do">
        {veryLow && (
          <CallLink href={telHref(s.emergencyNumber)} primary>
            <Phone size={22} aria-hidden /> Call {s.emergencyNumber}
          </CallLink>
        )}
        {!acked && (
          <Button variant={veryLow ? 'secondary' : 'primary'} icon={CheckCircle} disabled={ack.isPending} onClick={() => ack.mutate()}>
            I'm okay now
          </Button>
        )}
        {!veryLow && (
          <CallLink href={telHref(s.emergencyNumber)}>
            <Phone size={22} aria-hidden /> Call {s.emergencyNumber}
          </CallLink>
        )}
        {s.contactPhone && (
          <CallLink href={telHref(s.contactPhone)}>
            <Phone size={22} aria-hidden /> Call {s.contactName ? `${s.contactName} (my contact)` : 'my contact'}
          </CallLink>
        )}
        {!s.escalated && (
          <Button variant="secondary" disabled={esc.isPending} onClick={() => esc.mutate()}>
            Tell my contact now
          </Button>
        )}
        {!s.hasContact && (
          <Button variant="ghost" onClick={() => go('K9')}>
            Add an emergency contact
          </Button>
        )}
      </div>

      {(ack.isError || esc.isError) && <Alert tone="warn">That did not go through. If you feel unwell or confused, call {s.emergencyNumber} now, then try again.</Alert>}
      <Limits />
    </Screen>
  )
}
