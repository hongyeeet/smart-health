import { useState } from 'react'
import type { MissAnswer } from '@/data/types'
import { useDoses, useMissReason } from '@/data/hooks'
import { useGo } from '@/app/navigation'
import { useUi } from '@/state/store'
import { Sheet } from '@/ui/Sheet'
import { Alert, Button, Chip, Field } from '@/ui/primitives'

const answers: { id: MissAnswer; label: string }[] = [
  { id: 'took_it', label: 'I took it, forgot to log' },
  { id: 'forgot', label: 'I forgot' },
  { id: 'side_effects', label: 'Side effects' },
  { id: 'ran_out', label: 'I ran out' },
  { id: 'felt_fine', label: 'I felt fine' },
  { id: 'cost', label: 'Cost' },
  { id: 'away_from_home', label: 'Away from home' },
  { id: 'other', label: 'Something else' },
]

/**
 * H7 — Why was it not confirmed? One tap, no blame: a missed dose is information for the doctor, not a failure.
 * Opened from Home ("Tell us why") with the dose's id. Saving a reason makes the dose missed (or taken, for "I took it"), stores the
 * optional note for the doctor brief, and "Side effects" also adds a question to the doctor-question list.
 */
export function MissSheet({ onClose, doseId }: { onClose: () => void; doseId?: string }) {
  const [reason, setReason] = useState<MissAnswer | null>(null)
  const [note, setNote] = useState('')
  const save = useMissReason()
  const { data } = useDoses()
  const go = useGo()
  const toast = useUi((s) => s.showToast)
  const dose = data?.unconfirmed.find((d) => d.id === doseId)

  return (
    <Sheet title="Why was it not confirmed?" onClose={onClose} label={dose ? `Why was ${dose.whenLabel.toLowerCase()} not confirmed?` : 'Why was this dose not confirmed?'}>
      <div className="flex flex-col gap-4">
        <p className="text-body text-ink2">{dose ? `${dose.whenLabel}: ${dose.title}. ` : ''}Your answer helps your doctor see what gets in the way.</p>
        <div className="flex flex-wrap gap-2" role="radiogroup" aria-label="Reason">
          {answers.map((r) => (
            <Chip key={r.id} on={reason === r.id} onClick={() => setReason(r.id)}>
              {r.label}
            </Chip>
          ))}
        </div>
        {reason === 'side_effects' && (
          <Alert tone="info">
            <p>Want to note this for your doctor?</p>
            <div className="mt-2 flex flex-wrap gap-2">
              <Button size="md" variant="secondary" className="!w-auto" onClick={() => { onClose(); go('E4') }}>
                Add a symptom
              </Button>
            </div>
            <p className="mt-2 text-sub text-ink2">A question will also be added to your list when you save.</p>
          </Alert>
        )}
        <Field label="Add a note (optional)" value={note} onChange={setNote} placeholder="Anything your doctor should know" multiline />
        {save.isError && <Alert tone="warn">{save.error instanceof Error ? save.error.message : 'We could not save that. Please try again.'}</Alert>}
        <Button
          disabled={!reason || !doseId || save.isPending}
          onClick={() =>
            reason &&
            doseId &&
            save.mutate(
              { id: doseId, reason, note },
              {
                onSuccess: () => {
                  onClose()
                  toast(reason === 'took_it' ? 'Thanks. Marked as taken.' : 'Thanks. Added to your doctor brief.')
                },
              },
            )
          }
        >
          {save.isPending ? 'Saving…' : 'Save'}
        </Button>
        <Button variant="ghost" onClick={onClose}>
          Skip for now
        </Button>
      </div>
    </Sheet>
  )
}
