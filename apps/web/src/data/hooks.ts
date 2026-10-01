import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from './repositories'
import type { LogInput, NewMedication } from './repositories/types'
import type { MissReason, Period } from './types'

export const useHome = () => useQuery({ queryKey: ['home'], queryFn: () => api.getHome() })
export const useInsights = (period: Period) => useQuery({ queryKey: ['insights', period], queryFn: () => api.getInsights(period) })
export const useDay = (date: string) => useQuery({ queryKey: ['day', date], queryFn: () => api.getDay(date) })
export const useDayList = () => useQuery({ queryKey: ['dayList'], queryFn: () => api.getDayList() })
export const useRecent = () => useQuery({ queryKey: ['recent'], queryFn: () => api.listRecent() })
export const useMeds = () => useQuery({ queryKey: ['meds'], queryFn: () => api.listMedications() })
export const useMed = (id: string) => useQuery({ queryKey: ['med', id], queryFn: () => api.getMedication(id) })
export const useScan = () => useQuery({ queryKey: ['scan'], queryFn: () => api.getScanResult() })
export const useFacts = () => useQuery({ queryKey: ['facts'], queryFn: () => api.getFacts() })
export const useCarePlan = () => useQuery({ queryKey: ['care'], queryFn: () => api.getCarePlan() })
export const useBrief = () => useQuery({ queryKey: ['brief'], queryFn: () => api.getBrief() })
export const useNotices = () => useQuery({ queryKey: ['notices'], queryFn: () => api.listNotices() })
export const useSources = () => useQuery({ queryKey: ['sources'], queryFn: () => api.listSources() })

/** Every write refreshes every read: simple and correct for a mock, and easy to narrow later. */
function useWrite<A, R>(fn: (a: A) => Promise<R>) {
  const qc = useQueryClient()
  return useMutation({ mutationFn: fn, onSuccess: () => qc.invalidateQueries() })
}

export const useMarkTaken = () => useWrite((id: string) => api.markDoseTaken(id))
export const useMissReason = () => useWrite((a: { id: string; reason: MissReason; note?: string }) => api.saveMissReason(a.id, a.reason, a.note))
export const useAnswerCheckin = () => useWrite((a: { id: string; answer: 'yes' | 'no' | 'skip' }) => api.answerCheckin(a.id, a.answer))
export const useSnooze = () => useWrite(() => api.snoozePrompt())
export const useLog = () => useWrite((i: LogInput) => api.logEntry(i))
export const useDeleteEntry = () => useWrite((id: string) => api.deleteEntry(id))
export const useAddMed = () => useWrite((m: NewMedication) => api.addMedication(m))
export const useConfirmScan = () => useWrite(() => api.confirmScan())
export const useFactAction = () => useWrite((a: { id: string; action: 'confirm' | 'delete' | 'edit'; text?: string }) => api.factAction(a.id, a.action, a.text))
export const useAddQuestion = () => useWrite((a: { text: string; origin: 'user' | 'refused_chat' | 'clash' | 'side_effect' }) => api.addQuestion(a.text, a.origin))
export const useRemoveQuestion = () => useWrite((id: string) => api.removeQuestion(id))
export const usePlanAppointment = () => useWrite((a: { label: string; when: string }) => api.planAppointment(a.label, a.when))
export const useShare = () => useWrite(() => api.createShareLink())
export const useRevoke = () => useWrite(() => api.revokeShareLink())
export const useMarkRead = () => useWrite(() => api.markNoticesRead())
export const useSync = () => useWrite(() => api.syncSources())
export const useChat = () => useMutation({ mutationFn: (t: string) => api.sendChat(t) })
