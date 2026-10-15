import { useQuery } from '@tanstack/react-query'
import { api } from '@/data/repositories'
import type { Medication } from '@/data/types'

type S = { tone: 'ok' | 'info' | 'neutral' | 'warn'; label: string } | null

/** Today's status line for each medicine, from the dose list. */
export function useDoseState() {
  const { data } = useQuery({ queryKey: ['dosesToday'], queryFn: () => api.listDosesToday() })
  return (m: Medication): S => {
    const doses = (data ?? []).filter((d) => d.medId === m.id)
    if (doses.length === 0) return null
    if (doses.some((d) => d.status === 'due')) return { tone: 'info', label: `Due ${doses.find((d) => d.status === 'due')!.time}` }
    if (doses.every((d) => d.status === 'taken' || d.status === 'taken_late_logged')) return { tone: 'ok', label: 'Taken today' }
    const next = doses.find((d) => d.status === 'scheduled')
    if (next) return { tone: 'neutral', label: `Next ${next.time}` }
    return { tone: 'warn', label: 'Not confirmed' }
  }
}
