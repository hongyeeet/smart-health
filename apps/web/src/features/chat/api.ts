import i18n from '@/i18n'
import { useMutation, useQuery } from '@tanstack/react-query'
import { create } from 'zustand'
import { request } from '@/data/repositories/http'
import { useUi } from '@/state/store'

/** Wire types for the chat (services/api/app/schemas/chat.py). */
export type ReplyKind = 'answer' | 'urgent' | 'refused' | 'unavailable' | 'empty' | 'help'

export interface ChatSource {
  label: string
  to: string
  detail: string | null
}

export interface ChatAction {
  kind: 'open' | 'doctor_question'
  label: string
  to: string | null
  text: string | null
}

interface WireMessage {
  id: string
  role: 'user' | 'assistant'
  text: string
  kind: ReplyKind | null
  at: string
}

interface SendOut {
  conversationId: string
  message: WireMessage
  reply: WireMessage
  sources: ChatSource[]
  actions: ChatAction[]
  followUps: string[]
}

export interface Item {
  id: string
  role: 'user' | 'assistant'
  text: string
  kind?: ReplyKind
  sources?: ChatSource[]
  actions?: ChatAction[]
  followUps?: string[]
  /** The question could not be sent; the person can try again with the same words. */
  failed?: boolean
}

interface Thread {
  conversationId: string | null
  items: Item[]
}

/** The conversation is kept per person while the app is open, so leaving the screen and coming back does not lose it. */
const useThreads = create<{
  threads: Record<string, Thread>
  set: (user: string, f: (t: Thread) => Thread) => void
}>((setState, get) => ({
  threads: {},
  set: (user, f) =>
    setState({
      threads: {
        ...get().threads,
        [user]: f(get().threads[user] ?? { conversationId: null, items: [] }),
      },
    }),
}))

export function useThread() {
  const user = useUi((s) => s.userKey)
  const thread = useThreads((s) => s.threads[user]) ?? {
    conversationId: null,
    items: [],
  }
  const set = useThreads((s) => s.set)
  return {
    thread,
    update: (f: (t: Thread) => Thread) => set(user, f),
    clear: () => set(user, () => ({ conversationId: null, items: [] })),
  }
}

export function useStarters() {
  const user = useUi((s) => s.userKey)
  return useQuery({
    queryKey: ['chat', 'starters', user],
    queryFn: () => request<{ starters: string[] }>('/chat/starters').then((r) => r.starters),
    staleTime: 60_000,
  })
}

/** Sends one message. `retry` re-sends the words of a message that failed without showing them twice. */
export function useSend() {
  const { thread, update } = useThread()
  // The updates run inside the mutation function, not in mutate() callbacks, so an answer that arrives after the person has left the screen is still kept.
  const m = useMutation({
    mutationFn: async (text: string) => {
      try {
        const r = await request<SendOut>('/chat/messages', {
          method: 'POST',
          body: JSON.stringify({ text, conversationId: thread.conversationId }),
        })
        update((th) => ({
          conversationId: r.conversationId,
          items: [
            ...th.items,
            {
              id: r.reply.id,
              role: 'assistant',
              text: r.reply.text,
              kind: r.reply.kind ?? 'answer',
              sources: r.sources,
              actions: r.actions,
              followUps: r.followUps,
            },
          ],
        }))
      } catch {
        update((th) => ({
          ...th,
          items: [
            ...th.items,
            {
              id: `failed-${Date.now()}`,
              role: 'assistant',
              text,
              failed: true,
            },
          ],
        }))
      }
    },
  })
  const send = (text: string, retry = false) => {
    const t = text.trim()
    if (!t || m.isPending) return
    update((th) => ({
      ...th,
      items: retry ? th.items.filter((i) => !i.failed) : [...th.items, { id: `local-${Date.now()}`, role: 'user', text: t }],
    }))
    m.mutate(t)
  }
  return { send, pending: m.isPending }
}

/** Adds the person's own words to their doctor questions (screen K3). */
export function useAddDoctorQuestion() {
  const showToast = useUi((s) => s.showToast)
  return useMutation({
    mutationFn: (text: string) =>
      request<{ id: string; text: string }>('/chat/questions', {
        method: 'POST',
        body: JSON.stringify({ text }),
      }),
    onSuccess: () => showToast(i18n.t('chat.addedToast', 'Added to your doctor questions.')),
    onError: () => showToast(i18n.t('chat.addFailed', 'Could not add it. Please try again.')),
  })
}
