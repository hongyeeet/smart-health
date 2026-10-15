/**
 * The medicine-interaction notice (B2 and H1) and the question box the review page (H5) uses.
 */
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import type { ClashAlert } from '@/data/types'
import { useAskOwnClashQuestion } from '@/data/hooks'
import { useGo } from '@/app/navigation'
import { useUi } from '@/state/store'
import { Button } from '@/ui/primitives'
import { CheckCircle, PencilSimple, Warning } from '@/ui/icons'
import { MedPair, whenRaised } from './pieces'
import { NoticeCard } from './NoticeCard'

const MAX_QUESTION = 500
const MIN_QUESTION = 3

/** Type a question for the doctor or pharmacist about this alert. Saved, in the person's own words, to the doctor-question list. */
export function QuestionBox({ alertId, bare = false }: { alertId: string; /** inside its own card: no rule above it */ bare?: boolean }) {
  const { t } = useTranslation()
  const save = useAskOwnClashQuestion()
  const toast = useUi((s) => s.showToast)
  const [text, setText] = useState('')
  const [saved, setSaved] = useState(false)
  const ready = text.trim().length >= MIN_QUESTION
  const label = t('alerts.q.label', 'Questions for your doctor or pharmacist')
  return (
    <div className={bare ? 'flex flex-col gap-2' : 'flex flex-col gap-2 border-t border-line pt-3'}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <label htmlFor={`q-${alertId}`} className="flex items-center gap-1.5 text-sub font-bold text-ink">
          <PencilSimple size={18} aria-hidden />
          {label}
        </label>
        <span className={saved ? 'text-sub font-bold text-ok' : 'text-sub text-ink3'}>{saved ? t('alerts.q.saved', 'Saved') : t('alerts.q.draft', 'Draft')}</span>
      </div>
      <p className="text-sub text-ink2">{t('alerts.q.hint', 'Type a question or note to bring to your visit.')}</p>
      <textarea
        id={`q-${alertId}`}
        rows={3}
        maxLength={MAX_QUESTION}
        value={text}
        onChange={(e) => {
          setText(e.target.value)
          setSaved(false)
        }}
        placeholder={t('alerts.q.placeholder', 'For example: Should I take these at different times of day?')}
        className="w-full rounded-field border-[1.5px] border-line bg-card px-3.5 py-3 text-body text-ink placeholder:text-ink3 focus:border-brand focus:outline-none"
      />
      <Button
        size="md"
        disabled={!ready || save.isPending || saved}
        onClick={() =>
          save.mutate(
            { id: alertId, text: text.trim() },
            {
              onSuccess: () => {
                setSaved(true)
                toast(t('alerts.q.toast', 'Added to your doctor questions'))
              },
            },
          )
        }
      >
        {save.isPending ? t('common.saving', 'Saving…') : t('alerts.q.save', 'Save question')}
      </Button>
      {save.isError && <p className="text-sub text-ink2">{t('alerts.q.error', 'We could not save your question just now. Please try again.')}</p>}
    </div>
  )
}

/**
 * The clash notice, on the alerts page (B2) and on the Meds page (H1): the same clean card for both. The pair, the fixed sentence from the
 * server, and one link, "Review interaction", to the page with the details (H5). The other things a person can do with an alert (ask a
 * question, say they have checked with their doctor) are on that page.
 */
export function InteractionCard({ alert }: { alert: ClashAlert }) {
  const { t } = useTranslation()
  const go = useGo()
  const when = whenRaised(alert.raisedAt, t('common.today', 'Today'), t('common.yesterday', 'Yesterday'))
  return (
    <NoticeCard
      tone="warn"
      icon={Warning}
      tag={t('alerts.card.tag', 'Medication review')}
      when={when}
      title={t('alerts.card.title', 'Possible medicine interaction')}
      link={t('alerts.card.review', 'Review interaction')}
      onLink={() => go('H5', { params: { id: alert.id } })}
    >
      <MedPair alert={alert} />
      <p className="text-body text-ink">{alert.text}</p>
      {alert.questionAdded && (
        <p className="flex items-center gap-2 text-sub font-bold text-ok">
          <CheckCircle size={20} weight="fill" aria-hidden />
          {t('alerts.card.onList', 'This pair is on your doctor questions')}
        </p>
      )}
    </NoticeCard>
  )
}
