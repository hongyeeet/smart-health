/**
 * I1 — Ask Smart Health.
 *
 * A chat that answers only from the person's own data (POST /chat/messages). Urgent words and medicine or diagnosis questions get a fixed
 * reply from the server, never a model answer; a refused question can be added to the doctor questions. Every answer shows where its numbers
 * come from as chips that open the screen. The line under the box says what this is and is not.
 */
import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { ROUTES } from '@/app/routeIds'
import { Header } from '@/ui/layout'
import { Alert, Button, Skeleton } from '@/ui/primitives'
import { ArrowRight, ChatCircleDots } from '@/ui/icons'
import { useSend, useStarters, useThread, type Item } from './api'
import { Actions, Bubble, TypingIndicator } from './parts'

const MAX = 500

export function Chat() {
  const { t } = useTranslation()
  const { thread } = useThread()
  const { send, pending } = useSend()
  const starters = useStarters()
  const [text, setText] = useState('')
  const end = useRef<HTMLDivElement>(null)
  const box = useRef<HTMLTextAreaElement>(null)
  const items = thread.items

  useEffect(() => {
    end.current?.scrollIntoView({
      block: 'end',
      behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth',
    })
  }, [items.length, pending])

  const submit = (e?: FormEvent) => {
    e?.preventDefault()
    if (!text.trim() || pending) return
    send(text)
    setText('')
    box.current?.focus()
  }
  const onKey = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault()
      submit()
    }
  }
  const lastAnswerId = [...items].reverse().find((i) => i.role === 'assistant' && !i.failed)?.id

  return (
    // Not <Screen>: the box stays at the bottom of the screen, and only the conversation scrolls
    <div className="absolute inset-0 flex flex-col">
      <div className="hide-scroll scroll-area flex-1 overflow-y-auto overflow-x-hidden px-5 pt-1 md:px-8">
        <div className="mx-auto flex w-full flex-col gap-4 pb-4 md:max-w-[720px]">
          <Header title={t('chat.title', 'Ask Smart Health')} back backTo="B1" />
          <div role="log" aria-live="polite" aria-label={t('chat.conversation', 'Conversation')} className="flex flex-col gap-3">
            {items.length === 0 && (
              <div className="flex flex-col gap-3">
                <div className="flex items-start gap-3 rounded-card border border-line bg-card p-4">
                  <ChatCircleDots size={28} className="mt-0.5 flex-none text-brand" aria-hidden />
                  <p className="text-body text-ink">
                    {t('chat.intro', 'Ask about your own glucose, meals, activity, sleep or medicines. I answer from what you have logged.')}
                  </p>
                </div>
                <p className="text-sub font-bold text-ink3">{t('chat.couldAsk', 'You could ask')}</p>
                {starters.isLoading ? (
                  <Skeleton className="h-12" />
                ) : starters.isError ? (
                  <p className="text-sub text-ink2">{t('chat.typeBelow', 'You can type your own question below.')}</p>
                ) : (
                  <div className="flex flex-wrap gap-2">
                    {(starters.data ?? []).map((s) => (
                      <button
                        key={s}
                        type="button"
                        onClick={() => send(s)}
                        disabled={pending}
                        className="press min-h-12 rounded-chip border-[1.5px] border-line bg-card px-4 py-2 text-left text-sub text-ink hover:bg-well disabled:opacity-45"
                      >
                        {s}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )}
            {items.map((i) => (
              <Row key={i.id} item={i} showFollowUps={i.id === lastAnswerId && !pending} onAsk={send} onRetry={() => send(i.text, true)} />
            ))}
            {pending && <TypingIndicator />}
            <div ref={end} />
          </div>
        </div>
      </div>
      <div className="border-t border-line bg-canvas px-5 pb-[max(1rem,env(safe-area-inset-bottom))] pt-3 md:px-8">
        <div className="mx-auto flex w-full flex-col gap-2 md:max-w-[720px]">
          <form onSubmit={submit} className="flex items-end gap-2">
            <label htmlFor="chat-input" className="sr-only">
              {t('chat.yourQuestion', 'Your question')}
            </label>
            <textarea
              id="chat-input"
              ref={box}
              value={text}
              onChange={(e) => setText(e.target.value)}
              onKeyDown={onKey}
              maxLength={MAX}
              rows={1}
              placeholder={t('chat.placeholder', 'Type your question')}
              enterKeyHint="send"
              className="max-h-40 min-h-12 flex-1 resize-none rounded-card border-[1.5px] border-line bg-card px-3.5 py-3 text-body text-ink placeholder:text-ink3 focus:border-brand focus:outline-none"
            />
            <Button
              type="submit"
              size="md"
              disabled={!text.trim() || pending}
              aria-label={t('chat.send', 'Send')}
              className="!w-12 flex-none !px-0"
              icon={ArrowRight}
            >
              <span className="sr-only">{t('chat.send', 'Send')}</span>
            </Button>
          </form>
          <p className="text-micro text-ink3">{t('chat.note', 'Smart Health answers from your own data. It cannot give medical advice. For emergencies call 995.')}</p>
        </div>
      </div>
    </div>
  )
}

function Row({ item, showFollowUps, onAsk, onRetry }: { item: Item; showFollowUps: boolean; onAsk: (t: string) => void; onRetry: () => void }) {
  const { t } = useTranslation()
  if (item.failed)
    return (
      <Alert tone="warn" title={t('chat.failedTitle', 'That did not go through')}>
        <div className="flex flex-col gap-2">
          <span>{t('chat.failedText', 'We could not reach Smart Health. Your question was not answered.')}</span>
          <Button variant="secondary" size="md" onClick={onRetry}>
            {t('chat.retry', 'Try again')}
          </Button>
        </div>
      </Alert>
    )
  const openable = (item.sources ?? []).filter((s) => s.to in ROUTES)
  return (
    <div className="flex flex-col gap-2">
      <Bubble item={item} sources={item.role === 'assistant' ? openable : undefined} askText={item.actions?.find((a) => a.kind === 'doctor_question')?.text ?? undefined} />
      <Actions item={item} />
      {showFollowUps && (item.followUps ?? []).length > 0 && (
        <div className="flex flex-wrap gap-2" aria-label={t('chat.otherAsk', 'Other things you could ask')}>
          {(item.followUps ?? []).map((f) => (
            <button
              key={f}
              type="button"
              onClick={() => onAsk(f)}
              className="press min-h-11 rounded-chip border-[1.5px] border-line bg-card px-3.5 py-2 text-left text-sub text-ink hover:bg-well"
            >
              {f}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
