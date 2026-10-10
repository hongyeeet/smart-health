/** K6. What each consent allows, a switch for each, the history of changes, and the email reminder switch. Revoking the data-use consent asks first. */
import { useState } from 'react'
import { useUi } from '@/state/store'
import { Header, Screen } from '@/ui/layout'
import { Alert, Button, Card, SectionTitle, Skeleton, Toggle } from '@/ui/primitives'
import { EmailCard } from './settings/EmailCard'
import { type ConsentKind, type ConsentHistory, useConsents, useSetConsent } from './settings/api'
import { fmtDate } from './settings/rules'

const CONSENTS: { kind: ConsentKind; title: string; sub: string; required?: boolean }[] = [
  {
    kind: 'data_processing',
    title: 'Use my health data',
    sub: 'Lets Smart Health read what you log and what your devices send, so it can show your insights, reminders and doctor brief.',
    required: true,
  },
  { kind: 'brief_sharing', title: 'Share my doctor brief', sub: 'Lets you make a link to your doctor brief. You choose each time, and you can turn a link off.' },
  { kind: 'calendar_access', title: 'Add visits to my calendar', sub: 'Lets Smart Health add the medicine times and appointments you confirm to your calendar.' },
  { kind: 'caregiver_view', title: 'Let a caregiver see my data', sub: 'Lets someone you choose view your readings and summaries.' },
  { kind: 'research_use', title: 'Use my data for research', sub: 'Optional. Never includes your name.' },
]
const TITLE = Object.fromEntries(CONSENTS.map((c) => [c.kind, c.title])) as Record<ConsentKind, string>

export function Privacy() {
  const consents = useConsents()
  const setConsent = useSetConsent()
  const showToast = useUi((s) => s.showToast)
  const [askOff, setAskOff] = useState<ConsentKind | null>(null)

  const apply = (kind: ConsentKind, granted: boolean) =>
    setConsent.mutate({ kind, granted }, {
      onSuccess: () => {
        setAskOff(null)
        showToast(granted ? 'Turned on' : 'Turned off')
      },
    })

  const change = (kind: ConsentKind, granted: boolean) => {
    // Turning off the data-use consent stops the app working, so it is confirmed first.
    if (!granted && kind === 'data_processing') setAskOff(kind)
    else apply(kind, granted)
  }

  const history: ConsentHistory[] = consents.data?.history ?? []

  return (
    <Screen>
      <Header title="Privacy and consent" back backTo="K1" />
      <p className="text-body text-ink2">You can change any of these at any time. Turning one off does not delete your data.</p>

      <section className="flex flex-col gap-3">
        <SectionTitle>Your choices</SectionTitle>
        {consents.isPending && <Skeleton className="h-64" />}
        {consents.isError && <Alert tone="warn">We could not load your choices just now. {consents.error?.message}</Alert>}
        {consents.data && (
          <Card className="!py-1">
            <ul className="divide-y divide-line">
              {CONSENTS.map((c) => {
                const row = consents.data.consents.find((x) => x.kind === c.kind)
                const granted = !!row?.granted
                return (
                  <li key={c.kind} className="flex flex-col gap-3 py-3.5">
                    <div className="flex items-start justify-between gap-4">
                      <div className="min-w-0 flex-1">
                        <p className="text-body font-bold">{c.title}</p>
                        <p className="text-sub text-ink2">{c.sub}</p>
                        <p className="text-sub text-ink3">
                          {c.required && 'Required to use the app. '}
                          {granted ? `On${row?.grantedAt ? ` since ${fmtDate(row.grantedAt)}` : ''}` : 'Off'}
                        </p>
                      </div>
                      <Toggle on={granted} onChange={(v) => change(c.kind, v)} label={c.title} />
                    </div>
                    {askOff === c.kind && (
                      <Alert tone="warn" title="Turn off using your health data?">
                        <p>Smart Health will stop reading what you log and what your devices send. Insights, reminders and the doctor brief will stop until you turn this on again. Nothing is deleted.</p>
                        <div className="mt-3 flex flex-col gap-2">
                          <Button variant="danger" disabled={setConsent.isPending} onClick={() => apply(c.kind, false)}>
                            Turn off
                          </Button>
                          <Button variant="ghost" onClick={() => setAskOff(null)}>
                            Keep it on
                          </Button>
                        </div>
                      </Alert>
                    )}
                  </li>
                )
              })}
            </ul>
          </Card>
        )}
        {setConsent.isError && <Alert tone="warn">That change was not saved. {setConsent.error?.message}</Alert>}
      </section>

      {history.length > 0 && (
        <section className="flex flex-col gap-3">
          <SectionTitle>History</SectionTitle>
          <Card tone="soft">
            <ul className="flex flex-col gap-2 text-sub">
              {history.map((h) => (
                <li key={`${h.kind}-${h.grantedAt}`}>
                  <span className="font-bold">{TITLE[h.kind]}</span>: on from {fmtDate(h.grantedAt)}
                  {h.revokedAt ? `, off from ${fmtDate(h.revokedAt)}` : ', still on'}
                </li>
              ))}
            </ul>
          </Card>
        </section>
      )}

      <EmailCard />
    </Screen>
  )
}
