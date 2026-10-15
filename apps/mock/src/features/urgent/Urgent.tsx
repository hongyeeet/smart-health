import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { appConfig } from '@/config/app'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/data/repositories'
import { useGo } from '@/app/navigation'
import { useUi } from '@/state/store'
import { Screen } from '@/ui/layout'
import { Alert, Button, Card, Chip, StatusPill, TextLink } from '@/ui/primitives'
import { CheckCircle, Phone, ShieldCheck, Timer, WarningCircle } from '@/ui/icons'
import { clock } from '@/lib/format'

type Tier = 1 | 2

/**
 * Low-glucose alerts in two tiers. Written by people, no AI, no animation, no network call.
 *  Tier 1, low (below 4.0): can still treat it. Follow the doctor's plan, recheck in 15 minutes, check in.
 *  Tier 2, very low (below 3.0): may be unable to function. Call 995 and the emergency contact is alerted.
 * A low that does not improve, or a "worse" answer at the check-in, moves to tier 2.
 * Thresholds are placeholders pending clinical validation (config/app.ts).
 */
export function Urgent() {
  const [sp] = useSearchParams()
  const [tier, setTier] = useState<Tier>(sp.get('tier') === '1' ? 1 : 2)
  const { data: contact } = useQuery({ queryKey: ['contact'], queryFn: () => api.getEmergencyContact() })
  const go = useGo()
  const setRecheck = useUi((s) => s.setRecheck)
  const [hold, setHold] = useState(5)
  const [left, setLeft] = useState(appConfig.hypoTiers.recheckMinutes * 60)
  const [feel, setFeel] = useState<'better' | 'same' | 'worse' | null>(null)
  const [asking, setAsking] = useState(false)
  const reading = tier === 1 ? '3.6' : '2.8'

  useEffect(() => {
    const t = setInterval(() => {
      setHold((h) => Math.max(0, h - 1))
      setLeft((l) => Math.max(0, l - 1))
    }, 1000)
    return () => clearInterval(t)
  }, [])
  const mm = String(Math.floor(left / 60)).padStart(2, '0')
  const ss = String(left % 60).padStart(2, '0')
  const due = left === 0

  const finish = () => {
    setRecheck(Date.now() + appConfig.hypoTiers.recheckMinutes * 60_000)
    setAsking(true)
  }

  if (asking) return <Awareness onDone={() => go('B1', { replace: true })} />

  return (
    <Screen tone={tier === 2 ? 'urgent' : 'canvas'}>
      <div role="alert" className="flex flex-col gap-4 pt-4">
        <span className={`flex h-16 w-16 items-center justify-center rounded-full ${tier === 2 ? 'bg-danger text-card' : 'bg-warn-soft text-warn'}`}>
          <WarningCircle size={40} weight="fill" aria-hidden />
        </span>
        <StatusPill tone={tier === 2 ? 'danger' : 'warn'}>{tier === 2 ? 'Very low' : 'Low'}</StatusPill>
        <h1 className="font-serif text-xl font-medium leading-tight tracking-tight text-ink">
          {tier === 2 ? (
            <>
              Your glucose reading is very low: <span className="num">{reading}</span> mmol/L. Get help now.
            </>
          ) : (
            <>
              Your glucose is low: <span className="num">{reading}</span> mmol/L. Treat it now.
            </>
          )}
        </h1>
      </div>

      <Card className={tier === 2 ? 'border-danger/40' : 'border-warn/40'}>
        <p className="text-body">
          {tier === 2
            ? "If you can, follow the first steps in your doctor's low-sugar plan while you wait for help. Do not be alone."
            : "Take the fast-acting sugar listed in your doctor's low-sugar plan, then sit down and rest."}
        </p>
        <p className="mt-1 text-sub text-ink3">The wording of the plan will show here once your doctor adds it.</p>
      </Card>

      {tier === 2 && (
        <div className="flex flex-col gap-3">
          <a href={`tel:${appConfig.emergencyNumber}`} className="press flex min-h-16 items-center justify-center gap-2 rounded-[14px] bg-danger px-4 text-body font-bold text-card">
            <Phone size={24} aria-hidden /> Call {appConfig.emergencyNumber}
          </a>
          <Button variant="secondary" icon={Phone} className="!min-h-16" onClick={() => undefined}>
            Call my clinic
          </Button>
        </div>
      )}

      {tier === 2 && (
        <Card className="flex flex-col gap-2">
          <p className="flex items-center gap-2 text-sub font-bold text-ink2">
            <ShieldCheck size={20} aria-hidden /> Emergency contact
          </p>
          {contact?.consent ? (
            <>
              <p className="text-body">
                <b>{contact.name}</b> ({contact.relation.toLowerCase()}) was alerted by {contact.channels.filter((c) => c !== 'call').join(' and ')} at {clock(appConfig.demo.nowMinutes)}.
              </p>
              {contact.channels.includes('call') && <p className="text-sub text-ink2">If there is no reply in {appConfig.hypoTiers.contactCallAfterMinutes} minutes, we will call them.</p>}
              <StatusPill tone="ok" icon={CheckCircle}>
                Alert sent
              </StatusPill>
            </>
          ) : (
            <Alert tone="info">
              No emergency contact is set up.{' '}
              <TextLink onClick={() => go('K9')} className="!min-h-0">
                Add one
              </TextLink>
            </Alert>
          )}
        </Card>
      )}

      <Card className="flex items-center gap-3">
        <Timer size={26} className="flex-none text-ink2" aria-hidden />
        <div>
          <p className="text-body font-bold">Recheck in {appConfig.hypoTiers.recheckMinutes} minutes</p>
          <p className="num text-h2">
            {mm}:{ss}
          </p>
        </div>
      </Card>

      {tier === 1 && due && (
        <Card tone="soft" className="flex flex-col gap-3">
          <p className="text-body font-bold">Time to check in. How do you feel now?</p>
          <div className="flex flex-wrap gap-2" role="radiogroup" aria-label="How you feel">
            {([['better', 'Better'], ['same', 'About the same'], ['worse', 'Worse']] as const).map(([k, l]) => (
              <Chip key={k} on={feel === k} onClick={() => setFeel(k)}>
                {l}
              </Chip>
            ))}
          </div>
          <Button onClick={() => go('E3')}>Log a reading</Button>
          {(feel === 'same' || feel === 'worse') && (
            <Alert tone="danger">Not improving. We are moving to the very low steps.</Alert>
          )}
        </Card>
      )}

      {tier === 1 && (
        <Button variant="secondary" onClick={() => setTier(2)}>
          I feel worse
        </Button>
      )}
      {tier === 1 && due && (feel === 'same' || feel === 'worse') && (
        <Button variant="danger" onClick={() => setTier(2)}>
          Get help now
        </Button>
      )}

      <Button variant="secondary" disabled={tier === 2 && hold > 0} onClick={finish}>
        {tier === 2 && hold > 0 ? `I'm okay now (${hold})` : "I'm okay now"}
      </Button>
      <p className="text-sub text-ink2">This screen is fixed and written by people. No AI is involved.</p>
    </Screen>
  )
}

