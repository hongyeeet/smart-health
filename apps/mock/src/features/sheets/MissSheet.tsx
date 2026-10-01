import { useState } from 'react'
import type { MissReason } from '@/data/types'
import { useMissReason } from '@/data/hooks'
import { useGo } from '@/app/navigation'
import { useUi } from '@/state/store'
import { Sheet } from '@/ui/Sheet'
import { Alert, Button, Chip, Field } from '@/ui/primitives'

const reasons: { id: MissReason; label: string }[] = [
  { id: 'forgot', label: 'I forgot' },
  { id: 'side_effects', label: 'Side effects' },
  { id: 'ran_out', label: 'I ran out' },
  { id: 'felt_fine', label: 'I felt fine' },
  { id: 'cost', label: 'Cost' },
  { id: 'away_from_home', label: 'Away from home' },
  { id: 'other', label: 'Something else' },
]

/** One tap. No blame: a missed dose is information for the doctor, not a failure. */
export function MissSheet({ onClose, doseId = 'd-met-pm-y' }: { onClose: () => void; doseId?: string }) {
  const [reason, setReason] = useState<MissReason | null>(null)
  const [note, setNote] = useState('')
  const save = useMissReason()
  const go = useGo()
  const toast = useUi((s) => s.showToast)
  return (
    <Sheet title="Why was it not confirmed?" onClose={onClose} label="Why was yesterday's evening dose not confirmed?">
      <div className="flex flex-col gap-4">
        <p className="text-body text-ink2">Yesterday evening, Metformin 500 mg. Your answer helps your doctor see what gets in the way.</p>
        <div className="flex flex-wrap gap-2" role="radiogroup" aria-label="Reason">
          {reasons.map((r) => (
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
        <Button
          disabled={!reason}
          onClick={() =>
            reason &&
            save.mutate(
              { id: doseId, reason, note },
              {
                onSuccess: () => {
                  onClose()
                  toast('Thanks. Added to your doctor brief.')
                },
              },
            )
          }
        >
          Save
        </Button>
        <Button variant="ghost" onClick={onClose}>
          Skip for now
        </Button>
      </div>
    </Sheet>
  )
}
