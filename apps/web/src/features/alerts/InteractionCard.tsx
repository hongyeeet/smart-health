/**
 * One medicine-interaction alert on the alerts page (B2): the pair, the fixed sentence from the server, the "not advice"
 * note, and the actions from Damien's design: review it, contact the clinic, ask a question, or set it aside for now.
 */
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import type { ClashAlert } from '@/data/types'
import { useAskAboutClash, useAskOwnClashQuestion } from '@/data/hooks'
import { useGo } from '@/app/navigation'
import { useUi } from '@/state/store'
import { Alert, Button, StatusPill, TextLink } from '@/ui/primitives'
import { CaretRight, CheckCircle, PencilSimple, Phone, Question, Warning } from '@/ui/icons'
import { MedPair, NotAdviceNote, useDismissed, whenRaised } from './pieces'

const MAX_QUESTION = 500
const MIN_QUESTION = 3

/** What "Contact clinic" opens. Smart Health holds no clinic number yet, so it says so rather than showing a made-up one. */
export function ClinicNote() {
  const { t } = useTranslation()
  return <Alert tone="info" icon={Phone}>{t('alerts.clinic.note', 'Smart Health does not have your clinic or pharmacy number yet. Use the number on your appointment card or on your medicine label.')}</Alert>
}

/** Type a question for the doctor or pharmacist about this alert. Saved, in the person's own words, to the doctor-question list. */
export function QuestionBox({ alertId }: { alertId: string }) {
  const { t } = useTranslation()
  const save = useAskOwnClashQuestion()
  const toast = useUi((s) => s.showToast)
  const [text, setText] = useState('')
  const [saved, setSaved] = useState(false)
  const ready = text.trim().length >= MIN_QUESTION
  const label = t('alerts.q.label', 'Questions for your doctor or pharmacist')
  return (
    <div className="flex flex-col gap-2 border-t border-line pt-3">
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

/** Set an alert aside for now. It also saves the ready-made doctor question, so the pair is on the list for the next visit. */
export function useDismissAlert() {
  const { t } = useTranslation()
  const ask = useAskAboutClash()
  const dismiss = useDismissed((s) => s.dismiss)
  const toast = useUi((s) => s.showToast)
  return (alert: ClashAlert) => {
    if (!alert.questionAdded) ask.mutate(alert.id)
    dismiss(alert.id)
    toast(t('alerts.dismissed', 'Set aside. Added to your doctor questions'))
  }
}

export function InteractionCard({ alert }: { alert: ClashAlert }) {
  const { t } = useTranslation()
  const go = useGo()
  const dismiss = useDismissAlert()
  const [panel, setPanel] = useState<'clinic' | 'question' | null>(null)
  const when = whenRaised(alert.raisedAt, t('common.today', 'Today'), t('common.yesterday', 'Yesterday'))

  return (
    <article className="relative overflow-hidden rounded-card border border-line bg-card shadow-lift">
      <span className="absolute inset-y-0 left-0 w-1.5 bg-warn" aria-hidden />
      <div className="flex flex-col gap-3 p-4 pl-5">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <StatusPill tone="warn" icon={Warning}>
            {t('alerts.card.tag', 'Medication review')}
          </StatusPill>
          {when && <time dateTime={alert.raisedAt ?? undefined} className="text-sub text-ink3">{when}</time>}
        </div>

        <h2 className="font-serif text-h2 font-medium tracking-tight text-ink">{t('alerts.card.title', 'Possible medicine interaction')}</h2>
        <MedPair alert={alert} />
        <p className="text-body text-ink">{alert.text}</p>
        <NotAdviceNote />

        <div className="flex flex-col gap-2">
          <Button onClick={() => go('H5', { params: { id: alert.id } })}>
            <span className="inline-flex items-center gap-1.5">
              {t('alerts.card.review', 'Review interaction')}
              <CaretRight size={18} weight="bold" aria-hidden />
            </span>
          </Button>
          <div className="grid grid-cols-1 gap-2 min-[440px]:grid-cols-2">
            <Button size="md" variant="secondary" icon={Phone} aria-expanded={panel === 'clinic'} onClick={() => setPanel(panel === 'clinic' ? null : 'clinic')}>
              {t('alerts.card.clinic', 'Contact clinic')}
            </Button>
            <Button size="md" variant="secondary" icon={Question} aria-expanded={panel === 'question'} onClick={() => setPanel(panel === 'question' ? null : 'question')}>
              {t('alerts.card.ask', 'Ask a question')}
            </Button>
          </div>
          {panel === 'clinic' && <ClinicNote />}
          {panel === 'question' && <QuestionBox alertId={alert.id} />}
          {alert.questionAdded && (
            <p className="flex items-center gap-2 text-sub font-bold text-ok">
              <CheckCircle size={20} weight="fill" aria-hidden />
              {t('alerts.card.onList', 'This pair is on your doctor questions')}
            </p>
          )}
          <TextLink onClick={() => dismiss(alert)} className="self-start text-left">
            {t('alerts.card.dismiss', 'Dismiss for now and add to my doctor questions')}
          </TextLink>
        </div>
      </div>
    </article>
  )
}
