/**
 * H5 — Possible interaction. The details page behind an alert, following Damien's alert design: what was compared, where
 * the flag came from, why it was flagged, the next step, and the sources.
 *
 * Everything shown comes from the server's alert (docs/specs/f5-clash.md): the fixed sentence, the reason, the sources.
 * Left out of the design on purpose: a severity grade and "verified source" label (nothing here is clinically reviewed,
 * rules.md 1.15), a pharmacology explanation and a "consider an alternative medicine" line (medication advice, rules.md 1.1),
 * and "do not stop your medicine" (still advice). The report download waits for the doctor brief (L1).
 */
import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useAskAboutClash, useClash } from '@/data/hooks'
import { useBack } from '@/app/navigation'
import { useUi } from '@/state/store'
import { cn } from '@/lib/cn'
import { Header, Screen } from '@/ui/layout'
import { Alert, Button, Card, EmptyState, Skeleton, StatusPill, TextLink } from '@/ui/primitives'
import { ArrowLeft, CaretDown, CheckCircle, ClipboardText, Phone, ShieldCheck, Stethoscope } from '@/ui/icons'
import { ClinicNote, QuestionBox, useDismissAlert } from './InteractionCard'
import { MedPair, NotAdviceNote, originLabel, whenRaised } from './pieces'
import { SourceItem, uniqueSources } from '@/features/meds/SourceLinks'

