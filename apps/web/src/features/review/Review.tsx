/**
 * K11, "Review suggestions": for the care team and reviewers. One suggestion at a time, rated reasonable, not reasonable or unsafe.
 * The score at the top compares the share judged reasonable with the 85% target and counts unsafe ratings (which must be none).
 * The suggestions are computed from the person's own logged dishes, or from the shared sample dishes. Nothing here changes a
 * suggestion or the person's record; a rating is only kept for the score.
 */
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Header, Screen } from '@/ui/layout'
import { Segmented } from '@/ui/controls'
import { Alert, Button, Card, EmptyState, Skeleton, StatusPill } from '@/ui/primitives'
import { ArrowLeft, ArrowRight, CheckCircle, ForkKnife, Info, WarningCircle, type IconType } from '@/ui/icons'
import { useReviewQueue, useReviewScore, type QueueSource, type ReviewScore } from './api'
import { SuggestionCard } from './SuggestionCard'

function ScoreCard({ score, isError }: { score: ReviewScore | undefined; isError: boolean }) {
  const { t } = useTranslation()
  if (isError) return <Alert tone="warn">{t('review.score.loadError', 'We could not load the review score just now.')}</Alert>
  if (!score) return <Skeleton className="h-36" />

  const target = Math.round(score.target * 100)
  const pct = score.reasonableShare == null ? null : Math.round(score.reasonableShare * 100)
  const tile = (label: string, value: string | number) => (
    <div className="flex min-w-0 flex-col gap-0.5 rounded-card border border-line bg-card p-3">
      <span className="text-micro text-ink2">{label}</span>
      <span className="num text-h2 leading-tight">{value}</span>
    </div>
  )

  let pill: { tone: 'ok' | 'warn' | 'danger' | 'neutral'; icon: IconType; text: string; title: string }
  if (score.status === 'too_few') {
    pill = {
      tone: 'neutral',
      icon: Info,
      title: t('review.score.tooFewTitle', 'Too few ratings'),
      text: t('review.score.tooFew', 'Rate at least {{min}} suggestions to see a result. You have rated {{rated}} so far.', { min: score.minRatings, rated: score.rated }),
    }
  } else if (score.status === 'met') {
    pill = {
      tone: 'ok',
      icon: CheckCircle,
      title: t('review.score.metTitle', 'Target met'),
      text: t('review.score.met', '{{pct}}% judged reasonable. The aim is {{target}}% or more, with no unsafe ratings.', { pct, target }),
    }
  } else if (score.unsafe > 0) {
    pill = {
      tone: 'danger',
      icon: WarningCircle,
      title: t('review.score.notMetTitle', 'Target not met'),
      text:
        score.unsafe === 1
          ? t('review.score.unsafeOne', '{{n}} suggestion is rated unsafe. The aim is none.', { n: score.unsafe })
          : t('review.score.unsafeMany', '{{n}} suggestions are rated unsafe. The aim is none.', { n: score.unsafe }),
    }
  } else {
    pill = {
      tone: 'warn',
      icon: WarningCircle,
      title: t('review.score.notMetTitle', 'Target not met'),
      text: t('review.score.notMet', '{{pct}}% judged reasonable. The aim is {{target}}% or more.', { pct, target }),
    }
  }

  return (
    <Card tone="hero" as="section" className="flex flex-col gap-3" aria-label={t('review.score.aria', 'Review score')}>
      <div className="flex flex-col items-start gap-2">
        <h2 className="text-sub font-bold text-ink2">{t('review.score.title', 'Review score')}</h2>
        <StatusPill tone={pill.tone} icon={pill.icon}>
          {pill.title}
        </StatusPill>
        <p className="text-body text-ink">{pill.text}</p>
      </div>
      <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
        {tile(t('review.score.reasonable', 'Reasonable'), score.counts.reasonable)}
        {tile(t('review.score.notReasonable', 'Not reasonable'), score.counts.notReasonable)}
        {tile(t('review.score.unsafe', 'Unsafe'), score.unsafe)}
        {tile(t('review.score.target', 'Target'), `${target}%`)}
      </div>
      <p className="text-micro text-ink3">
        {t('review.score.ratingsSoFar', 'Ratings so far: {{n}}. The target and the count of {{min}} are placeholders pending review.', { n: score.rated, min: score.minRatings })}
      </p>
    </Card>
  )
}

