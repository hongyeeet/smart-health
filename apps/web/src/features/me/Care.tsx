/**
 * K3. Care plan: the next visit, the checks and screenings on record, and the questions to take to the doctor.
 * Dates only, nothing here says what to do about a check. The doctor brief is one tap away (L1).
 */
import { useState } from 'react'
import { useGo } from '@/app/navigation'
import { Header, Screen } from '@/ui/layout'
import { Alert, Button, Card, EmptyState, Field, SectionTitle, Skeleton, StatusPill, TextLink } from '@/ui/primitives'
import { CalendarBlank, ChatCircleDots, Stethoscope, Trash } from '@/ui/icons'
import { useAddQuestion, useCarePlan, useRemoveQuestion, type Appointment, type DoctorQuestion } from './care/api'
import { PreventiveStatusPill } from './care/parts'

const MAX_QUESTION = 300

export function Care() {
  const go = useGo()
  const { data, isError, isLoading } = useCarePlan()
  return (
    <Screen>
      <Header title="Care plan" back backTo="K1" />

      {isError && <Alert tone="warn">We could not load your care plan just now. Please try again in a moment.</Alert>}
      {isLoading && !data && <Skeleton className="h-40" />}

      {data && (
        <>
          <NextVisit next={data.nextAppointment} suggested={data.upcoming.filter((a) => a.status === 'suggested')} />

          <section className="flex flex-col gap-2">
            <SectionTitle>Checks and screenings</SectionTitle>
            <p className="text-sub text-ink3">Based only on the dates on record.</p>
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
            <p className="text-sub text-ink2">A printable report of your readings, symptoms and medicines for your next visit.</p>
            <Button icon={Stethoscope} onClick={() => go('L1')}>
              Generate my doctor brief
            </Button>
          </Card>
        </>
      )}
    </Screen>
  )
}

function NextVisit({ next, suggested }: { next: Appointment | null; suggested: Appointment[] }) {
  const go = useGo()
  return (
    <section className="flex flex-col gap-2">
      <SectionTitle>Next visit</SectionTitle>
      <Card className="flex flex-col gap-3">
        {next ? (
          <>
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="text-body font-bold">{next.kindLabel}</span>
              <StatusPill tone="ok">Planned</StatusPill>
            </div>
            <p className="text-body text-ink">{next.scheduledLabel}</p>
            {next.location && <p className="text-sub text-ink2">{next.location}</p>}
          </>
        ) : (
          <p className="text-body text-ink2">No visit is planned yet. Plan one when you have a date.</p>
        )}
        {suggested.length > 0 && (
          <p className="text-sub text-ink2">
            Smart Health has suggested {suggested.length === 1 ? 'a visit' : `${suggested.length} visits`}. You can confirm it when you plan an appointment.
          </p>
        )}
        <Button variant="secondary" size="md" icon={CalendarBlank} onClick={() => go('K7')}>
          {next ? 'Plan another appointment' : 'Plan an appointment'}
        </Button>
      </Card>
    </section>
  )
}

function Questions({ questions }: { questions: DoctorQuestion[] }) {
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
      <SectionTitle>Questions for your doctor</SectionTitle>

      <Card className="flex flex-col gap-3">
        <Field
          label="Add a question"
          multiline
          value={text}
          onChange={setText}
          placeholder="For example: Should I change when I eat my dinner?"
          hint={`Keep it short. Up to ${MAX_QUESTION} characters.`}
          error={add.isError ? add.error.message : undefined}
        />
        <Button variant="secondary" size="md" icon={ChatCircleDots} disabled={!trimmed || add.isPending} onClick={submit}>
          {add.isPending ? 'Adding' : 'Add question'}
        </Button>
      </Card>

      {questions.length === 0 ? (
        <div className="flex flex-col gap-2 px-1">
          <EmptyState icon={ChatCircleDots}>No questions yet. Add one when you think of it, so it is ready for your visit.</EmptyState>
          <TextLink onClick={() => go('I1')}>Ask Smart Health in the chat</TextLink>
        </div>
      ) : (
        <ul className="flex flex-col gap-3">
          {questions.map((q) => (
            <li key={q.id}>
              <Card className="flex flex-col gap-2">
                <p className="text-body text-ink">{q.text}</p>
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="text-sub text-ink3">{q.originLabel}</span>
                  {q.status === 'asked' && <StatusPill tone="neutral">Asked</StatusPill>}
                </div>
                {q.canRemove &&
                  (confirmId === q.id ? (
                    <div className="flex flex-col gap-2 sm:flex-row">
                      <Button variant="danger" size="md" icon={Trash} disabled={remove.isPending} onClick={() => remove.mutate(q.id, { onSuccess: () => setConfirmId(null) })}>
                        Yes, remove it
                      </Button>
                      <Button variant="secondary" size="md" onClick={() => setConfirmId(null)}>
                        Keep it
                      </Button>
                    </div>
                  ) : (
                    <Button variant="ghost" size="md" icon={Trash} onClick={() => setConfirmId(q.id)} aria-label={`Remove question: ${q.text}`}>
                      Remove
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