export function InteractionDetail() {
  const { t } = useTranslation()
  const { id } = useParams()
  const back = useBack('B2')
  const { data, isError } = useClash()
  const ask = useAskAboutClash()
  const dismiss = useDismissAlert()
  const toast = useUi((s) => s.showToast)
  const [clinic, setClinic] = useState(false)
  const [sources, setSources] = useState(false)
  const alert = data?.alerts.find((a) => a.id === id)

  return (
    <Screen narrow>
      <Header
        back
        backTo="B2"
        title={t('alerts.detail.title', 'Possible interaction')}
        sub={t('alerts.detail.sub', 'A check of your medicine list flagged this for your pharmacist or doctor to look at.')}
      />
      {isError && <Alert tone="warn">{t('alerts.detail.error', 'We could not load this alert.')}</Alert>}
      {!data && !isError && <Skeleton className="h-64" />}
      {data && !alert && (
        <EmptyState icon={CheckCircle} action={<Button variant="secondary" size="md" className="!w-auto" onClick={back}>{t('alerts.detail.backToAlerts', 'Back to alerts')}</Button>}>
          {t('alerts.detail.gone', 'This alert is no longer open. It may have been checked with your doctor, or one of the medicines was removed.')}
        </EmptyState>
      )}

      {alert && (
        <>
          <div className="flex flex-wrap items-center gap-2">
            <StatusPill tone="neutral" icon={ShieldCheck}>
              {t('alerts.detail.tag', 'Medicine list check')}
            </StatusPill>
            {whenRaised(alert.raisedAt, t('common.today', 'Today'), t('common.yesterday', 'Yesterday')) && (
              <time dateTime={alert.raisedAt ?? undefined} className="text-sub text-ink3">
                {whenRaised(alert.raisedAt, t('common.today', 'Today'), t('common.yesterday', 'Yesterday'))}
              </time>
            )}
          </div>

          <NotAdviceNote />

          <Card as="section" className="flex flex-col gap-3">
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <h2 className="font-serif text-h2 font-medium tracking-tight">{t('alerts.detail.compared', 'Medicines compared')}</h2>
              <span className="text-sub text-ink3">{t('alerts.detail.two', '2 medicines')}</span>
            </div>
            <MedPair alert={alert} />
            <p className="text-body font-bold text-ink">{alert.text}</p>
          </Card>

          <Card as="section" className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <p className="text-sub text-ink3">{t('alerts.detail.originLabel', 'Where this flag came from')}</p>
              <p className="text-body font-bold">{originLabel(alert.origin, t)}</p>
            </div>
            <StatusPill tone="brass">{t('alerts.detail.unreviewed', 'Not reviewed by a clinician')}</StatusPill>
          </Card>

          <Card as="section" className="flex flex-col gap-2">
            <h2 className="font-serif text-h2 font-medium tracking-tight">{t('alerts.detail.why', 'Why this was flagged')}</h2>
            <p className="rounded-field bg-well p-3 text-body text-ink">{alert.summary || t('alerts.detail.noSummary', 'No explanation was recorded for this flag. Your pharmacist or doctor can tell you whether it matters for you.')}</p>
            {alert.sources.length === 0 && <p className="text-sub text-ink3">{t('alerts.detail.aiOnly', 'No web page was found for this. It is an AI suggestion, so please check it with your pharmacist. Not medical advice.')}</p>}
          </Card>

          <Card as="section" className="flex flex-col gap-3">
            <div className="flex items-center gap-2.5">
              <span className="flex h-10 w-10 flex-none items-center justify-center rounded-full bg-brand-soft text-brand">
                <Stethoscope size={20} aria-hidden />
              </span>
              <h2 className="font-serif text-h2 font-medium tracking-tight">{t('alerts.detail.next', 'Suggested next step')}</h2>
            </div>
            <p className="text-body text-ink2">{t('alerts.detail.nextText', 'Ask your pharmacist or doctor to review your medicines. When you next collect a prescription or see your doctor, bring your full medicine list.')}</p>
            <Button icon={Phone} aria-expanded={clinic} onClick={() => setClinic(!clinic)}>
              {t('alerts.detail.contact', 'Contact my care team')}
            </Button>
            {clinic && <ClinicNote />}
            {alert.questionAdded ? (
              <p className="flex min-h-12 items-center gap-2 text-sub font-bold text-ok">
                <CheckCircle size={22} weight="fill" aria-hidden />
                {t('alerts.detail.added', 'Added to your doctor questions')}
              </p>
            ) : (
              <Button variant="secondary" icon={ClipboardText} disabled={ask.isPending} onClick={() => ask.mutate(alert.id, { onSuccess: () => toast(t('alerts.q.toast', 'Added to your doctor questions')) })}>
                {ask.isPending ? t('common.saving', 'Saving…') : t('alerts.detail.add', 'Add to my doctor questions')}
              </Button>
            )}
            {ask.isError && <p className="text-sub text-ink2">{t('alerts.q.error', 'We could not save your question just now. Please try again.')}</p>}
            <QuestionBox alertId={alert.id} />
          </Card>

          <Card as="section" className="!p-0">
            <button type="button" aria-expanded={sources} onClick={() => setSources(!sources)} className="press flex min-h-14 w-full items-center justify-between gap-3 p-4 text-left">
              <span className="text-body font-bold">{t('alerts.detail.sources', 'Where this information comes from')}</span>
              <CaretDown size={20} className={cn('flex-none text-ink3 transition-transform', sources && 'rotate-180')} aria-hidden />
            </button>
            {sources && (
              <div className="flex flex-col gap-2 px-4 pb-4">
                {alert.sources.length > 0 ? (
                  <ul className="flex flex-col gap-1.5">
                    {uniqueSources(alert.sources).map((s) => (
                      <li key={s.title} className="text-body">
                        <SourceItem s={s} linkClass="break-words text-brand underline underline-offset-4" />
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-body text-ink2">{t('alerts.detail.noSources', 'No source page was recorded for this flag.')}</p>
                )}
                <p className="text-sub text-ink3">{t('alerts.detail.sourcesNote', 'These pages have not been reviewed by a clinician for Smart Health. Not medical advice.')}</p>
              </div>
            )}
          </Card>

          <div className="flex flex-col items-center gap-1 pb-4">
            <TextLink icon={ArrowLeft} onClick={back}>
              {t('alerts.detail.backToAlerts', 'Back to alerts')}
            </TextLink>
            <TextLink
              onClick={() => {
                dismiss(alert)
                back()
              }}
            >
              {t('alerts.card.dismiss', 'Dismiss for now and add to my doctor questions')}
            </TextLink>
          </div>
        </>
      )}
    </Screen>
  )
}
