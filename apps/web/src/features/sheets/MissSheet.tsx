import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import type { MissAnswer } from '@/data/types'
import { useDoses, useMissReason } from '@/data/hooks'
import { useGo } from '@/app/navigation'
import { useUi } from '@/state/store'
import { Sheet } from '@/ui/Sheet'
import { Alert, Button, Chip, Field } from '@/ui/primitives'

/**
 * H7 — Why was it not confirmed? One tap, no blame: a missed dose is information for the doctor, not a failure.
 * Opened from Home ("Tell us why") with the dose's id. Saving a reason makes the dose missed (or taken, for "I took it"), stores the
 * optional note for the doctor brief, and "Side effects" also adds a question to the doctor-question list.
 */
export function MissSheet({ onClose, doseId }: { onClose: () => void; doseId?: string }) {
  const { t } = useTranslation()
  const answers: { id: MissAnswer; label: string }[] = [
    { id: 'took_it', label: t('log.miss.tookIt', 'I took it, forgot to log') },
    { id: 'forgot', label: t('log.miss.forgot', 'I forgot') },
    { id: 'side_effects', label: t('log.miss.sideEffects', 'Side effects') },
    { id: 'ran_out', label: t('log.miss.ranOut', 'I ran out') },
    { id: 'felt_fine', label: t('log.miss.feltFine', 'I felt fine') },
    { id: 'cost', label: t('log.miss.cost', 'Cost') },
    { id: 'away_from_home', label: t('log.miss.away', 'Away from home') },
    { id: 'other', label: t('log.miss.other', 'Something else') },
  ]
  const [reason, setReason] = useState<MissAnswer | null>(null)
  const [note, setNote] = useState('')
  const save = useMissReason()
  const { data } = useDoses()
  const go = useGo()
  const toast = useUi((s) => s.showToast)
  const dose = data?.unconfirmed.find((d) => d.id === doseId)

  return (
    <Sheet title={t('log.miss.title', 'Why was it not confirmed?')} onClose={onClose} label={dose ? t('log.miss.labelDose', 'Why was {{when}} not confirmed?', { when: dose.whenLabel.toLowerCase() }) : t('log.miss.label', 'Why was this dose not confirmed?')}>
      <div className="flex flex-col gap-4">
        <p className="text-body text-ink2">{dose ? t('log.miss.doseLine', '{{when}}: {{title}}. ', { when: dose.whenLabel, title: dose.title }) : ''}{t('log.miss.helps', 'Your answer helps your doctor see what gets in the way.')}</p>
        <div className="flex flex-wrap gap-2" role="radiogroup" aria-label={t('log.miss.reason', 'Reason')}>
          {answers.map((r) => (
            <Chip key={r.id} on={reason === r.id} onClick={() => setReason(r.id)}>
              {r.label}
            </Chip>
          ))}
        </div>
        {reason === 'side_effects' && (
          <Alert tone="info">
            <p>{t('log.miss.noteDoctor', 'Want to note this for your doctor?')}</p>
            <div className="mt-2 flex flex-wrap gap-2">
              <Button size="md" variant="secondary" className="!w-auto" onClick={() => { onClose(); go('E4') }}>
                {t('log.miss.addSymptom', 'Add a symptom')}
              </Button>
            </div>
            <p className="mt-2 text-sub text-ink2">{t('log.miss.questionAdded', 'A question will also be added to your list when you save.')}</p>
          </Alert>
        )}
        <Field label={t('log.miss.note', 'Add a note (optional)')} value={note} onChange={setNote} placeholder={t('log.miss.notePh', 'Anything your doctor should know')} multiline />
        {save.isError && <Alert tone="warn">{save.error instanceof Error ? save.error.message : t('log.miss.saveError', 'We could not save that. Please try again.')}</Alert>}
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
                  toast(reason === 'took_it' ? t('log.miss.thanksTaken', 'Thanks. Marked as taken.') : t('log.miss.thanksBrief', 'Thanks. Added to your doctor brief.'))
                },
              },
            )
          }
        >
          {save.isPending ? t('log.miss.saving', 'Saving…') : t('log.miss.save', 'Save')}
        </Button>
        <Button variant="ghost" onClick={onClose}>
          {t('log.miss.skip', 'Skip for now')}
        </Button>
      </div>
    </Sheet>
  )
}
