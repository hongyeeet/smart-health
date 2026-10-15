/**
 * Data for the reviewer screen (K11): the suggestions the app made, and the ratings a reviewer gave them (GET /review/queue,
 * POST /review/ratings, GET /review/score). Every key includes the signed-in person, so the demo user and Mr Tan never share a queue.
 *
 * The queue is computed on the server and is slow (it looks up dishes and checks each one), so it is cached for a few minutes, and a
 * new rating updates the cached item in place instead of asking for the whole queue again.
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { request } from '@/data/repositories/http'
import { useUi } from '@/state/store'

export type Verdict = 'reasonable' | 'not_reasonable' | 'unsafe'
export type QueueSource = 'mine' | 'sample'

export interface ReviewUsual {
  name: string
  timesLogged: number | null
  kcal: number | null
  proteinG: number | null
  carbsG: number | null
  fatG: number | null
  sugarG: number | null
  sodiumMg: number | null
}

export interface ReviewSuggested {
  name: string
  serving: string | null
  kcal: number | null
  proteinG: number | null
  carbsG: number | null
  fatG: number | null
  sugarG: number | null
  sodiumMg: number | null
}

export interface ReviewRating {
  verdict: Verdict
  comment: string | null
}

export interface ReviewItem {
  suggestionKey: string
  usual: ReviewUsual
  suggested: ReviewSuggested
  change: string
  myRating: ReviewRating | null
}

export interface ReviewQueue {
  source: QueueSource
  items: ReviewItem[]
  total: number
  rated: number
  message: string | null
  sampleOffered: boolean
}

export interface ReviewScore {
  counts: { reasonable: number; notReasonable: number; unsafe: number }
  rated: number
  reasonableShare: number | null
  target: number
  minRatings: number
  unsafe: number
  status: 'met' | 'not_met' | 'too_few'
}

export interface RatingResult {
  suggestionKey: string
  verdict: Verdict
  comment: string | null
  rated: number
}

export const COMMENT_MAX = 300
const QUEUE_SIZE = 20

export function useReviewQueue(source: QueueSource) {
  const userKey = useUi((s) => s.userKey)
  return useQuery({
    queryKey: ['review', 'queue', userKey, source],
    queryFn: () => request<ReviewQueue>(`/review/queue?limit=${QUEUE_SIZE}&set=${source}`),
    staleTime: 5 * 60_000,
  })
}

export function useReviewScore() {
  const userKey = useUi((s) => s.userKey)
  return useQuery({ queryKey: ['review', 'score', userKey], queryFn: () => request<ReviewScore>('/review/score') })
}

export function useRateSuggestion(source: QueueSource) {
  const userKey = useUi((s) => s.userKey)
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (v: { suggestionKey: string; verdict: Verdict; comment: string | null }) =>
      request<RatingResult>('/review/ratings', { method: 'POST', body: JSON.stringify(v) }),
    onSuccess: (res) => {
      // Put the new rating into the cached queue; the score is cheap, so it is simply asked for again.
      queryClient.setQueryData<ReviewQueue>(['review', 'queue', userKey, source], (q) => {
        if (!q) return q
        const items = q.items.map((i) => (i.suggestionKey === res.suggestionKey ? { ...i, myRating: { verdict: res.verdict, comment: res.comment } } : i))
        return { ...q, items, rated: items.filter((i) => i.myRating).length }
      })
      queryClient.invalidateQueries({ queryKey: ['review', 'score', userKey] })
    },
  })
}
