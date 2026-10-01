import type { RecentEntry } from '@/data/types'
import { useDeleteEntry } from '@/data/hooks'
import { useGo } from '@/app/navigation'
import { useUi } from '@/state/store'
import { Sheet } from '@/ui/Sheet'
import { Button } from '@/ui/primitives'
import { PencilSimple, Trash, CalendarBlank } from '@/ui/icons'
import type { RouteId } from '@/app/routeIds'

const editRoute: Record<RecentEntry['kind'], RouteId> = { meal: 'E2', glucose: 'E3', workout: 'F1', symptom: 'E4', checkin: 'E5' }

export function EntrySheet({ onClose, entry }: { onClose: () => void; entry?: RecentEntry }) {
  const go = useGo()
  const del = useDeleteEntry()
  const toast = useUi((s) => s.showToast)
  if (!entry) return null
  return (
    <Sheet title={entry.title} onClose={onClose}>
      <div className="flex flex-col gap-3">
        <p className="text-body text-ink2">
          {entry.detail}, {entry.when}
        </p>
        <Button variant="secondary" icon={CalendarBlank} onClick={() => { onClose(); go('D1', { params: { date: entry.date } }) }}>
          See it in your day
        </Button>
        <Button variant="secondary" icon={PencilSimple} onClick={() => { onClose(); go(editRoute[entry.kind]) }}>
          Edit this entry
        </Button>
        <Button
          variant="ghost"
          icon={Trash}
          onClick={() =>
            del.mutate(entry.id, {
              onSuccess: () => {
                onClose()
                toast('Entry deleted. Edits and deletions are logged.')
              },
            })
          }
        >
          Delete this entry
        </Button>
      </div>
    </Sheet>
  )
}
