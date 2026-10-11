import { useEffect, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { useGo } from '@/app/navigation'
import { Header, Screen } from '@/ui/layout'
import { Alert, Button, Card, EmptyState, Skeleton, StatusPill } from '@/ui/primitives'
import { CheckCircle, Phone, Timer, Warning, WarningCircle } from '@/ui/icons'
import { useAcknowledge, useEscalate, useUrgentState, type UrgentState } from './api'
import { agoText, CallLink, clock, minutesAgo, secondsUntil, telHref, useNow } from './parts'

/** J1: the low-glucose alert. The wording is fixed on purpose: no doses, no food amounts, nothing beyond the two sentences below. */
export function Urgent() {
  const { t } = useTranslation()
  const go = useGo()
  const { data, isError, refetch } = useUrgentState()

  if (isError && !data) {
    return (
      <Screen narrow>
        <Header title={t('urgent.title', 'Low glucose alert')} back backTo="B1" />
        <Alert tone="warn" onClick={() => void refetch()}>
          {t('urgent.checkFailed', 'We could not check just now. If you feel unwell or confused, call 995 now. Tap here to try again.')}
        </Alert>
        <CallLink href="tel:995" primary>
          <Phone size={22} aria-hidden /> {t('urgent.call', 'Call {{n}}', { n: '995' })}
        </CallLink>
      </Screen>
    )
  }
  if (!data) {
    return (
      <Screen narrow>
        <Header title={t('urgent.title', 'Low glucose alert')} back backTo="B1" />
        <Skeleton className="h-48" />
      </Screen>
    )
  }
  if (data.status === 'none') {
    return (
      <Screen narrow>
        <Header title={t('urgent.title', 'Low glucose alert')} back backTo="B1" />
        <EmptyState icon={CheckCircle} action={<Button onClick={() => go('B1')}>{t('urgent.backHome', 'Back to Home')}</Button>}>
          {t('urgent.none', 'No low glucose right now.')}
        </EmptyState>
        <Limits />
      </Screen>
    )
  }
  return <ActiveAlert s={data} />
}

function Limits() {
  const { t } = useTranslation()
  return <p className="text-micro text-ink3">{t('urgent.limits', 'These limits are placeholders and have not had clinical review.')}</p>
}

function ActiveAlert({ s }: { s: UrgentState }) {
  const { t } = useTranslation()
  const go = useGo()
  const now = useNow()
  const ack = useAcknowledge()
  const esc = useEscalate()
  const veryLow = s.tier === 'very_low'
  const acked = s.status === 'acknowledged'
  const age = minutesAgo(s.since, now)
  const untilContact = secondsUntil(s.contactAfter, now)
  const untilRecheck = secondsUntil(s.recheckAt, now)
  const contactName = s.contactName ?? t('urgent.yourContact', 'your emergency contact')

  // The person has not answered in time: tell the contact once. The server also refuses to queue a second email.
  const auto = useRef<string | null>(null)
  useEffect(() => {
    if (s.status === 'active' && s.contactAfter && now >= new Date(s.contactAfter).getTime() && auto.current !== s.id && !esc.isPending) {
      auto.current = s.id
      esc.mutate()
    }
  })

  const sentence = t('urgent.sentence', 'Your glucose looks {{level}}: {{value}} mmol/L, {{ago}}', {
    level: veryLow ? t('urgent.veryLow', 'very low') : t('urgent.low', 'low'),
    value: String(s.value?.toFixed(1)),
    ago: agoText(age),
  })
  const emailable = s.channels.email

  return (
    <Screen narrow tone="urgent">
      <Header title={t('urgent.title', 'Low glucose alert')} back backTo="B1" />
      <div role="alert" className="flex flex-col gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <StatusPill tone="danger" icon={veryLow ? WarningCircle : Warning}>
            {veryLow ? t('urgent.pillVeryLow', 'Very low') : t('urgent.pillLow', 'Low')}
          </StatusPill>
          {s.demo && <StatusPill tone="info">{t('urgent.demo', 'DEMO, not a real reading')}</StatusPill>}
        </div>
        <p className="num flex flex-wrap items-baseline gap-x-3 text-giant font-bold text-danger" aria-hidden>
          {s.value?.toFixed(1)} <span className="text-h2 font-medium text-ink2">mmol/L</span>
        </p>
        <p className="text-h2 font-bold leading-snug">{sentence}</p>
        <p className="text-body">{t('urgent.unwell', 'If you feel unwell or confused, call {{n}} now. Follow the plan your doctor gave you.', { n: s.emergencyNumber })}</p>
      </div>

      {acked ? (
        <Card className="flex flex-col gap-2" aria-live="polite">
          <p className="flex items-center gap-2 text-body font-bold">
            <Timer size={22} aria-hidden /> {t('urgent.rechecking', 'Checking again in {{time}}', { time: clock(untilRecheck) })}
          </p>
          <p className="text-sub text-ink2">
            {t('urgent.okayText', 'You said you are okay. We will look at your sensor again in {{minutes}} minutes. If it is still low, we will alert you again.', {
              minutes: s.recheckMinutes,
            })}
          </p>
        </Card>
      ) : (
        <>
          {s.status === 'active' && s.hasContact && emailable && (
            <Alert tone="warn" icon={Timer}>
              {untilContact > 0
                ? t('urgent.emailIn', 'If you do not answer in {{time}}, we will email {{name}}.', { time: clock(untilContact), name: contactName })
                : t('urgent.tellingNow', 'Telling {{name}} now.', { name: contactName })}
            </Alert>
          )}
          {s.status === 'active' && !emailable && <Alert tone="warn">{t('urgent.noEmail', 'No emergency contact email is saved, so we cannot email anyone for you.')}</Alert>}
        </>
      )}

      {s.escalated && (
        <Alert
          tone={s.emailQueued ? 'info' : 'warn'}
          title={s.emailQueued ? t('urgent.beingTold', 'Your contact is being told') : t('urgent.notSent', 'No email could be sent')}
        >
          {s.emailQueued
            ? t('urgent.askedEmail', 'We have asked to email {{name}} that you may have low glucose.', { name: contactName })
            : t('urgent.nobodyEmailed', 'There is no emergency contact email saved, so nobody was emailed. Use the call buttons below.')}
        </Alert>
      )}

      <div className="flex flex-col gap-3" aria-label={t('urgent.canDo', 'What you can do')}>
        {veryLow && (
          <CallLink href={telHref(s.emergencyNumber)} primary>
            <Phone size={22} aria-hidden /> {t('urgent.call', 'Call {{n}}', { n: s.emergencyNumber })}
          </CallLink>
        )}
        {!acked && (
          <Button size="xl" variant={veryLow ? 'secondary' : 'primary'} icon={CheckCircle} disabled={ack.isPending} onClick={() => ack.mutate()}>
            {t('urgent.imOkay', "I'm okay now")}
          </Button>
        )}
        {!veryLow && (
          <CallLink href={telHref(s.emergencyNumber)}>
            <Phone size={22} aria-hidden /> {t('urgent.call', 'Call {{n}}', { n: s.emergencyNumber })}
          </CallLink>
        )}
        {s.contactPhone && (
          <CallLink href={telHref(s.contactPhone)}>
            <Phone size={22} aria-hidden />{' '}
            {s.contactName ? t('urgent.callNamed', 'Call {{name}} (my contact)', { name: s.contactName }) : t('urgent.callMyContact', 'Call my contact')}
          </CallLink>
        )}
        {!s.escalated && (
          <Button variant="secondary" disabled={esc.isPending} onClick={() => esc.mutate()}>
            {t('urgent.tellNow', 'Tell my contact now')}
          </Button>
        )}
        {!s.hasContact && (
          <Button variant="ghost" onClick={() => go('K9')}>
            {t('urgent.addContact', 'Add an emergency contact')}
          </Button>
        )}
      </div>

      {(ack.isError || esc.isError) && (
        <Alert tone="warn">
          {t('urgent.failed', 'That did not go through. If you feel unwell or confused, call {{n}} now, then try again.', { n: s.emergencyNumber })}
        </Alert>
      )}
      <Limits />
    </Screen>
  )
}
