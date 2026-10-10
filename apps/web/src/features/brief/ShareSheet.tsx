import { Sheet } from '@/ui/Sheet'
import { Button } from '@/ui/primitives'

/** L2: placeholder until it is built. The registration in src/app/sheetRegistry.tsx is already in place; replace this file's contents. */
export function ShareSheet({ onClose }: { onClose: () => void } & Record<string, unknown>) {
  return (
    <Sheet title="Share with my doctor" onClose={onClose}>
      <div className="flex flex-col gap-4">
        <p className="text-body text-ink2">This is not built yet.</p>
        <Button onClick={onClose}>Close</Button>
      </div>
    </Sheet>
  )
}