export function Review() {
  const [source, setSource] = useState<QueueSource>('mine')
  const [index, setIndex] = useState(0)
  const queue = useReviewQueue(source)
  const score = useReviewScore()
  const { t } = useTranslation()

  const items = queue.data?.items ?? []
  const i = Math.min(index, Math.max(items.length - 1, 0))
  const current = items[i]
  const SOURCE_NOTE: Record<QueueSource, string> = {
    mine: t('review.sourceMine', 'Dishes you have logged more than once, with a lighter swap from the Singapore food database.'),
    sample: t('review.sourceSample', 'Typical hawker dishes at their published serving. Not anyone’s logged meals.'),
  }

  function switchTo(next: QueueSource) {
    setSource(next)
    setIndex(0)
  }

  return (
    <Screen>
      <Header title={t('review.title', 'Review suggestions')} back backTo="K1" />
      <p className="text-body text-ink2">
        {t(
          'review.intro',
          'Each card shows a dish the app suggested as a lighter swap, with the numbers behind it. Say whether the swap is reasonable. Your ratings feed the review score.',
        )}
      </p>

      <ScoreCard score={score.data} isError={score.isError} />

      <Segmented
        label={t('review.whichDishes', 'Which dishes to review')}
        value={source}
        onChange={switchTo}
        options={[
          { value: 'mine', label: t('review.myDishes', 'My dishes') },
          { value: 'sample', label: t('review.sampleDishes', 'Sample dishes') },
        ]}
      />
      <p className="-mt-2 text-sub text-ink2">{SOURCE_NOTE[source]}</p>

      {queue.isLoading && (
        <Card className="flex flex-col gap-3" aria-live="polite">
          <p className="text-body text-ink">{t('review.loading', 'Looking at the dishes and checking lighter swaps. This can take up to a minute.')}</p>
          <Skeleton className="h-56" />
        </Card>
      )}

      {queue.isError && <Alert tone="warn">{t('review.queueError', 'We could not load the suggestions just now. Please try again in a moment.')}</Alert>}

      {queue.data && items.length === 0 && (
        <EmptyState
          icon={ForkKnife}
          action={
            queue.data.sampleOffered ? (
              <Button variant="secondary" size="md" onClick={() => switchTo('sample')}>
                {t('review.trySample', 'Try the sample dishes')}
              </Button>
            ) : undefined
          }
        >
          {queue.data.message ?? t('review.nothingYet', 'There is nothing to review yet.')}
        </EmptyState>
      )}

      {queue.data && current && (
        <>
          <div className="flex flex-col gap-2">
            <div className="flex items-baseline justify-between gap-3">
              <p className="num text-body font-bold text-ink" aria-live="polite">
                {t('review.ratedOf', '{{rated}} of {{total}} rated', { rated: queue.data.rated, total: queue.data.total })}
              </p>
              <p className="num text-sub text-ink2">{t('review.suggestionOf', 'Suggestion {{i}} of {{n}}', { i: i + 1, n: items.length })}</p>
            </div>
            <div
              className="h-2 w-full overflow-hidden rounded-chip bg-well"
              role="progressbar"
              aria-label={t('review.ratedSoFar', 'Rated so far')}
              aria-valuemin={0}
              aria-valuemax={queue.data.total}
              aria-valuenow={queue.data.rated}
            >
              <div className="h-full rounded-chip bg-brand transition-[width] duration-300" style={{ width: `${queue.data.total ? (queue.data.rated / queue.data.total) * 100 : 0}%` }} />
            </div>
          </div>

          <SuggestionCard key={current.suggestionKey} item={current} source={source} />

          <nav aria-label={t('review.moveAria', 'Move between suggestions')} className="grid grid-cols-2 gap-3">
            <Button variant="secondary" icon={ArrowLeft} disabled={i === 0} onClick={() => setIndex(Math.max(0, i - 1))}>
              {t('review.previous', 'Previous')}
            </Button>
            <Button variant="secondary" icon={ArrowRight} disabled={i >= items.length - 1} onClick={() => setIndex(Math.min(items.length - 1, i + 1))}>
              {t('review.next', 'Next')}
            </Button>
          </nav>
        </>
      )}
    </Screen>
  )
}
