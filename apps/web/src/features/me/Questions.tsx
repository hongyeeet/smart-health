/**
 * K12. Questions for your doctor: add a question, mark it done or not done, or remove it. Open questions come first, then the done ones.
 * Each question shows where it came from (the stored origin). The open ones also go into the doctor brief (L1).
 */
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Header, Screen } from '@/ui/layout'
import { Alert, Button, Card, EmptyState, Field, Skeleton, StatusPill } from '@/ui/primitives'
import { ArrowCounterClockwise, Check, ChatCircleDots, CheckCircle, Trash } from '@/ui/icons'
import { useAddQuestion, useCarePlan, useRemoveQuestion, useSetQuestionDone, type DoctorQuestion } from './care/api'

const MAX_QUESTION = 300

export function Questions() {
  const { t } = useTranslation()
  const { data, isError, isLoading } = useCarePlan()
  return (
    <Screen>
      <Header title={t('me.questions.title', 'Questions for your doctor')} back backTo="K1" />

      {/* the writing box on the left and the list on the right from a laptop up; the box first in one column */}
      <div className="grid gap-4 lg:grid-cols-[minmax(0,2fr)_minmax(0,3fr)] lg:items-start lg:gap-6 [&>*]:min-w-0">
        <div className="flex flex-col gap-4">
          <p className="text-body text-ink2">
            {t('me.questions.intro', 'Write down what you want to ask at your next visit. The questions you have not done yet also go into your doctor brief.')}
          </p>
          <AddQuestion />
        </div>
        <div className="flex flex-col gap-4">
          {isError && <Alert tone="warn">{t('me.questions.loadError', 'We could not load your questions just now. Please try again in a moment.')}</Alert>}
          {isLoading && !data && <Skeleton className="h-40" />}
          {data && <QuestionList questions={data.questions} />}
        </div>
      </div>
    </Screen>
  )
}

function AddQuestion() {
  const { t } = useTranslation()
  const [text, setText] = useState('')
  const add = useAddQuestion()
  const trimmed = text.trim()

  const submit = () => {
    if (!trimmed) return
    add.mutate(trimmed, { onSuccess: () => setText('') })
  }

  return (
    <Card className="flex flex-col gap-3">
      <Field
        label={t('me.care.addQuestion', 'Add a question')}
        multiline
        value={text}
        onChange={setText}
        placeholder={t('me.care.questionPlaceholder', 'For example: Should I change when I eat my dinner?')}
        hint={t('me.care.questionHint', 'Keep it short. Up to {{max}} characters.', { max: MAX_QUESTION })}
        error={add.isError ? add.error.message : undefined}
      />
      <Button variant="secondary" size="md" icon={ChatCircleDots} disabled={!trimmed || add.isPending} onClick={submit}>
        {add.isPending ? t('me.care.adding', 'Adding') : t('me.care.addButton', 'Add question')}
      </Button>
    </Card>
  )
}

function QuestionList({ questions }: { questions: DoctorQuestion[] }) {
  const { t } = useTranslation()
  if (questions.length === 0) {
    return <EmptyState icon={ChatCircleDots}>{t('me.questions.empty', 'No questions yet. Add one when you think of it, so it is ready for your visit.')}</EmptyState>
  }
  return (
    <ul className="flex flex-col gap-3" aria-label={t('me.questions.listLabel', 'Your questions')}>
      {questions.map((q) => (
        <li key={q.id}>
          <QuestionCard q={q} />
        </li>
      ))}
    </ul>
  )
}

function QuestionCard({ q }: { q: DoctorQuestion }) {
  const { t } = useTranslation()
  const [confirming, setConfirming] = useState(false)
  const setDone = useSetQuestionDone()
  const remove = useRemoveQuestion()
  const done = q.status === 'asked'
  const busy = setDone.isPending || remove.isPending
  const failed = setDone.isError || remove.isError

  return (
    <Card className="flex flex-col gap-3">
      <p className="text-body break-words text-ink">{q.text}</p>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="text-sub text-ink3">{q.originLabel}</span>
        {done ? (
          <StatusPill tone="ok" icon={CheckCircle}>
            {t('me.questions.done', 'Done')}
          </StatusPill>
        ) : (
          <StatusPill tone="neutral">{t('me.questions.toAsk', 'To ask')}</StatusPill>
        )}
      </div>

      {failed && <Alert tone="danger">{t('me.questions.actionError', 'That did not save. Please try again.')}</Alert>}

      <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap">
        <Button
          variant="secondary"
          size="md"
          className="sm:!w-auto"
          icon={done ? ArrowCounterClockwise : Check}
          disabled={busy}
          onClick={() => setDone.mutate({ id: q.id, done: !done })}
        >
          {done ? t('me.questions.notDone', 'Not done yet') : t('me.questions.markDone', 'Mark as done')}
        </Button>

        {confirming ? (
          <>
            <Button variant="danger" size="md" className="sm:!w-auto" icon={Trash} disabled={busy} onClick={() => remove.mutate(q.id, { onSuccess: () => setConfirming(false) })}>
              {t('me.care.yesRemove', 'Yes, remove it')}
            </Button>
            <Button variant="secondary" size="md" className="sm:!w-auto" onClick={() => setConfirming(false)}>
              {t('me.care.keepIt', 'Keep it')}
            </Button>
          </>
        ) : (
          q.canRemove && (
            <Button variant="ghost" size="md" className="sm:!w-auto" icon={Trash} disabled={busy} onClick={() => setConfirming(true)} aria-label={t('me.care.removeAria', 'Remove question: {{text}}', { text: q.text })}>
              {t('me.care.remove', 'Remove')}
            </Button>
          )
        )}
      </div>
    </Card>
  )
}
