/**
 * One suggestion to rate: the usual dish and its logged numbers, the dish suggested instead and its numbers, the change in words,
 * then the rating. Keyed by suggestion, so switching cards starts each one from its own saved rating.
 */
import { useState, type ComponentProps } from 'react'
import { useTranslation } from 'react-i18next'
import { cn } from '@/lib/cn'
import { Alert, Button, Card, Field, StatusPill } from '@/ui/primitives'
import { Check, Warning, X, type IconType } from '@/ui/icons'
import { COMMENT_MAX, useRateSuggestion, type QueueSource, type ReviewItem, type Verdict } from './api'

/** Numbers as the person logged them or as published. A missing number is a dash, never zero. */
export const fmt = (v: number | null, unit: string) => (v == null ? '–' : `${Math.round(v).toLocaleString('en-US')} ${unit}`)

function Numbers({ n }: { n: { kcal: number | null; protein: number | null; carbs: number | null; fat: number | null; salt: number | null; sugar: number | null } }) {
  const { t } = useTranslation()
  const rows: [string, string][] = [
    [t('review.num.energy', 'Energy'), fmt(n.kcal, 'kcal')],
    [t('review.num.protein', 'Protein'), fmt(n.protein, 'g')],
    [t('review.num.carbs', 'Carbs'), fmt(n.carbs, 'g')],
    [t('review.num.fat', 'Fat'), fmt(n.fat, 'g')],
    [t('review.num.salt', 'Salt'), fmt(n.salt, 'mg')],
    [t('review.num.sugar', 'Sugar'), fmt(n.sugar, 'g')],
  ]
  return (
    <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1.5 text-sub">
      {rows.map(([label, value]) => (
        <div key={label} className="contents">
          <dt className="text-ink2">{label}</dt>
          <dd className="num text-right font-bold text-ink">{value}</dd>
        </div>
      ))}
    </dl>
  )
}

function DishPanel({ kind, name, sub, n }: { kind: string; name: string; sub: string; n: ComponentProps<typeof Numbers>['n'] }) {
  return (
    <Card tone="soft" className="flex min-w-0 flex-col gap-3">
      <div className="flex flex-col gap-0.5">
        <span className="text-micro font-bold uppercase tracking-wide text-ink2">{kind}</span>
        <p className="break-words text-body font-bold text-ink">{name}</p>
        <p className="text-sub text-ink2">{sub}</p>
      </div>
      <Numbers n={n} />
    </Card>
  )
}

