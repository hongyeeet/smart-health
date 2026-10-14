/**
 * K12. Questions for your doctor. On the left: the box to add a question, and under it the questions Equinox suggests (a plain list,
 * each with an Add link). On the right: the questions log, a ruled list of everything added. Remove sits at the top right of each item;
 * "Already asked" marks one done and it can be put back. Open questions come first, then the ones already asked. The open ones also go into
 * the doctor brief (L1). The suggestions are fixed starter questions that ask, never advise; one already on the list is not offered again.
 */
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Header, Screen } from '@/ui/layout'
import { Alert, Button, Card, EmptyState, Field, SectionTitle, Skeleton, TextLink } from '@/ui/primitives'
import { ArrowCounterClockwise, Check, ChatCircleDots, CheckCircle, Plus } from '@/ui/icons'
import { shortDate } from '@/lib/format'
import { useAddQuestion, useCarePlan, useRemoveQuestion, useSetQuestionDone, type DoctorQuestion } from './care/api'

const MAX_QUESTION = 300

export function Questions() {
  const { t } = useTranslation()
  const { data, isError, isLoading } = useCarePlan()
  return (
    <Screen>
      <Header title={t('me.questions.title', 'Questions for your doctor')} back backTo="K1" />

      {/* the writing box and the suggestions on the left and the log on the right from a laptop up; the box first in one column */}
      <div className="grid gap-4 lg:grid-cols-[minmax(0,2fr)_minmax(0,3fr)] lg:items-start lg:gap-8 [&>*]:min-w-0">
        <div className="flex flex-col gap-4">
          <p className="text-body text-ink2">
            {t('me.questions.introV2', 'Write down what you want to ask at your next visit. The questions you have not asked yet also go into your doctor brief.')}
          </p>
          <AddQuestion />
          <Suggestions asked={data?.questions.map((q) => q.text) ?? []} />
        </div>
        <div className="flex flex-col gap-3">
          <SectionTitle>{t('me.questions.logTitle', 'Your questions log')}</SectionTitle>
          {isError && <Alert tone="warn">{t('me.questions.loadError', 'We could not load your questions just now. Please try again in a moment.')}</Alert>}
          {isLoading && !data && <Skeleton className="h-40" />}
          {data && <QuestionLog questions={data.questions} />}
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
    add.mutate({ text: trimmed }, { onSuccess: () => setText('') })
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

/** Not boxes: a heading, then plain lines with a rule between them and an Add link at the end of each. */
function Suggestions({ asked }: { asked: string[] }) {
  const { t } = useTranslation()
  const add = useAddQuestion()
  const all: { key: string; text: string }[] = [
    { key: 'results', text: t('me.questions.s.results', 'Are my glucose and HbA1c results where they should be for me?') },
    { key: 'medicines', text: t('me.questions.s.medicines', 'Do any of my medicines need to change, and are there side effects I should watch for?') },
    { key: 'checks', text: t('me.questions.s.checks', 'Which yearly checks (eyes, feet, kidneys) am I due for?') },
    { key: 'highlow', text: t('me.questions.s.highlow', 'What should I do on a day my glucose is very high or very low?') },
    { key: 'bp', text: t('me.questions.s.bp', 'Is my blood pressure at a good level for me?') },
    { key: 'food_activity', text: t('me.questions.s.foodActivity', 'Which changes to my food or activity would help me most?') },
  ]
  const left = all.filter((s) => !asked.includes(s.text))
  if (left.length === 0) return null
  return (
    <section className="flex flex-col gap-1" aria-label={t('me.questions.suggestedTitle', 'Suggested by Equinox')}>
      <SectionTitle>{t('me.questions.suggestedTitle', 'Suggested by Equinox')}</SectionTitle>
      <p className="text-sub text-ink2">{t('me.questions.suggestedSub', 'Common things to ask. Add the ones that matter to you.')}</p>
      <ul className="divide-y divide-line border-y border-line">
        {left.map((s) => (
          <li key={s.key} className="flex items-center justify-between gap-3 py-1.5">
            <span className="min-w-0 break-words text-body">{s.text}</span>
            <TextLink icon={Plus} onClick={() => add.mutate({ text: s.text, suggestedKey: s.key })} className="flex-none">
              {t('me.questions.addSuggested', 'Add')}
            </TextLink>
          </li>
        ))}
      </ul>
      {add.isError && <Alert tone="danger">{t('me.questions.actionError', 'That did not save. Please try again.')}</Alert>}
    </section>
  )
}

function QuestionLog({ questions }: { questions: DoctorQuestion[] }) {
  const { t } = useTranslation()
  if (questions.length === 0) {
    return <EmptyState icon={ChatCircleDots}>{t('me.questions.empty', 'No questions yet. Add one when you think of it, so it is ready for your visit.')}</EmptyState>
  }
  return (
    <ul className="divide-y divide-line border-y border-line" aria-label={t('me.questions.listLabel', 'Your questions')}>
      {questions.map((q) => (
        <li key={q.id}>
          <QuestionRow q={q} />
        </li>
      ))}
    </ul>
  )
}

function QuestionRow({ q }: { q: DoctorQuestion }) {
  const { t } = useTranslation()
  const [confirming, setConfirming] = useState(false)
  const setDone = useSetQuestionDone()
  const remove = useRemoveQuestion()
  const asked = q.status === 'asked'
  const busy = setDone.isPending || remove.isPending
  const failed = setDone.isError || remove.isError

  return (
    <div className="flex flex-col gap-1 py-3">
      <div className="flex items-start justify-between gap-3">
        <p className={asked ? 'min-w-0 break-words text-body text-ink2' : 'min-w-0 break-words text-body text-ink'}>{q.text}</p>
        {q.canRemove && !confirming && (
          <TextLink onClick={() => setConfirming(true)} className="flex-none !font-normal !text-ink2">
            {t('me.care.remove', 'Remove')}
          </TextLink>
        )}
      </div>
      <p className="text-sub text-ink3">
        {q.originLabel}
        {q.createdAt ? ` · ${shortDate(q.createdAt.slice(0, 10))}` : ''}
      </p>

      {failed && <Alert tone="danger">{t('me.questions.actionError', 'That did not save. Please try again.')}</Alert>}

      {confirming ? (
        <div className="flex flex-wrap items-center gap-2 pt-1">
          <span className="text-sub text-ink2">{t('me.questions.removeAsk', 'Remove this question?')}</span>
          <Button variant="danger" size="md" className="!w-auto" disabled={busy} onClick={() => remove.mutate(q.id, { onSuccess: () => setConfirming(false) })}>
            {t('me.care.yesRemove', 'Yes, remove it')}
          </Button>
          <Button variant="secondary" size="md" className="!w-auto" onClick={() => setConfirming(false)}>
            {t('me.care.keepIt', 'Keep it')}
          </Button>
        </div>
      ) : (
        <div className="flex flex-wrap items-center gap-2">
          <Button
            variant={asked ? 'ghost' : 'secondary'}
            size="md"
            className="!w-auto"
            icon={asked ? ArrowCounterClockwise : Check}
            disabled={busy}
            onClick={() => setDone.mutate({ id: q.id, done: !asked })}
          >
            {asked ? t('me.questions.notAskedV2', 'Not asked yet') : t('me.questions.alreadyAsked', 'Already asked')}
          </Button>
          {asked && (
            <span className="inline-flex items-center gap-1 text-sub text-ink2">
              <CheckCircle size={18} aria-hidden />
              {t('me.questions.askedTag', 'Asked')}
            </span>
          )}
        </div>
      )}
    </div>
  )
}
