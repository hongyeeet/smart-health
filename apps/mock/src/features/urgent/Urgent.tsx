import { useEffect, useState } from 'react'
import { appConfig } from '@/config/app'
import { useGo } from '@/app/navigation'
import { useUi } from '@/state/store'
import { Screen } from '@/ui/layout'
import { Button, Card } from '@/ui/primitives'
import { Phone, Timer, WarningCircle } from '@/ui/icons'

/**
 * Urgent. A fixed screen written by people: no AI, no animation, no network call.
 * "I'm okay now" stays disabled for 5 seconds so it is not tapped by reflex.
 */
export function Urgent() {
  const go = useGo()
  const setRecheck = useUi((s) => s.setRecheck)
  const [hold, setHold] = useState(5)
  const [left, setLeft] = useState(appConfig.reminderRecheckMinutes * 60)
  useEffect(() => {
    const t = setInterval(() => {
      setHold((h) => Math.max(0, h - 1))
      setLeft((l) => Math.max(0, l - 1))
    }, 1000)
    return () => clearInterval(t)
  }, [])
  const mm = String(Math.floor(left / 60)).padStart(2, '0')
  const ss = String(left % 60).padStart(2, '0')
  return (
    <Screen tone="urgent">
      <div role="alert" className="flex flex-col gap-4 pt-4">
        <span className="flex h-16 w-16 items-center justify-center rounded-full bg-danger text-card">
          <WarningCircle size={40} weight="fill" aria-hidden />
        </span>
        <h1 className="font-serif text-xl font-medium leading-tight tracking-tight text-ink">
          Your glucose reading is very low: <span className="num">2.8</span> mmol/L. Get help now.
        </h1>
      </div>
      <Card className="border-danger/40">
        <p className="text-body">Steps from your doctor's low-sugar plan will show here.</p>
      </Card>
      <div className="flex flex-col gap-3">
        <a href={`tel:${appConfig.emergencyNumber}`} className="press flex min-h-16 items-center justify-center gap-2 rounded-[14px] bg-danger px-4 text-body font-bold text-card">
          <Phone size={24} aria-hidden /> Call {appConfig.emergencyNumber}
        </a>
        <Button variant="secondary" icon={Phone} className="!min-h-16" onClick={() => undefined}>
          Call my clinic
        </Button>
      </div>
      <Card className="flex items-center gap-3">
        <Timer size={26} className="flex-none text-ink2" aria-hidden />
        <div>
          <p className="text-body font-bold">Recheck in {appConfig.reminderRecheckMinutes} minutes</p>
          <p className="num text-h2" aria-live="off">
            {mm}:{ss}
          </p>
        </div>
      </Card>
      <Button
        variant="secondary"
        disabled={hold > 0}
        onClick={() => {
          setRecheck(Date.now() + appConfig.reminderRecheckMinutes * 60_000)
          go('B1', { replace: true })
        }}
      >
        {hold > 0 ? `I'm okay now (${hold})` : "I'm okay now"}
      </Button>
      <p className="text-sub text-ink2">This screen is fixed and written by people. No AI is involved.</p>
    </Screen>
  )
}
