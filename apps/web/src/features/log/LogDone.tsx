/**
 * E6 — Saved confirmation screen.
 *
 * Reads `lastLog` from the UI store (set by useFinishLog). Shows what was
 * saved, where it landed, any flag or swap, and buttons to see the day or
 * insights. If urgent, shows a "Get help now" button.
 */
import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useGo } from '@/app/navigation'
import { href } from '@/app/routeIds'
import { useUi } from '@/state/store'
import { Screen } from '@/ui/layout'
import { Alert, Button, Card, SectionTitle, TextLink } from '@/ui/primitives'
import { CheckCircle, Info } from '@/ui/icons'

const relatedLabel: Record<string, string> = {
  C2: 'See your glucose insights',
  C3: 'See your food insights',
  C4: 'See your activity',
  C5: 'See your sleep and stress',
}

export function LogDone() {
  const last = useUi((s) => s.lastLog)
  const go = useGo()
  const navigate = useNavigate()
  useEffect(() => {
    if (!last) navigate(href('E1'), { replace: true })
  }, [last, navigate])
  if (!last) return null
  const tone = last.flag?.level === 'in_range' ? 'ok' : last.flag?.level === 'info' ? 'warn' : 'warn'
  return (
    <Screen>
      <div className="h-2" aria-hidden />
      <div className="flex flex-col items-center gap-3 pb-1 pt-6 text-center">
        <span className="flex h-16 w-16 items-center justify-center rounded-full bg-ok-soft text-ok">
          <CheckCircle size={38} weight="regular" aria-hidden />
        </span>
        <h1 className="font-serif text-h1 font-medium tracking-tight">{last.title}</h1>
        <p className="text-body text-ink2">{last.detail}</p>
      </div>
      <Card className="flex flex-col gap-3">
        <div>
          <p className="text-sub text-ink3">Added to</p>
          <p className="text-body font-bold">{last.landedIn}</p>
        </div>
        {last.lines.map((l) => (
          <p key={l} className="text-body">
            {l}
          </p>
        ))}
        {last.flag && (
          <Alert tone={tone as 'ok' | 'warn'} icon={last.flag.level === 'in_range' ? CheckCircle : Info}>
            {last.flag.text}
          </Alert>
        )}
      </Card>
      {last.swap && (
        <Card tone="soft" className="flex flex-col gap-1">
          <SectionTitle>A swap to consider</SectionTitle>
          <p className="text-body">{last.swap.text}</p>
          <p className="text-sub text-ink3">{last.swap.source}</p>
        </Card>
      )}
      <div className="flex flex-col gap-2">
        <Button onClick={() => go('D1', { params: { date: last.day } })}>See your day</Button>
        <Button variant="secondary" onClick={() => go(last.related)}>
          {relatedLabel[last.related] ?? 'See insights'}
        </Button>
        {last.urgent && (
          <Button variant="danger" onClick={() => go('J1')}>
            Get help now
          </Button>
        )}
        <TextLink onClick={() => go('B1')} className="self-center">
          Done
        </TextLink>
      </div>
    </Screen>
  )
}
