/**
 * E7 — Entry detail, edit and delete (sheet).
 *
 * Opened when tapping a recent entry, on Insights, Food (C3). Deleting is a soft delete on the server (the row stays with a
 * `deleted_at` time, and the entry leaves the timeline). A blood pressure reading can be edited here with the same form as
 * E3; the other kinds are changed by deleting them and logging them again.
 */
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import type { RecentEntry } from '@/data/types'
import { useBloodPressure, useDeleteEntry, useUpdateBloodPressure } from '@/data/hooks'
import { useGo } from '@/app/navigation'
import { useUi } from '@/state/store'
import { Sheet } from '@/ui/Sheet'
import { Alert, Button, Skeleton } from '@/ui/primitives'
import { BloodPressureForm, saveErrorText } from '@/features/log/LogBloodPressure'
import { CalendarBlank, PencilSimple, Trash } from '@/ui/icons'

export function EntrySheet({ onClose, entry }: { onClose: () => void; entry?: RecentEntry }) {
  const { t } = useTranslation()
  const go = useGo()
  const del = useDeleteEntry()
  const update = useUpdateBloodPressure()
  const toast = useUi((s) => s.showToast)
  const [editing, setEditing] = useState(false)
  const isBp = entry?.kind === 'blood_pressure'
  // the reading is fetched only once the person asks to edit it
  const reading = useBloodPressure(entry && isBp && editing ? entry.id : undefined)
  if (!entry) return null
  return (
    <Sheet title={entry.title} onClose={onClose}>
      <div className="flex flex-col gap-3">
        <p className="text-body text-ink2">
          {entry.detail}, {entry.when}
        </p>
        {isBp && !editing && (
          <Button variant="secondary" icon={PencilSimple} onClick={() => setEditing(true)}>
            {t('log.entry.edit', 'Edit this reading')}
          </Button>
        )}
        {isBp && editing &&
          (reading.isError ? (
            <Alert tone="danger">{t('log.entry.loadError', 'We could not load this reading. Please try again.')}</Alert>
          ) : !reading.data ? (
            <Skeleton className="h-64" />
          ) : (
            <BloodPressureForm
              initial={reading.data}
              submitLabel={t('log.entry.saveChanges', 'Save changes')}
              pending={update.isPending}
              error={saveErrorText(update.error, t)}
              onSave={(input) => update.mutate({ id: entry.id, input }, { onSuccess: () => { onClose(); toast(t('log.entry.updated', 'Reading updated.')) } })}
            />
          ))}
        <Button variant="secondary" icon={CalendarBlank} onClick={() => { onClose(); go('D1', { params: { date: entry.date } }) }}>
          {t('log.entry.seeDay', 'See it in your day')}
        </Button>
        <Button variant="ghost" icon={Trash} disabled={del.isPending} onClick={() => del.mutate(entry.id, { onSuccess: () => { onClose(); toast(t('log.entry.deleted', 'Entry deleted.')) } })}>
          {del.isPending ? t('log.entry.deleting', 'Deleting…') : t('log.entry.delete', 'Delete this entry')}
        </Button>
        {del.isError && <Alert tone="danger">{t('log.entry.error', 'It could not be deleted just now. Please try again.')}</Alert>}
        {!isBp && <p className="text-sub text-ink3">{t('log.entry.mistake', 'Made a mistake? Delete it and log it again.')}</p>}
      </div>
    </Sheet>
  )
}