/** One question after a low, so the doctor sees whether lows are felt before the sensor alerts. */
function Awareness({ onDone }: { onDone: () => void }) {
  const [saving, setSaving] = useState(false)
  const toast = useUi((s) => s.showToast)
  const save = async (a: 'felt_first' | 'sensor_first' | 'not_sure') => {
    setSaving(true)
    await api.recordAwareness(a)
    toast('Thanks. Added to your doctor brief.')
    onDone()
  }
  return (
    <Screen>
      <div className="flex flex-col gap-4 pt-6">
        <h1 className="font-serif text-h1 font-medium tracking-tight">One quick question</h1>
        <p className="text-body">Did you feel it coming before your sensor alerted you?</p>
        <div className="flex flex-col gap-2">
          <Button disabled={saving} onClick={() => void save('felt_first')}>
            Yes, I felt it first
          </Button>
          <Button variant="secondary" disabled={saving} onClick={() => void save('sensor_first')}>
            No, the sensor told me first
          </Button>
          <Button variant="secondary" disabled={saving} onClick={() => void save('not_sure')}>
            Not sure
          </Button>
          <TextLink onClick={onDone} className="self-center">
            Skip
          </TextLink>
        </div>
        <p className="text-sub text-ink3">This helps your doctor see how well you sense lows. It is not a diagnosis.</p>
      </div>
    </Screen>
  )
}
