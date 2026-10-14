import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from './repositories'
import type { BloodPressureLogInput, LogInput, NewMedication, WorkoutLogInput } from './repositories/types'
import type { ClashStatus, HomeOverview, InsightsDays, LunchIdeas, MedicineStock, MissAnswer, Period, ReportDays, StockList, TimelineDays, UserList } from './types'
import { request } from './repositories/http'
import { useUi } from '@/state/store'

export const useHome = () => useQuery({ queryKey: ['home'], queryFn: () => api.getHome() })
export const useInsights = (period: Period) => useQuery({ queryKey: ['insights', period], queryFn: () => api.getInsights(period) })
export const useInsightsOverview = (days: InsightsDays) => useQuery({ queryKey: ['insights', 'overview', days], queryFn: () => api.getInsightsOverview(days) })
/** `end` (YYYY-MM-DD) moves the period back; leave it out for the latest days */
export const useInsightsTimeline = (days: TimelineDays, end?: string) =>
  useQuery({ queryKey: ['insights', 'timeline', days, end ?? 'latest'], queryFn: () => api.getInsightsTimeline(days, end), placeholderData: keepPreviousData })
/** One day for the Insights drill-down (the day page) */
export const useInsightsDay = (date: string, enabled = true) => useQuery({ queryKey: ['insights', 'day', date], queryFn: () => api.getInsightsDay(date), enabled })
export const useInsightsOverviewDays = (from: string, to: string, enabled = true) =>
  useQuery({ queryKey: ['insights', 'overviewDays', from, to], queryFn: () => api.getInsightsOverviewDays(from, to), enabled, placeholderData: keepPreviousData })
export const useInsightsGlucose = (days: InsightsDays) => useQuery({ queryKey: ['insights', 'glucose', days], queryFn: () => api.getInsightsGlucose(days) })
export const useInsightsFood = (days: InsightsDays) => useQuery({ queryKey: ['insights', 'food', days], queryFn: () => api.getInsightsFood(days) })
export const useInsightsActivity = (days: InsightsDays) => useQuery({ queryKey: ['insights', 'activity', days], queryFn: () => api.getInsightsActivity(days) })
export const useInsightsSleep = (days: InsightsDays) => useQuery({ queryKey: ['insights', 'sleep', days], queryFn: () => api.getInsightsSleep(days) })
/** One calendar month of doses ("YYYY-MM"); without a month, the person's latest month. The previous month stays on screen while the next one loads. */
export const useInsightsMedication = (month?: string) => useQuery({ queryKey: ['insights', 'medication', month ?? 'latest'], queryFn: () => api.getInsightsMedication(month), placeholderData: keepPreviousData })
export const useInsightsSprint = () => useQuery({ queryKey: ['insights', 'sprint'], queryFn: () => api.getInsightsSprint() })
export const useInsightsHeart = (days: InsightsDays) => useQuery({ queryKey: ['insights', 'heart', days], queryFn: () => api.getInsightsHeart(days) })
export const useInsightsBloodPressure = (days: InsightsDays) => useQuery({ queryKey: ['insights', 'bloodPressure', days], queryFn: () => api.getInsightsBloodPressure(days) })
export const useDay = (date: string) => useQuery({ queryKey: ['day', date], queryFn: () => api.getDay(date) })
export const useDayList = () => useQuery({ queryKey: ['dayList'], queryFn: () => api.getDayList() })
export const useLogProgress = () => useQuery({ queryKey: ['logProgress'], queryFn: () => api.getLogProgress(), refetchInterval: 60_000 })
/**
 * Home: today's plan, the four numbers and the 7-day chart in one read. Refreshed every minute (the plan follows the clock).
 * Every write goes through useWrite (mark a dose taken, save a meal or any log), which refreshes every read, so this key
 * ['homeOverview'] is refreshed with ['doses'] and ['logProgress'] without being named.
 */
export const useHomeOverview = () => useQuery({ queryKey: ['homeOverview'], queryFn: () => request<HomeOverview>('/home/overview'), refetchInterval: 60_000 })
export const useFoodFlags = () => useQuery({ queryKey: ['foodFlags'], queryFn: () => api.getFoodFlags() })
export const useLunchIdeas = () => useQuery({ queryKey: ['lunchIdeas'], queryFn: () => api.getLunchIdeas() })
/** Ideas for the open mealtime built from the person's own past meals of that kind (GET /nutrition/meal-ideas); off until a meal is named. */
export const useMealIdeas = (meal: 'lunch' | 'dinner' | null) =>
  useQuery({ queryKey: ['mealIdeas', meal], queryFn: () => request<LunchIdeas>(`/nutrition/meal-ideas?meal=${meal}`), enabled: meal != null, staleTime: 5 * 60_000 })
export const useAcceptSuggestion = () => useWrite((key: string) => api.acceptSuggestion(key))
export const useLearned = () => useQuery({ queryKey: ['learned'], queryFn: () => api.getLearned() })
export const useDigest = () => useQuery({ queryKey: ['digest'], queryFn: () => api.getDigest() })
export const useAudit = (enabled: boolean) => useQuery({ queryKey: ['audit'], queryFn: () => api.getAudit(), enabled })
export const useProgress = () => useQuery({ queryKey: ['progress'], queryFn: () => api.getProgress() })
export const useDietDays = (start: string, end: string) => useQuery({ queryKey: ['dietDays', start, end], queryFn: () => api.getDietDays(start, end) })
/** The same day totals for an Insights period. Waits until the period is known (it comes from the Food insights read). */
export const useDietDaysFor = (start?: string, end?: string) =>
  useQuery({ queryKey: ['dietDays', start, end], queryFn: () => api.getDietDays(start!, end!), enabled: !!start && !!end })
