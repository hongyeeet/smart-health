import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from './repositories'
import type { LogInput, NewMedication } from './repositories/types'
import type { ClashStatus, MissAnswer, Period, UserList } from './types'
import { request } from './repositories/http'
import { useUi } from '@/state/store'

export const useHome = () => useQuery({ queryKey: ['home'], queryFn: () => api.getHome() })
export const useInsights = (period: Period) => useQuery({ queryKey: ['insights', period], queryFn: () => api.getInsights(period) })
export const useDay = (date: string) => useQuery({ queryKey: ['day', date], queryFn: () => api.getDay(date) })
export const useDayList = () => useQuery({ queryKey: ['dayList'], queryFn: () => api.getDayList() })
export const useLogProgress = () => useQuery({ queryKey: ['logProgress'], queryFn: () => api.getLogProgress(), refetchInterval: 60_000 })
export const useFoodFlags = () => useQuery({ queryKey: ['foodFlags'], queryFn: () => api.getFoodFlags() })
export const useLunchIdeas = () => useQuery({ queryKey: ['lunchIdeas'], queryFn: () => api.getLunchIdeas() })
export const useAcceptSuggestion = () => useWrite((key: string) => api.acceptSuggestion(key))
export const useLearned = () => useQuery({ queryKey: ['learned'], queryFn: () => api.getLearned() })
export const useDigest = () => useQuery({ queryKey: ['digest'], queryFn: () => api.getDigest() })
export const useAudit = (enabled: boolean) => useQuery({ queryKey: ['audit'], queryFn: () => api.getAudit(), enabled })
export const useProgress = () => useQuery({ queryKey: ['progress'], queryFn: () => api.getProgress() })
export const useLearnedAction = () => useWrite((a: { id: string; action: 'confirm' | 'edit' | 'delete'; text?: string }) => api.learnedAction(a.id, a.action, a.text))
export const useDismissSuggestion = () => useWrite((key: string) => api.dismissSuggestion(key))
export const useAiUsage = () => useQuery({ queryKey: ['aiUsage'], queryFn: () => api.getAiUsage() })
export const useLogContext = () => useQuery({ queryKey: ['logContext'], queryFn: () => api.getLogContext() })
export const useWeekWorkouts = () => useQuery({ queryKey: ['weekWorkouts'], queryFn: () => api.getWeekWorkouts() })
export const useAnalyzeMeal = () => useMutation({ mutationFn: (a: { file: File; description?: string }) => api.analyzeMeal(a.file, a.description) })
export const useRecent = () => useQuery({ queryKey: ['recent'], queryFn: () => api.listRecent() })
/** Today's doses for Home. Refreshed every minute because a dose's window opens and closes with the clock. */
export const useDoses = () => useQuery({ queryKey: ['doses'], queryFn: () => api.getDosesToday(), refetchInterval: 60_000 })
/** The clash box. Polled every few seconds because the check runs in the background for up to a minute after a medicine is added. */
export const useClash = () => useQuery({ queryKey: ['clash'], queryFn: () => api.getClash(), refetchInterval: 5_000 })
export const useRunClashCheck = () => {
  const qc = useQueryClient()
  return useMutation({ mutationFn: () => api.runClashCheck(), onSuccess: (s) => qc.setQueryData(['clash'], s) })
}
export const useAskAboutClash = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => api.askAboutClash(id),
    onSuccess: (_, id) =>
      qc.setQueryData<ClashStatus>(['clash'], (old) => (old ? { ...old, alerts: old.alerts.map((a) => (a.id === id ? { ...a, questionAdded: true } : a)) } : old)),
  })
}
/** The person's own question about a clash alert, in their words. It does not use up the ready-made question. */
export const useAskOwnClashQuestion = () => useMutation({ mutationFn: (a: { id: string; text: string }) => api.askAboutClash(a.id, a.text) })
export const useAcknowledgeClash = () => {
  const qc = useQueryClient()
  return useMutation({ mutationFn: (id: string) => api.acknowledgeClash(id), onSuccess: (s) => qc.setQueryData(['clash'], s) })
}
export const useMeds = () => useQuery({ queryKey: ['meds'], queryFn: () => api.listMedications() })
export const useMed = (id: string) => useQuery({ queryKey: ['med', id], queryFn: () => api.getMedication(id) })
/** Makes the explanation the first time (a web search, up to 30 seconds), then it is saved and instant. */
export const useExplainMed = () => useMutation({ mutationFn: (id: string) => api.explainMedication(id) })
export const useAskDoctorAbout = () => useMutation({ mutationFn: (a: { id: string; text: string }) => api.askDoctorAbout(a.id, a.text) })
export const useScan = (scanId: string | undefined) =>
  useQuery({ queryKey: ['scan', scanId], queryFn: () => api.getScanResult(scanId!), enabled: !!scanId })
