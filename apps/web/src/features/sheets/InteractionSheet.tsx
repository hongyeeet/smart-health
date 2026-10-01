import { useAddQuestion } from '@/data/hooks'
import { useGo } from '@/app/navigation'
import { useUi } from '@/state/store'
import { Sheet } from '@/ui/Sheet'
import { Alert, Button, StatusPill } from '@/ui/primitives'
import { Info, WarningCircle } from '@/ui/icons'

/** The wording is fixed on purpose. It never says stop, and unknown items are "not checked", never "safe". */
export function InteractionSheet({ onClose, a = 'Clarithromycin', b = 'Atorvastatin' }: { onClose: () => void; a?: string; b?: string }) {
  const go = useGo()
  const add = useAddQuestion()
  const toast = useUi((s) => s.showToast)
  return (
    <Sheet title="Possible interaction" onClose={onClose}>
      <div className="flex flex-col gap-4">
        <Alert tone="warn" icon={WarningCircle}>
          Possible interaction between <b>{a}</b> and <b>{b}</b>. Please check with your pharmacist or doctor before continuing.
        </Alert>
        <StatusPill tone="info" icon={Info}>
          Matched against reference data that has not been clinically reviewed.
        </StatusPill>
        <div className="rounded-card bg-well p-3.5">
          <p className="text-body font-bold">Herbal tonic</p>
          <p className="text-sub text-ink2">Not checked: we don't have interaction data for this item.</p>
        </div>
        <Button
          onClick={() =>
            add.mutate(
              { text: `Is it safe to take ${a} together with ${b}?`, origin: 'clash' },
              {
                onSuccess: () => {
                  onClose()
                  toast('Added to your doctor questions')
                  go('K3')
                },
              },
            )
          }
        >
          Add to my doctor questions
        </Button>
        <Button variant="ghost" onClick={onClose}>
          OK
        </Button>
      </div>
    </Sheet>
  )
}
