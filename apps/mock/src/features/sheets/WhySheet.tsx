import { Sheet } from '@/ui/Sheet'
import { Button, StatusPill } from '@/ui/primitives'
import { Info } from '@/ui/icons'

const topics: Record<string, { title: string; how: string[]; status: string }> = {
  default: {
    title: 'Why am I seeing this?',
    how: ['We compare today with your own normal: the middle of your last 28 days.', 'A pattern is shown only after it repeats on at least 3 days.', 'We say "higher than your usual", never "normal" or "abnormal".'],
    status: 'Derived: a calculation from your own readings.',
  },
  glucose: {
    title: 'Why am I seeing this?',
    how: ['Your own normal for fasting glucose is the middle of your last 28 mornings, with the usual spread around it (6.6 to 7.2 mmol/L).', 'Your last 7 mornings were 7.1 to 7.9 mmol/L, above that band on most days for about 3 weeks.', 'This is a pattern to mention to your doctor. It is not a diagnosis.'],
    status: 'Derived: a calculation from your own readings.',
  },
  pattern: {
    title: 'Why am I seeing this?',
    how: ['We matched mornings after an evening walk with mornings after no walk and compared fasting glucose.', 'A comparison is shown only with at least 5 matched pairs.', 'The words are "associated with", never "caused by". Other things may explain it.'],
    status: 'Derived and unverified. No clinician has reviewed it.',
  },
}

export function WhySheet({ onClose, topic = 'default' }: { onClose: () => void; topic?: string }) {
  const t = topics[topic] ?? topics.default!
  return (
    <Sheet title={t.title} onClose={onClose}>
      <div className="flex flex-col gap-4">
        <ul className="flex flex-col gap-3">
          {t.how.map((h) => (
            <li key={h} className="flex gap-3 text-body">
              <span className="mt-2.5 h-1.5 w-1.5 flex-none rounded-full bg-brand" aria-hidden />
              {h}
            </li>
          ))}
        </ul>
        <StatusPill tone="info" icon={Info}>
          {t.status}
        </StatusPill>
        <p className="text-sub text-ink2">Smart Health explains, organises and reminds. It does not give medical advice.</p>
        <Button onClick={onClose}>Got it</Button>
      </div>
    </Sheet>
  )
}