export const useUploadScan = () =>
  useMutation({ mutationFn: (file: File) => api.uploadScan(file) })
export const useFacts = () => useQuery({ queryKey: ['facts'], queryFn: () => api.getFacts() })
export const useCarePlan = () => useQuery({ queryKey: ['care'], queryFn: () => api.getCarePlan() })
export const useBrief = () => useQuery({ queryKey: ['brief'], queryFn: () => api.getBrief() })
export const useNotices = () => useQuery({ queryKey: ['notices'], queryFn: () => api.listNotices() })
export const useUsers = () => useQuery({ queryKey: ['users'], queryFn: () => request<UserList>('/users'), staleTime: Infinity })

/** Switch between the demo user and Mr Tan. Everything cached belongs to the previous person, so it is reset and reloaded. */
export function useSwitchUser() {
  const qc = useQueryClient()
  const setUserKey = useUi((s) => s.setUserKey)
  return (key: string) => {
    setUserKey(key)
    void qc.resetQueries()
  }
}
export const useSources = () => useQuery({ queryKey: ['sources'], queryFn: () => api.listSources() })

/** Every write refreshes every read: simple and correct for a mock, and easy to narrow later. */
function useWrite<A, R>(fn: (a: A) => Promise<R>) {
  const qc = useQueryClient()
  return useMutation({ mutationFn: fn, onSuccess: () => qc.invalidateQueries() })
}

export const useMarkTaken = () => useWrite((id: string) => api.markDoseTaken(id))
export const useMissReason = () => useWrite((a: { id: string; reason: MissAnswer; note?: string }) => api.saveMissReason(a.id, a.reason, a.note))
export const useAnswerCheckin = () => useWrite((a: { id: string; answer: 'yes' | 'no' | 'skip' }) => api.answerCheckin(a.id, a.answer))
export const useSnooze = () => useWrite(() => api.snoozePrompt())
export const useLog = () => useWrite((i: LogInput) => api.logEntry(i))
export const useDeleteEntry = () => useWrite((id: string) => api.deleteEntry(id))
export const useAddMed = () => useWrite((m: NewMedication) => api.addMedication(m))
export const useConfirmScan = () =>
  useWrite((a: { scanId: string; fields: Record<string, string | null>; times: string[]; kind?: NewMedication['kind'] }) =>
    api.confirmScan(a.scanId, a.fields, a.times, a.kind))
export const useFactAction = () => useWrite((a: { id: string; action: 'confirm' | 'delete' | 'edit'; text?: string }) => api.factAction(a.id, a.action, a.text))
export const useAddQuestion = () => useWrite((a: { text: string; origin: 'user' | 'refused_chat' | 'clash' | 'side_effect' }) => api.addQuestion(a.text, a.origin))
export const useRemoveQuestion = () => useWrite((id: string) => api.removeQuestion(id))
export const usePlanAppointment = () => useWrite((a: { label: string; when: string }) => api.planAppointment(a.label, a.when))
export const useShare = () => useWrite(() => api.createShareLink())
export const useRevoke = () => useWrite(() => api.revokeShareLink())
export const useOpenNotice = () => useWrite((id: string) => api.openNotice(id))
export const useSync = () => useWrite(() => api.syncSources())
export const useChat = () => useMutation({ mutationFn: (t: string) => api.sendChat(t) })
