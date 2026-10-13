/**
 * A4 — Set up by chat. The conversational route to the same profile as the About-you pages (A3): one question at a time, in the
 * person's own words or a tap. The server reads each answer and checks it the same way the form does (POST /onboarding/chat);
 * nothing is saved until the person finishes, and Finish saves through the same requests as the form.
 *
 * The transcript and the next question are read from the answers store, so the chat and the form always agree, and a person
 * can switch between them. Medicines are not part of set-up: they are added from the Medications tab. Nothing here scores, stages or
 * judges an answer (rules.md 1.1, 1.6).
 */
import { Fragment, useEffect, useRef, useState, type ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { href } from '@/app/routeIds'
import { cn } from '@/lib/cn'
import { Screen } from '@/ui/layout'
import { Alert, Button, Card, TextLink } from '@/ui/primitives'
import { ListChecks, PencilSimple } from '@/ui/icons'
import { DemoNotice, Dock, Later, LoadNotice, LoadingAnswers, TopBar } from './parts'
import { useOptions } from './options'
import { allPagesBody, emailBody, useOnboardingSource, useSaveStep } from './api'
import { useOnboarding, type OnboardingAnswers } from './useOnboarding'
import { CHAT_QUESTIONS, answerLabel, choicesFor, isAsked, replyText, type ChatQuestion, type Tr } from './chat/steps'
import { useChatAnswer, type ChatKnown } from './chat/api'

export function ChatSetup() {
  const { t } = useTranslation()
  const tr: Tr = (key, fallback) => t(key, fallback)
  const navigate = useNavigate()
  const a = useOnboarding((s) => s.answers)
  const set = useOnboarding((s) => s.set)
  const o = useOptions()
  const src = useOnboardingSource()
  const save = useSaveStep()
  const chat = useChatAnswer()
  /* optional questions skipped on this visit; not kept after leaving the screen */
  const [skipped, setSkipped] = useState<string[]>([])
  /* the question being changed from the transcript, if any */
  const [editing, setEditing] = useState<string | null>(null)
  /* the clarifying question, or a plain problem, for the last answer */
  const [notice, setNotice] = useState<string | null>(null)
  /* an answer the server could not read: it is shown as the person's message, then the reply above */
  const [unread, setUnread] = useState<string | null>(null)
  const [draft, setDraft] = useState('')
  /* the last Finish failed: the reason, shown in plain words */
  const [failed, setFailed] = useState<string | null>(null)
  const endRef = useRef<HTMLDivElement>(null)

  /* only the questions this person is asked (the work week only when they work), in the form's order */
  const questions = CHAT_QUESTIONS.filter((q) => isAsked(q, a))
  const rows = questions.map((q) => ({ q, label: answerLabel(q.id, a, o, tr) }))
  const pending = rows.find((r) => r.label === '' && !skipped.includes(r.q.id))
  const activeId = editing ?? pending?.q.id ?? null
  const active: ChatQuestion | undefined = activeId ? questions.find((q) => q.id === activeId) : undefined
  /* show the questions up to the one being asked; once everything is answered, the whole conversation */
  const visible = active ? rows.slice(0, questions.indexOf(active) + 1) : rows
  const done = rows.filter((r) => r.label !== '' || skipped.includes(r.q.id)).length
  const busy = chat.isPending
  /* what the checks depend on, from the form: sent with each answer, and never saved by the chat */
  const known: ChatKnown = { birthYear: a.birthYear, labDate: a.labDate, hba1cUnit: a.hba1cUnit, glucoseUnit: a.glucoseUnit, workType: a.workType }

  useEffect(() => {
    endRef.current?.scrollIntoView?.({ behavior: 'smooth', block: 'end' })
  }, [visible.length, notice, busy])

  if (!src.ready) {
    return (
      <Screen narrow>
        <TopBar />
        <LoadingAnswers />
      </Screen>
    )
  }

  /* Sends one answer. The server reads it; the answers it found go into the store, which the form reads too. */
  const send = async (text: string) => {
    const value = text.trim()
    if (!active || !value || busy) return
    setNotice(null)
    try {
      const res = await chat.mutateAsync({ text: value, step: active.id, known })
      const found = Object.keys(res.fields)
      if (found.length) set(res.fields as unknown as Partial<OnboardingAnswers>)
      if (res.understood) {
        /* understood with nothing to store is a skip ("skip", "I do not know", or "none" for free text) */
        if (found.length === 0) setSkipped((s) => [...s, active.id])
        setDraft('')
        setUnread(null)
        setEditing(null)
      } else {
        /* the words the person typed stay in the conversation, above the reply that asks again */
        setUnread(value)
        setDraft('')
        setNotice(res.reply)
      }
    } catch {
      setNotice(t('setup.offline', 'Smart Health could not reach the server just now. Your answer is not lost. Try again in a moment, or use the form.'))
    }
  }

  const skip = (id: string) => {
    setSkipped((s) => [...s, id])
    setNotice(null)
    setUnread(null)
    setDraft('')
  }
  const edit = (id: string) => {
    setEditing(id)
    setNotice(null)
    setUnread(null)
    setDraft('')
  }
  const keep = () => {
    setEditing(null)
    setNotice(null)
    setUnread(null)
    setDraft('')
  }

  /* Same as the form's Finish: every page and the reminder email are saved, then the summary. A failure keeps the person here. */
  const finish = async () => {
    if (src.readOnly) return navigate(href('A6'))
    if (src.loadFailed) {
      setFailed(t('setup.noRead', 'Your saved answers could not be read, so nothing is saved right now. Check your connection, then try again.'))
      return
    }
    setFailed(null)
    try {
      const email = src.email.isSuccess || a.reminderEmail.trim() ? emailBody(a) : null
      const res = await save.mutateAsync({ profile: allPagesBody(a, !src.saved.data?.profile), email })
      if (res.email === 'waiting') {
        setFailed(t('onboarding.email.waiting', 'We will save your email when your profile is created. It is kept on this device until then.'))
        return
      }
    } catch (err) {
      setFailed(err instanceof Error ? err.message : '')
      return
    }
    navigate(href('A6'))
  }

  const formLink = active ? (active.formStep === null ? href('A2') : `${href('A3')}?step=${active.formStep}`) : `${href('A3')}?step=3`
  const inputType = active?.kind === 'email' ? 'email' : active?.kind === 'phone' ? 'tel' : 'text'
  const choices = active ? choicesFor(active.id, o, tr) : []

  return (
    <Screen narrow>
      <TopBar />
      <div className="flex flex-col gap-2">
        <h1 className="break-words font-serif text-h1 font-medium tracking-tight text-ink">{t('setup.title', 'Set up by chat')}</h1>
        <p className="text-sub text-ink2">{t('setup.sub', 'Answer in your own words, or tap an answer. Nothing you say is lost if you switch to the form.')}</p>
        <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1">
          <p className="text-sub font-bold text-brand" aria-live="polite">
            {t('setup.progress', '{{done}} of {{total}} answered', { done, total: questions.length })}
          </p>
          <TextLink icon={ListChecks} onClick={() => navigate(formLink)}>
            {t('setup.useForm', 'Use the form instead')}
          </TextLink>
        </div>
        <div className="flex gap-1" aria-hidden>
          {questions.map((q, i) => (
            <span key={q.id} className={cn('h-1.5 flex-1 rounded-full', i < done ? 'bg-brand' : 'bg-line')} />
          ))}
        </div>
      </div>

      {src.loadFailed && <LoadNotice />}
      {src.readOnly && <DemoNotice />}

      <Card as="section" className="flex flex-col gap-4">
        <ol className="flex flex-col gap-4" aria-label={t('setup.conversation', 'Conversation')}>
          {visible.map(({ q, label }) => (
            <Fragment key={q.id}>
              <Bubble from="bot">{t(`setup.ask.${q.id}`, q.ask)}</Bubble>
              {label !== '' && (
                <Bubble
                  from="me"
                  action={
                    editing === q.id ? null : (
                      <TextLink icon={PencilSimple} onClick={() => edit(q.id)} className="self-end">
                        {t('setup.edit', 'Edit')}
                        <span className="sr-only"> {t(`setup.ask.${q.id}`, q.ask)}</span>
                      </TextLink>
                    )
                  }
                >
                  {label}
                </Bubble>
              )}
              {label === '' && skipped.includes(q.id) && <Bubble from="me">{t('setup.skipped', 'Skipped')}</Bubble>}
            </Fragment>
          ))}
          {unread !== null && <Bubble from="me">{unread}</Bubble>}
          {notice && <Bubble from="bot">{notice}</Bubble>}
          {busy && (
            <Bubble from="bot">
              <span className="inline-flex items-center gap-1.5" role="status">
                <span className="sr-only">{t('setup.reading', 'Reading your answer')}</span>
                {[0, 1, 2].map((i) => (
                  <span key={i} className="h-2 w-2 animate-pulse rounded-full bg-ink3" style={{ animationDelay: `${i * 150}ms` }} />
                ))}
              </span>
            </Bubble>
          )}
        </ol>
        <div ref={endRef} />
      </Card>

      {active ? (
        <Card as="section" className="flex flex-col gap-3" key={active.id}>
          {choices.length > 0 && (
            <div className="flex flex-wrap gap-2" role="group" aria-label={t(`setup.ask.${active.id}`, active.ask)}>
              {choices.map((c) => (
                <Button key={c.value} variant="secondary" size="md" className="!w-auto" disabled={busy} onClick={() => send(replyText(c.value))}>
                  {c.label}
                </Button>
              ))}
            </div>
          )}
          <form
            className="flex gap-2"
            onSubmit={(e) => {
              e.preventDefault()
              send(draft)
            }}
          >
            <input
              autoFocus
              type={inputType}
              inputMode={active.inputMode}
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              placeholder={active.placeholder && t(`setup.ph.${active.id}`, active.placeholder)}
              aria-label={t(`setup.ask.${active.id}`, active.ask)}
              className="min-h-12 min-w-0 flex-1 rounded-field border-[1.5px] border-line bg-card px-3.5 py-3 text-body text-ink placeholder:text-ink3 focus:border-brand focus:outline-none"
            />
            <Button type="submit" size="md" className="!w-auto flex-none px-5" disabled={!draft.trim() || busy}>
              {t('setup.send', 'Send')}
            </Button>
          </form>
          <div className="flex flex-wrap gap-x-5 gap-y-1">
            {editing === null && active.optional && <TextLink onClick={() => skip(active.id)}>{t('setup.skip', 'Skip this question')}</TextLink>}
            {editing !== null && <TextLink onClick={keep}>{t('setup.keep', 'Keep my answer')}</TextLink>}
          </div>
        </Card>
      ) : (
        <>
          {failed !== null && (
            <Alert tone="danger">
              <p>{t('setup.failed', 'Setup is not finished yet. Your answers are still on this device. Check your connection, then tap Check my answers again.')}</p>
              {failed && <p className="mt-1.5">{failed}</p>}
            </Alert>
          )}
          <Later />
          <Dock onNext={finish} nextDisabled={save.isPending} nextLabel={t('setup.toSummary', 'Check my answers')} />
        </>
      )}
    </Screen>
  )
}

/** One message. The assistant's are on the left; the person's, with any action such as Edit, on the right. */
function Bubble({ from, children, action }: { from: 'bot' | 'me'; children: ReactNode; action?: ReactNode }) {
  const { t } = useTranslation()
  const me = from === 'me'
  return (
    <li className={cn('flex max-w-[90%] flex-col gap-1', me && 'self-end items-end')}>
      <span className="text-micro font-bold text-ink2">{me ? t('setup.you', 'You') : t('setup.us', 'Smart Health')}</span>
      <div className={cn('break-words rounded-card border-[1.5px] px-3.5 py-2.5 text-body text-ink', me ? 'border-brand bg-brand-soft' : 'border-line bg-card')}>{children}</div>
      {action}
    </li>
  )
}
