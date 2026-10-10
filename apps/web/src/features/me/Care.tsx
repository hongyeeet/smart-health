/**
 * K3. Care plan: the next visit, the checks and screenings on record, and the questions to take to the doctor.
 * Dates only, nothing here says what to do about a check. The doctor brief is one tap away (L1).
 */
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useGo } from '@/app/navigation'
import { Header, Screen } from '@/ui/layout'
import { Alert, Button, Card, EmptyState, Field, SectionTitle, Skeleton, StatusPill, TextLink } from '@/ui/primitives'
import { CalendarBlank, ChatCircleDots, Stethoscope, Trash } from '@/ui/icons'
import { useAddQuestion, useCarePlan, useRemoveQuestion, type Appointment, type DoctorQuestion } from './care/api'
import { PreventiveStatusPill } from './care/parts'

const MAX_QUESTION = 300

export function Care() {
  const { t } = useTranslation()
  const go = useGo()
  const { data, isError, isLoading } = useCarePlan()
  return (
    <Screen>
      <Header title={t('me.care.title', 'Care plan')} back backTo="K1" />

      {isError && <Alert tone="warn">{t('me.care.loadError', 'We could not load your care plan just now. Please try again in a moment.')}</Alert>}
      {isLoading && !data && <Skeleton className="h-40" />}

      {data && (
        <>
          <NextVisit next={data.nextAppointment} suggested={data.upcoming.filter((a) => a.status === 'suggested')} />

          <section className="flex flex-col gap-2">
            <SectionTitle>{t('me.care.checks', 'Checks and screenings')}</SectionTitle>
            <p className="text-sub text-ink3">{t('me.care.basedOnDates', 'Based only on the dates on record.')}</p>
            <ul className="flex flex-col gap-3">
              {data.preventive.map((p) => (
                <li key={p.kind}>
                  <Card className="flex flex-col gap-2">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <span className="text-body font-bold">{p.label}</span>
                      <PreventiveStatusPill status={p.status} />
                    </div>
                    <p className="text-sub text-ink2">{p.detail}</p>
                  </Card>
                </li>
              ))}
            </ul>
          </section>

          <Questions questions={data.questions} />

          <Card tone="soft" className="flex flex-col gap-3">
            <p className="text-sub text-ink2">{t('me.menu.briefSub', 'A printable report of your readings, symptoms and medicines for your next visit.')}</p>
            <Button icon={Stethoscope} onClick={() => go('L1')}>
              {t('me.care.brief', 'Generate my doctor brief')}
            </Button>
          </Card>
        </>
      )}
    </Screen>
  )
}

function NextVisit({ next, suggested }: { next: Appointment | null; suggested: Appointment[] }) {
  const { t } = useTranslation()
  const go = useGo()
  return (
    <section className="flex flex-col gap-2">
      <SectionTitle>{t('me.care.nextVisit', 'Next visit')}</SectionTitle>
      <Card className="flex flex-col gap-3">
        {next ? (
          <>
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="text-body font-bold">{next.kindLabel}</span>
              <StatusPill tone="ok">{t('me.care.planned', 'Planned')}</StatusPill>
            </div>
            <p className="text-body text-ink">{next.scheduledLabel}</p>
            {next.location && <p className="text-sub text-ink2">{next.location}</p>}
          </>
        ) : (
          <p className="text-body text-ink2">{t('me.care.noVisit', 'No visit is planned yet. Plan one when you have a date.')}</p>
        )}
        {suggested.length > 0 && (
          <p className="text-sub text-ink2">
            {suggested.length === 1
              ? t('me.care.suggestedOne', 'Smart Health has suggested a visit. You can confirm it when you plan an appointment.')
              : t('me.care.suggestedMany', 'Smart Health has suggested {{n}} visits. You can confirm it when you plan an appointment.', { n: suggested.length })}
          </p>
        )}
        <Button variant="secondary" size="md" icon={CalendarBlank} onClick={() => go('K7')}>
          {next ? t('me.care.planAnother', 'Plan another appointment') : t('me.care.planOne', 'Plan an appointment')}
        </Button>
      </Card>
    </section>
  )
}

function Questions({ questions }: { questions: DoctorQuestion[] }) {
  const { t } = useTranslation()
  const go = useGo()
  const [text, setText] = useState('')
  const [confirmId, setConfirmId] = useState<string | null>(null)
  const add = useAddQuestion()
  const remove = useRemoveQuestion()
  const trimmed = text.trim()

  const submit = () => {
    if (!trimmed) return
    add.mutate(trimmed, { onSuccess: () => setText('') })
  }

  return (
    <section className="flex flex-col gap-2">
      <SectionTitle>{t('me.care.questions', 'Questions for your doctor')}</SectionTitle>

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

      {questions.length === 0 ? (
        <div className="flex flex-col gap-2 px-1">
          <EmptyState icon={ChatCircleDots}>{t('me.care.noQuestions', 'No questions yet. Add one when you think of it, so it is ready for your visit.')}</EmptyState>
          <TextLink onClick={() => go('I1')}>{t('me.care.askInChat', 'Ask Smart Health in the chat')}</TextLink>
        </div>
      ) : (
        <ul className="flex flex-col gap-3">
          {questions.map((q) => (
            <li key={q.id}>
              <Card className="flex flex-col gap-2">
                <p className="text-body text-ink">{q.text}</p>
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="text-sub text-ink3">{q.originLabel}</span>
                  {q.status === 'asked' && <StatusPill tone="neutral">{t('me.care.asked', 'Asked')}</StatusPill>}
                </div>
                {q.canRemove &&
                  (confirmId === q.id ? (
                    <div className="flex flex-col gap-2 sm:flex-row">
                      <Button variant="danger" size="md" icon={Trash} disabled={remove.isPending} onClick={() => remove.mutate(q.id, { onSuccess: () => setConfirmId(null) })}>
                        {t('me.care.yesRemove', 'Yes, remove it')}
                      </Button>
                      <Button variant="secondary" size="md" onClick={() => setConfirmId(null)}>
                        {t('me.care.keepIt', 'Keep it')}
                      </Button>
                    </div>
                  ) : (
                    <Button variant="ghost" size="md" icon={Trash} onClick={() => setConfirmId(q.id)} aria-label={t('me.care.removeAria', 'Remove question: {{text}}', { text: q.text })}>
                      {t('me.care.remove', 'Remove')}
                    </Button>
                  ))}
              </Card>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
