/**
 * A4 — Set up by chat. The conversational route to the same profile as the About-you form (A3): one question at a time, in the
 * person's own words or a tap. The server reads each answer and checks it the same way the form does (POST /onboarding/chat);
 * nothing is saved until the person finishes, and the save uses the form's own request.
 *
 * The transcript and the next question are read from the answers store, so the chat and the form always agree, and a person
 * can switch between them. Nothing here scores, stages or judges an answer (rules.md 1.1, 1.6).
 */
import { Fragment, useEffect, useRef, useState, type ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { href } from '@/app/routeIds'
import { useUi } from '@/state/store'
import { cn } from '@/lib/cn'
import { Screen } from '@/ui/layout'
import { Alert, Button, Card, TextLink } from '@/ui/primitives'
import { ListChecks, PencilSimple } from '@/ui/icons'
import { Dock, PickMany, TopBar } from './parts'
import { labelOf, useOptions } from './options'
import { SafetyAlerts } from './SafetyAlerts'
import { toProfileBody, useNotifyEmail, usePrefillOnboarding, useSaveNotifyEmail, useSaveProfile, useSavedOnboarding } from './api'
import { useOnboarding, type OnboardingAnswers } from './useOnboarding'
import { CHAT_QUESTIONS, answerLabel, choicesFor, replyText, type ChatQuestion, type Tr } from './chat/steps'
import { useChatAnswer } from './chat/api'

export function ChatSetup() {
  const { t } = useTranslation()
  const tr: Tr = (key, fallback) => t(key, fallback)
  const navigate = useNavigate()
  const locale = useUi((s) => s.locale)
  const a = useOnboarding((s) => s.answers)
  const set = useOnboarding((s) => s.set)
  const o = useOptions()
  const saved = useSavedOnboarding()
  usePrefillOnboarding(saved.data)
  const saveProfile = useSaveProfile()
  const notify = useNotifyEmail()
  const saveEmail = useSaveNotifyEmail()
  const chat = useChatAnswer()
  /* optional questions skipped on this visit; not kept after leaving the screen */
  const [skipped, setSkipped] = useState<string[]>([])
  /* the question being changed from the transcript, if any */
  const [editing, setEditing] = useState<string | null>(null)
  /* the clarifying question, or a plain problem, for the last answer */
  const [notice, setNotice] = useState<string | null>(null)
  const [draft, setDraft] = useState('')
  const [emailFailed, setEmailFailed] = useState(false)
  const endRef = useRef<HTMLDivElement>(null)

  /* an address already stored for reminders fills the box once, when it is still empty (as on the form) */
  useEffect(() => {
    const stored = notify.data?.email
    if (stored && !useOnboarding.getState().answers.reminderEmail) set({ reminderEmail: stored })
  }, [notify.data, set])

  const rows = CHAT_QUESTIONS.map((q) => ({ q, label: answerLabel(q.id, a, o, tr) }))
  const pending = rows.find((r) => r.label === '' && !skipped.includes(r.q.id))
  const activeId = editing ?? pending?.q.id ?? null
  const active: ChatQuestion | undefined = activeId ? CHAT_QUESTIONS.find((q) => q.id === activeId) : undefined
  /* show the questions up to the one being asked; once everything is answered, the whole conversation */
  const visible = active ? rows.slice(0, CHAT_QUESTIONS.indexOf(active) + 1) : rows
  const done = rows.filter((r) => r.label !== '' || skipped.includes(r.q.id)).length
  const busy = chat.isPending

  useEffect(() => {
    endRef.current?.scrollIntoView?.({ behavior: 'smooth', block: 'end' })
  }, [visible.length, notice, busy])

  /* Sends one answer. The server reads it; the answers it found go into the store, which the form reads too. */
  const send = async (text: string) => {
    const value = text.trim()
    if (!active || !value || busy) return
    setNotice(null)
    try {
      const res = await chat.mutateAsync({ text: value, step: active.id })
      if (Object.keys(res.fields).length) set(res.fields as unknown as Partial<OnboardingAnswers>)
      if (res.understood) {
        setDraft('')
        setEditing(null)
      } else {
        setNotice(res.reply)
      }
    } catch {
      setNotice(t('setup.offline', 'Smart Health could not reach the server just now. Your answer is not lost. Try again in a moment, or use the form.'))
    }
  }

  const skip = (id: string) => {
    setSkipped((s) => [...s, id])
    setNotice(null)
    setDraft('')
  }
  const edit = (id: string) => {
    setEditing(id)
    setNotice(null)
    setDraft('')
  }
  const keep = () => {
    setEditing(null)
    setNotice(null)
    setDraft('')
  }

  /* Same as the form's last step: the reminder address first, then the profile. A failed address does not block the person. */
  const finish = async () => {
    const email = a.reminderEmail.trim()
    if (email && !emailFailed) {
      try {
        await saveEmail.mutateAsync(email)
      } catch {
        setEmailFailed(true)
        return
      }
    }
    await saveProfile.mutateAsync(toProfileBody(useOnboarding.getState().answers, locale, (code) => labelOf(o.conditions, code))).catch(() => undefined)
    navigate(href('A6'))
  }

  const formLink = active ? (active.formStep === null ? href('A2') : `${href('A3')}?step=${active.formStep}`) : href('A3')
  const inputType = active?.kind === 'email' ? 'email' : active?.kind === 'phone' ? 'tel' : 'text'

  return (
    <Screen>
      <TopBar />
      <div className="flex flex-col gap-2">
        <h1 className="break-words font-serif text-h1 font-medium tracking-tight text-ink">{t('setup.title', 'Set up by chat')}</h1>
        <p className="text-sub text-ink2">{t('setup.sub', 'Answer in your own words, or tap an answer. Nothing you say is lost if you switch to the form.')}</p>
        <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1">
          <p className="text-sub font-bold text-brand" aria-live="polite">
            {t('setup.progress', '{{done}} of {{total}} answered', { done, total: CHAT_QUESTIONS.length })}
          </p>
          <TextLink icon={ListChecks} onClick={() => navigate(formLink)}>
            {t('setup.useForm', 'Use the form instead')}
          </TextLink>
        </div>
        <div className="flex gap-1" aria-hidden>
          {CHAT_QUESTIONS.map((q, i) => (
            <span key={q.id} className={cn('h-1.5 flex-1 rounded-full', i < done ? 'bg-brand' : 'bg-line')} />
          ))}
        </div>
      </div>

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
          {active.kind === 'flags' ? (
            <>
              <PickMany stack none="none" label={t('setup.redLabel', 'Is any of these happening? Tick all that apply.')} options={o.redFlags} value={a.redFlags} onChange={(redFlags) => set({ redFlags })} />
              <SafetyAlerts flags={a.redFlags} />
              <Button disabled={a.redFlags.length === 0} onClick={keep}>
                {t('setup.continue', 'Continue')}
              </Button>
            </>
          ) : (
            <>
              {active.kind === 'choice' && (
                <div className="flex flex-wrap gap-2" role="group" aria-label={t(`setup.ask.${active.id}`, active.ask)}>
                  {choicesFor(active.id, o, tr).map((c) => (
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
                {editing === null && active.optional && (
                  <TextLink onClick={() => skip(active.id)}>{t('setup.skip', 'Skip this question')}</TextLink>
                )}
                {editing !== null && <TextLink onClick={keep}>{t('setup.keep', 'Keep my answer')}</TextLink>}
              </div>
            </>
          )}
        </Card>
      ) : (
        <>
          {emailFailed && <Alert tone="warn">{t('setup.emailFailed', 'We could not save your email just now. Your answer is kept on this device. You can add it later in Me, Privacy.')}</Alert>}
          <Dock onNext={finish} nextDisabled={saveProfile.isPending || saveEmail.isPending} nextLabel={emailFailed ? t('setup.emailAnyway', 'Continue without it') : t('setup.toSummary', 'Check my answers')} />
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
