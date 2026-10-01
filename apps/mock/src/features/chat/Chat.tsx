import { useEffect, useRef, useState } from 'react'
import { useAddQuestion, useChat } from '@/data/hooks'
import type { ChatReply } from '@/data/types'
import { useGo, useBack } from '@/app/navigation'
import { useUi } from '@/state/store'
import { Chip } from '@/ui/primitives'
import { ArrowLeft, ArrowRight, ShieldCheck } from '@/ui/icons'
import { cn } from '@/lib/cn'

interface Msg {
  id: number
  from: 'user' | 'ai'
  text: string
  reply?: ChatReply
  asked?: string
  done?: boolean
}

const suggestions = ['How was my week?', 'What is metformin for?', 'My sugar is fine today, can I skip my metformin?']

export function Chat() {
  const back = useBack('B1')
  const go = useGo()
  const chat = useChat()
  const add = useAddQuestion()
  const toast = useUi((s) => s.showToast)
  const [text, setText] = useState('')
  const [msgs, setMsgs] = useState<Msg[]>([{ id: 0, from: 'ai', text: 'Hello Mr Tan. I can explain your medicines, look back over your week, and note questions for your doctor. I cannot give medical advice.' }])
  const end = useRef<HTMLDivElement>(null)
  useEffect(() => {
    end.current?.scrollIntoView({ block: 'end' })
  }, [msgs, chat.isPending])

  const send = (t: string) => {
    const q = t.trim()
    if (!q || chat.isPending) return
    setText('')
    setMsgs((m) => [...m, { id: Date.now(), from: 'user', text: q }])
    chat.mutate(q, { onSuccess: (r) => setMsgs((m) => [...m, { id: Date.now() + 1, from: 'ai', text: r.text, reply: r, asked: q }]) })
  }

  const act = (m: Msg, a: NonNullable<ChatReply['actions']>[number]) => {
    setMsgs((all) => all.map((x) => (x.id === m.id ? { ...x, done: true } : x)))
    if (a.id === 'add_question') add.mutate({ text: m.asked ?? 'A question about my medicine', origin: 'refused_chat' }, { onSuccess: () => { toast('Added to your doctor questions'); go('K3') } })
    if (a.id === 'open_week') go('C1')
    if (a.id === 'open_med') go('H6', { params: { id: 'metformin' } })
  }

  return (
    <div className="absolute inset-0 flex flex-col">
      <header className="flex flex-none items-center gap-2 border-b border-line px-5 pb-2 pt-1">
        <button type="button" onClick={back} aria-label="Back" className="press -ml-3 flex h-12 w-12 items-center justify-center rounded-full hover:bg-well">
          <ArrowLeft size={26} aria-hidden />
        </button>
        <div>
          <h1 className="font-serif text-h2 font-medium">Ask Smart Health</h1>
          <p className="text-sub text-ink3">Explains and organises. No medical advice.</p>
        </div>
      </header>

      <div className="hide-scroll flex-1 overflow-y-auto px-5 py-4" role="log" aria-live="polite">
        <div className="flex flex-col gap-3">
          {msgs.map((m) => (
            <Bubble key={m.id} m={m} onAction={(a) => act(m, a)} />
          ))}
          {chat.isPending && (
            <div className="flex w-fit gap-1.5 rounded-card bg-well px-4 py-3.5" aria-label="Smart Health is typing">
              {[0, 1, 2].map((i) => (
                <span key={i} className="h-2 w-2 animate-pulse rounded-full bg-ink3" style={{ animationDelay: `${i * 140}ms` }} />
              ))}
            </div>
          )}
          <div ref={end} />
        </div>
      </div>

      <div className="flex-none border-t border-line bg-canvas px-5 pb-6 pt-3">
        {msgs.length < 3 && (
          <div className="hide-scroll -mx-5 mb-3 flex gap-2 overflow-x-auto px-5">
            {suggestions.map((s) => (
              <Chip key={s} onClick={() => send(s)} className="flex-none whitespace-nowrap">
                {s}
              </Chip>
            ))}
          </div>
        )}
        <form
          onSubmit={(e) => {
            e.preventDefault()
            send(text)
          }}
          className="flex items-center gap-2"
        >
          <label htmlFor="chat-input" className="sr-only">
            Your message
          </label>
          <input id="chat-input" value={text} onChange={(e) => setText(e.target.value)} placeholder="Ask about your week or a medicine" className="min-h-14 min-w-0 flex-1 rounded-chip border-[1.5px] border-line bg-card px-5 text-body placeholder:text-ink3 focus:border-brand focus:outline-none" />
          <button type="submit" aria-label="Send" disabled={!text.trim()} className="press flex h-14 w-14 flex-none items-center justify-center rounded-full bg-brand text-on-brand disabled:opacity-40">
            <ArrowRight size={24} aria-hidden />
          </button>
        </form>
      </div>
    </div>
  )
}

function Bubble({ m, onAction }: { m: Msg; onAction: (a: NonNullable<ChatReply['actions']>[number]) => void }) {
  if (m.from === 'user') return <p className="ml-auto max-w-[85%] rounded-card rounded-br-md bg-brand px-4 py-3 text-body text-on-brand">{m.text}</p>
  const safety = m.reply?.kind === 'safety'
  return (
    <div className={cn('max-w-[92%] rounded-card rounded-bl-md px-4 py-3', safety ? 'border-[1.5px] border-brass/60 bg-brass-soft' : 'bg-well')}>
      {safety && (
        <p className="mb-1.5 flex items-center gap-1.5 text-sub font-bold text-brass">
          <ShieldCheck size={20} aria-hidden /> Safety message
        </p>
      )}
      <p className="text-body">{m.text}</p>
      {m.reply?.actions && !m.done && (
        <div className="mt-3 flex flex-col gap-2">
          {m.reply.actions.map((a, i) => (
            <button key={a.id} type="button" onClick={() => onAction(a)} className={cn('press min-h-12 rounded-field px-3 text-sub font-bold', i === 0 ? 'bg-brand text-on-brand' : 'border-[1.5px] border-brand bg-card text-brand')}>
              {a.label}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
