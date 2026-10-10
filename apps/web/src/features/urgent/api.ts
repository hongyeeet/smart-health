import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { request } from '@/data/repositories/http'
import { useUi } from '@/state/store'

export type UrgentTier = 'none' | 'low' | 'very_low'
export type UrgentStatus = 'none' | 'active' | 'acknowledged' | 'escalated'

export interface UrgentState {
  id: string | null
  status: UrgentStatus
  tier: UrgentTier
  value: number | null
  since: string | null
  ageMinutes: number | null
  recheckAt: string | null
  contactAfter: string | null
  demo: boolean
  hasContact: boolean
  contactName: string | null
  contactPhone: string | null
  channels: { phone: boolean; email: boolean }
  emailQueued: boolean
  escalated: boolean
  emergencyNumber: string
  recheckMinutes: number
  contactAfterMinutes: number
}

const POLL_MS = 15_000

/** Who it is for is part of the key, so switching person never shows the other person's alert. */
const key = (user: string) => ['urgent', 'state', user] as const

export function useUrgentState() {
  const user = useUi((s) => s.userKey)
  return useQuery({ queryKey: key(user), queryFn: () => request<UrgentState>('/urgent/state'), refetchInterval: POLL_MS, refetchIntervalInBackground: false })
}

function useChange<V = void>(path: string, body?: (v: V) => unknown) {
  const qc = useQueryClient()
  const user = useUi((s) => s.userKey)
  return useMutation({
    mutationFn: (v: V) => request<UrgentState>(path, { method: 'POST', body: body ? JSON.stringify(body(v)) : undefined }),
    onSuccess: (s) => qc.setQueryData(key(user), s),
    onSettled: () => void qc.invalidateQueries({ queryKey: ['urgent'] }),
  })
}

export const useAcknowledge = () => useChange('/urgent/acknowledge')
export const useEscalate = () => useChange('/urgent/escalate')
export const useSimulate = () => useChange<number>('/urgent/simulate', (value) => ({ value }))