export const useBarrierSummary = () => useQuery({ queryKey: ['barrierSummary'], queryFn: () => api.getBarrierSummary() })
export const useLearnedAction = () => useWrite((a: { id: string; action: 'confirm' | 'edit' | 'delete'; text?: string }) => api.learnedAction(a.id, a.action, a.text))
export const useDismissSuggestion = () => useWrite((key: string) => api.dismissSuggestion(key))
export const useAiUsage = () => useQuery({ queryKey: ['aiUsage'], queryFn: () => api.getAiUsage() })
export const useLogContext = () => useQuery({ queryKey: ['logContext'], queryFn: () => api.getLogContext() })
export const useWeekWorkouts = () => useQuery({ queryKey: ['weekWorkouts'], queryFn: () => api.getWeekWorkouts() })
export const useAnalyzeMeal = () => useMutation({ mutationFn: (a: { file: File; description?: string; signal?: AbortSignal }) => api.analyzeMeal(a.file, a.description, a.signal) })
export const useRecent = () => useQuery({ queryKey: ['recent'], queryFn: () => api.listRecent() })
/** Today's doses for Home. Refreshed every minute because a dose's window opens and closes with the clock. */
export const useDoses = () => useQuery({ queryKey: ['doses'], queryFn: () => api.getDosesToday(), refetchInterval: 60_000 })
/**
 * The clash box. While a check is running (the server says so) it is read every 3 seconds, since the check runs in the background for up
 * to a minute after a medicine is added. Otherwise it is read on load and when the window regains focus, with no timer.
 */
export const useClash = () =>
  useQuery({ queryKey: ['clash'], queryFn: () => api.getClash(), refetchInterval: (q) => (q.state.data?.checking ? 3_000 : false) })
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
/** My stock (H1): how many are left of each regular medicine. */
export const useStock = () => useQuery({ queryKey: ['stock'], queryFn: () => request<StockList>('/medications/stock') })
/** "I bought more" ({add}) or "Change the number" ({set}). Every read refreshes after it (useWrite). */
export const useStockChange = () =>
  useWrite((a: { id: string; change: { add: number } | { set: number } }) =>
    request<MedicineStock>(`/medications/${encodeURIComponent(a.id)}/stock`, { method: 'POST', body: JSON.stringify(a.change) }))
/** Makes the explanation the first time (a web search, up to 30 seconds), then it is saved and instant. */
export const useExplainMed = () => useMutation({ mutationFn: (id: string) => api.explainMedication(id) })
export const useAskDoctorAbout = () => useMutation({ mutationFn: (a: { id: string; text: string }) => api.askDoctorAbout(a.id, a.text) })
export const useScan = (scanId: string | undefined) =>
  useQuery({ queryKey: ['scan', scanId], queryFn: () => api.getScanResult(scanId!), enabled: !!scanId })
export const useUploadScan = () =>
  useMutation({ mutationFn: (a: { file: File; cancel?: AbortSignal }) => api.uploadScan(a.file, a.cancel) })
export const useFacts = () => useQuery({ queryKey: ['facts'], queryFn: () => api.getFacts() })
export const useCarePlan = () => useQuery({ queryKey: ['care'], queryFn: () => api.getCarePlan() })
export const useBrief = () => useQuery({ queryKey: ['brief'], queryFn: () => api.getBrief() })
export const useDoctorReport = (days: ReportDays) => useQuery({ queryKey: ['doctorReport', days], queryFn: () => api.getDoctorReport(days) })
export const useNotices = () => useQuery({ queryKey: ['notices'], queryFn: () => api.listNotices() })
export const useNoticeHistory = () => useQuery({ queryKey: ['noticeHistory'], queryFn: () => api.listNoticeHistory() })
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
/** One blood pressure reading for the edit sheet; only fetched when an id is given. */
export const useBloodPressure = (id?: string) => useQuery({ queryKey: ['bp', id], queryFn: () => api.getBloodPressure(id!), enabled: !!id })
export const useWorkoutEntry = (id?: string) => useQuery({ queryKey: ['workout', id], queryFn: () => api.getWorkout(id!), enabled: !!id })
export const useUpdateWorkout = () => useWrite((a: { id: string; input: WorkoutLogInput }) => api.updateWorkout(a.id, a.input))
export const useUpdateBloodPressure = () => useWrite((a: { id: string; input: BloodPressureLogInput }) => api.updateBloodPressure(a.id, a.input))
export const useAddMed = () => useWrite((m: NewMedication) => api.addMedication(m))
export const useRemoveMed = () => useWrite((id: string) => api.removeMedication(id))
export const useConfirmScan = () =>
  useWrite((a: { scanId: string; fields: Record<string, string | null>; times: string[]; kind?: NewMedication['kind']; asNeeded?: boolean }) =>
    api.confirmScan(a.scanId, a.fields, a.times, a.kind, a.asNeeded))
export const useFactAction = () => useWrite((a: { id: string; action: 'confirm' | 'delete' | 'edit'; text?: string }) => api.factAction(a.id, a.action, a.text))
export const useAddQuestion = () => useWrite((a: { text: string; origin: 'user' | 'refused_chat' | 'clash' | 'side_effect' }) => api.addQuestion(a.text, a.origin))
export const useRemoveQuestion = () => useWrite((id: string) => api.removeQuestion(id))
export const usePlanAppointment = () => useWrite((a: { label: string; when: string }) => api.planAppointment(a.label, a.when))
export const useShare = () => useWrite(() => api.createShareLink())
export const useRevoke = () => useWrite(() => api.revokeShareLink())
export const useOpenNotice = () => useWrite((id: string) => api.openNotice(id))
export const useSync = () => useWrite(() => api.syncSources())
export const useChat = () => useMutation({ mutationFn: (t: string) => api.sendChat(t) })
