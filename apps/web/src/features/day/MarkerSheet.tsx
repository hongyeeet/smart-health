import { Sheet } from '@/ui/Sheet'
import { Button } from '@/ui/primitives'

/** D2: placeholder until it is built. The registration in src/app/sheetRegistry.tsx is already in place; replace this file's contents. */
export function MarkerSheet({ onClose }: { onClose: () => void } & Record<string, unknown>) {
  return (
    <Sheet title="What happened here" onClose={onClose}>
      <div className="flex flex-col gap-4">
        <p className="text-body text-ink2">This is not built yet.</p>
        <Button onClick={onClose}>Close</Button>
      </div>
    </Sheet>
  )
}
