/**
 * E7 — Entry detail and delete (sheet).
 *
 * Opened from the Log hub when tapping a recent entry. Deleting is a soft delete on the server (the row stays with a
 * `deleted_at` time, and the entry leaves the timeline). To change an entry, delete it and log it again.
 */
import { useTranslation } from 'react-i18next'
import type { RecentEntry } from '@/data/types'
import { useDeleteEntry } from '@/data/hooks'
import { useGo } from '@/app/navigation'
import { useUi } from '@/state/store'
import { Sheet } from '@/ui/Sheet'
import { Alert, Button } from '@/ui/primitives'
import { Trash, CalendarBlank } from '@/ui/icons'

export function EntrySheet({ onClose, entry }: { onClose: () => void; entry?: RecentEntry }) {
  const { t } = useTranslation()
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
          {t('log.entry.seeDay', 'See it in your day')}
        </Button>
        <Button variant="ghost" icon={Trash} disabled={del.isPending} onClick={() => del.mutate(entry.id, { onSuccess: () => { onClose(); toast(t('log.entry.deleted', 'Entry deleted.')) } })}>
          {del.isPending ? t('log.entry.deleting', 'Deleting…') : t('log.entry.delete', 'Delete this entry')}
        </Button>
        {del.isError && <Alert tone="danger">{t('log.entry.error', 'It could not be deleted just now. Please try again.')}</Alert>}
        <p className="text-sub text-ink3">{t('log.entry.mistake', 'Made a mistake? Delete it and log it again.')}</p>
      </div>
    </Sheet>
  )
}
