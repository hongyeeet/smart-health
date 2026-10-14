/**
 * H5 — Review interaction. The page behind the notice: where the flag came from, why it was flagged, a box for the person's own questions
 * for their doctor or pharmacist, and the sources. A back arrow at the top and a link at the bottom lead back to the medicines. Two quiet
 * links at the very end let the person put the pair on their doctor questions, or say they have checked with their doctor (which clears it).
 *
 * Everything shown comes from the server's alert (docs/specs/f5-clash.md): the reason and the sources. Left out on purpose: a severity
 * grade and "verified source" label (nothing here is clinically reviewed, rules.md 1.15), a pharmacology explanation and a "consider an
 * alternative medicine" line (medication advice, rules.md 1.1), and "do not stop your medicine" (still advice).
 */
import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useAcknowledgeClash, useAskAboutClash, useClash } from '@/data/hooks'
import { useBack, useGo } from '@/app/navigation'
import { useUi } from '@/state/store'
import { cn } from '@/lib/cn'
import { Header, Screen } from '@/ui/layout'
import { Alert, Button, Card, EmptyState, Skeleton, StatusPill, TextLink } from '@/ui/primitives'
import { ArrowLeft, CaretDown, CheckCircle } from '@/ui/icons'
import { QuestionBox } from './InteractionCard'
import { originLabel } from './pieces'
import { SourceItem, uniqueSources } from '@/features/meds/SourceLinks'

export function InteractionDetail() {
  const { t } = useTranslation()
  const { id } = useParams()
  const back = useBack('H1')
  const go = useGo()
  const { data, isError } = useClash()
  const ask = useAskAboutClash()
  const ack = useAcknowledgeClash()
  const toast = useUi((s) => s.showToast)
  const [sources, setSources] = useState(false)
  const alert = data?.alerts.find((a) => a.id === id)

  return (
    <Screen narrow>
      <Header back backTo="H1" title={t('alerts.detail.title', 'Review interaction')} />
      {isError && <Alert tone="warn">{t('alerts.detail.error', 'We could not load this alert.')}</Alert>}
      {!data && !isError && <Skeleton className="h-64" />}
      {data && !alert && (
        <EmptyState icon={CheckCircle} action={<Button variant="secondary" size="md" className="!w-auto" onClick={back}>{t('alerts.detail.backToMeds', 'Back to medications')}</Button>}>
          {t('alerts.detail.gone', 'This alert is no longer open. It may have been checked with your doctor, or one of the medicines was removed.')}
        </EmptyState>
      )}

      {alert && (
        <>
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

          <Card as="section">
            <QuestionBox alertId={alert.id} bare />
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
                <p className="text-sub text-ink3">{t('alerts.detail.sourcesNote', 'These pages have not been reviewed by a clinician for Equinox. Not medical advice.')}</p>
              </div>
            )}
          </Card>

          <div className="flex flex-col items-center gap-1 pb-4">
            <TextLink icon={ArrowLeft} onClick={() => go('H1')}>
              {t('alerts.detail.backToMeds', 'Back to medications')}
            </TextLink>
            {alert.questionAdded ? (
              <p className="flex min-h-11 items-center gap-2 text-sub font-bold text-ok">
                <CheckCircle size={20} weight="fill" aria-hidden />
                {t('alerts.detail.added', 'Added to your doctor questions')}
              </p>
            ) : (
              <TextLink onClick={() => ask.mutate(alert.id, { onSuccess: () => toast(t('alerts.q.toast', 'Added to your doctor questions')) })}>
                {ask.isPending ? t('common.saving', 'Saving…') : t('alerts.detail.addPair', 'Add this pair to my doctor questions')}
              </TextLink>
            )}
            <TextLink
              onClick={() => ack.mutate(alert.id, { onSuccess: () => back() })}
            >
              {ack.isPending ? t('common.saving', 'Saving…') : t('alerts.detail.checked', 'I have checked with my doctor')}
            </TextLink>
          </div>
        </>
      )}
    </Screen>
  )
}
