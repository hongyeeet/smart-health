/**
 * The chat setup's one request: read one answer (POST /onboarding/chat). It saves nothing. The screen puts the answers it
 * gets into the answers store, and the profile is saved through the form's own hooks in ../api.ts.
 */
import { useMutation } from '@tanstack/react-query'
import { request } from '@/data/repositories/http'

export interface ChatReply {
  /** answers found in the text, keyed as the answers store names them; values are as the form stores them */
  fields: Record<string, string>
  /** the answer to the question asked was read and passed the same checks as the form */
  understood: boolean
  /** the next question in order, or null after the last one; the question asked again when not understood */
  nextStep: string | null
  /** a short line, or the clarifying question when the answer was not understood */
  reply: string
}

export function useChatAnswer() {
  return useMutation({
    mutationFn: ({ text, step }: { text: string; step: string }) =>
      request<ChatReply>('/onboarding/chat', { method: 'POST', body: JSON.stringify({ text, step }) }),
  })
}