export function SuggestionCard({ item, source }: { item: ReviewItem; source: QueueSource }) {
  const rate = useRateSuggestion(source)
  const { t } = useTranslation()
  const saved = item.myRating
  const [verdict, setVerdict] = useState<Verdict | null>(saved?.verdict ?? null)
  const [comment, setComment] = useState(saved?.comment ?? '')
  const [problem, setProblem] = useState<string | null>(null)

  const VERDICT_WORDS: Record<Verdict, string> = {
    reasonable: t('review.verdict.reasonable', 'Reasonable'),
    not_reasonable: t('review.verdict.notReasonable', 'Not reasonable'),
    unsafe: t('review.verdict.unsafe', 'Unsafe'),
  }
  const VERDICTS: { value: Verdict; icon: IconType; hint: string }[] = [
    { value: 'reasonable', icon: Check, hint: t('review.verdict.reasonableHint', 'A sensible swap for this dish') },
    { value: 'not_reasonable', icon: X, hint: t('review.verdict.notReasonableHint', 'Not a sensible swap') },
    { value: 'unsafe', icon: Warning, hint: t('review.verdict.unsafeHint', 'Could harm someone with type 2 diabetes') },
  ]

  const trimmed = comment.trim()
  const unsafe = verdict === 'unsafe'
  const changed = verdict !== (saved?.verdict ?? null) || trimmed !== (saved?.comment ?? '')
  const showSaved = !!saved && !changed && rate.isSuccess

  function save() {
    if (!verdict) return setProblem(t('review.problemChoose', 'Choose Reasonable, Not reasonable or Unsafe first.'))
    if (unsafe && !trimmed) return setProblem(t('review.problemUnsafe', 'Unsafe needs a comment. Say what could harm someone.'))
    setProblem(null)
    rate.mutate(
      { suggestionKey: item.suggestionKey, verdict, comment: trimmed || null },
      { onError: (e) => setProblem(e instanceof Error ? e.message : t('review.saveFailed', 'The rating was not saved. Please try again.')) },
    )
  }

  const usual = item.usual
  const sugg = item.suggested
  return (
    <Card as="section" className="flex flex-col gap-4 md:p-5" aria-label={t('review.card.aria', 'Suggestion to rate')}>
      <div className="grid gap-3 md:grid-cols-2">
        <DishPanel
          kind={t('review.card.usual', 'Your usual dish')}
          name={usual.name}
          sub={
            usual.timesLogged == null
              ? t('review.card.usualSample', 'Typical serving (sample set, not logged by anyone)')
              : t('review.card.usualLogged', 'Logged {{n}} times. These are the average numbers.', { n: usual.timesLogged })
          }
          n={{ kcal: usual.kcal, protein: usual.proteinG, carbs: usual.carbsG, fat: usual.fatG, salt: usual.sodiumMg, sugar: usual.sugarG }}
        />
        <DishPanel
          kind={t('review.card.suggested', 'Suggested instead')}
          name={sugg.name}
          sub={sugg.serving ? t('review.card.serving', 'Serving: {{serving}}', { serving: sugg.serving }) : t('review.card.servingUnknown', 'Serving not known')}
          n={{ kcal: sugg.kcal, protein: sugg.proteinG, carbs: sugg.carbsG, fat: sugg.fatG, salt: sugg.sodiumMg, sugar: sugg.sugarG }}
        />
      </div>

      <div className="flex flex-col gap-1">
        <h2 className="text-sub font-bold text-ink2">{t('review.card.whatChanges', 'What changes')}</h2>
        <p className="text-body text-ink">{item.change}</p>
        <p className="text-micro text-ink3">{t('review.card.workedOut', 'Worked out from the numbers above. Not a health claim.')}</p>
      </div>

      <div className="flex flex-col gap-2">
        <h2 className="text-sub font-bold text-ink2">{t('review.card.yourRating', 'Your rating')}</h2>
        {saved && !changed && (
          <StatusPill tone={saved.verdict === 'unsafe' ? 'danger' : saved.verdict === 'reasonable' ? 'ok' : 'warn'} icon={VERDICTS.find((v) => v.value === saved.verdict)?.icon}>
            {t('review.card.youRated', 'You rated this: {{word}}', { word: VERDICT_WORDS[saved.verdict] })}
          </StatusPill>
        )}
        <div role="group" aria-label={t('review.card.rateAria', 'Rate this suggestion')} className="grid gap-2 sm:grid-cols-3">
          {VERDICTS.map((v) => {
            const on = verdict === v.value
            const Icon = v.icon
            return (
              <button
                key={v.value}
                type="button"
                aria-pressed={on}
                onClick={() => {
                  setVerdict(v.value)
                  setProblem(null)
                }}
                className={cn(
                  'press flex min-h-14 flex-col items-center justify-center gap-0.5 rounded-card border-2 px-3 py-2 text-center',
                  on ? 'border-brand bg-brand-soft text-ink' : 'border-line bg-card text-ink',
                )}
              >
                <span className="flex items-center gap-2 font-bold">
                  <Icon size={22} aria-hidden />
                  {VERDICT_WORDS[v.value]}
                </span>
                <span className="text-micro text-ink2">{v.hint}</span>
              </button>
            )
          })}
        </div>

        <Field
          label={unsafe ? t('review.card.commentNeeded', 'Comment (needed for Unsafe)') : t('review.card.commentOptional', 'Comment (optional)')}
          value={comment}
          onChange={(v) => setComment(v.slice(0, COMMENT_MAX))}
          multiline
          placeholder={unsafe ? t('review.card.commentPhUnsafe', 'Say what could harm someone') : t('review.card.commentPh', 'Anything the reviewer should know')}
          hint={t('review.card.count', '{{n}} of {{max}} characters', { n: comment.length, max: COMMENT_MAX })}
        />
      </div>

      {problem && <Alert tone="warn">{problem}</Alert>}
      {showSaved && (
        <Alert tone="ok" icon={Check}>
          {t('review.card.saved', 'Saved.')}
        </Alert>
      )}

      <Button onClick={save} disabled={rate.isPending || !verdict || (!changed && !!saved)}>
        {rate.isPending ? t('review.card.saving', 'Saving...') : saved ? t('review.card.update', 'Update rating') : t('review.card.save', 'Save rating')}
      </Button>
    </Card>
  )
}
