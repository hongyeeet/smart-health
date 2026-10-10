import { useState } from 'react'
import { useGo } from '@/app/navigation'
import { cn } from '@/lib/cn'
import { Button } from '@/ui/primitives'
import { Check, Warning } from '@/ui/icons'
import { useAddDoctorQuestion, type Item } from './api'

/** One message. The person's words sit on the right; Smart Health's on the left. An urgent reply says so in words and shape, not colour alone. */
export function Bubble({ item }: { item: Item }) {
  const mine = item.role === 'user'
  const urgent = item.kind === 'urgent'
  return (
    <div className={cn('flex', mine ? 'justify-end' : 'justify-start')}>
      <div
        className={cn(
          'max-w-[88%] whitespace-pre-line break-words rounded-card px-4 py-3 text-body',
          mine ? 'bg-brand text-on-brand' : urgent ? 'border-2 border-danger bg-danger-soft text-ink' : 'border border-line bg-card text-ink',
        )}
      >
        {!mine && <span className="sr-only">Smart Health says: </span>}
        {urgent && (
          <span className="mb-1 flex items-center gap-1.5 font-bold">
            <Warning size={20} weight="fill" aria-hidden /> Urgent
          </span>
        )}
        {item.text}
      </div>
    </div>
  )
}

/** Shown while the answer is on its way. Still dots when the person asks for less motion. */
export function TypingIndicator() {
  return (
    <div role="status" className="flex">
      <span className="sr-only">Smart Health is typing</span>
      <div className="flex items-center gap-1.5 rounded-card border border-line bg-card px-4 py-4" aria-hidden>
        {[0, 1, 2].map((n) => (
          <span key={n} className="h-2.5 w-2.5 rounded-full bg-ink3 motion-safe:animate-pulse" style={{ animationDelay: `${n * 180}ms` }} />
        ))}
      </div>
    </div>
  )
}

/** The buttons under a reply: open the urgent screen, or add a refused question to the doctor questions (with a toast to confirm). */
export function Actions({ item }: { item: Item }) {
  const go = useGo()
  const add = useAddDoctorQuestion()
  const [done, setDone] = useState(false)
  const actions = item.actions ?? []
  if (!actions.length) return null
  return (
    <div className="flex flex-col gap-2 md:flex-row">
      {actions.map((a) =>
        a.kind === 'open' && a.to ? (
          <Button key={a.label} size="md" variant="danger" onClick={() => go('J1')}>
            {a.label}
          </Button>
        ) : (
          <Button
            key={a.label}
            size="md"
            variant="secondary"
            icon={done ? Check : undefined}
            disabled={done || add.isPending}
            onClick={() => a.text && add.mutate(a.text, { onSuccess: () => setDone(true) })}
          >
            {done ? 'Added to your doctor questions' : a.label}
          </Button>
        ),
      )}
    </div>
  )
}
