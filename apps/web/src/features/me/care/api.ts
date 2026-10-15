/**
 * Data for the Me care screens (K3, K4, K7, K12). Own types and hooks, as the other feature folders do. Every key includes the user, so
 * switching between the demo user and Mr Tan never shows the other person's visits or questions.
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { request } from '@/data/repositories/http'
import { useUi } from '@/state/store'

/** The kinds the Log an appointment form offers. */
export type AppointmentKind = 'gp_review' | 'diabetes_review' | 'eye_screening' | 'foot_screening' | 'kidney_test' | 'hba1c_test' | 'other'

/** Older visits can still hold a kind the form no longer offers; they keep their old label. */
export type StoredAppointmentKind = AppointmentKind | 'vaccination' | 'dental'

export const APPOINTMENT_KINDS: { value: AppointmentKind; label: string }[] = [
  { value: 'gp_review', label: 'GP review' },
  { value: 'diabetes_review', label: 'Diabetes review' },
  { value: 'eye_screening', label: 'Eye screening' },
  { value: 'foot_screening', label: 'Foot check' },
  { value: 'kidney_test', label: 'Kidney test' },
  { value: 'hba1c_test', label: 'Blood test' },
  { value: 'other', label: 'Other visit' },
]

/** Labels for the kinds no longer offered, used only when an older visit or a suggested visit has one of them. */
export const RETIRED_KIND_LABELS: Partial<Record<StoredAppointmentKind, string>> = {
  vaccination: 'Vaccination',
  dental: 'Dental check',
}

export interface Appointment {
  id: string
  kind: StoredAppointmentKind
  kindLabel: string
  /** 'past' is a planned visit whose time has passed; it is listed under Earlier visits, never as Planned. */
  status: 'suggested' | 'planned' | 'completed' | 'cancelled' | 'missed' | 'past'
  scheduledFor: string | null
  scheduledLabel: string | null
  /** Kept on the record for older visits; the screens no longer show it. */
  location: string | null
  suggestedReason: string | null
  confirmedAt: string | null
}

export interface Preventive {
  kind: string
  label: string
  status: 'ok' | 'due_soon' | 'overdue' | 'unknown'
  lastDoneOn: string | null
  nextDueOn: string | null
  detail: string
}

export interface DoctorQuestion {
  id: string
  text: string
  origin: 'user' | 'refused_chat' | 'checkin' | 'agent_suggested' | null
  originLabel: string
  /** open: on the list. asked: marked done. */
  status: 'open' | 'asked'
  createdAt: string
  canRemove: boolean
}

export interface CarePlan {
  /** the earliest planned visit whose time is still to come (the one rule shared with the L1 brief), or null */
  nextAppointment: Appointment | null
  upcoming: Appointment[]
  /** planned visits whose time has passed, newest first, with status 'past' */
  earlier: Appointment[]
  preventive: Preventive[]
  questions: DoctorQuestion[]
}

export interface NewAppointment {
  kind: StoredAppointmentKind
  /** Local Singapore time, without a zone: "2026-10-20T09:30" */
  scheduledFor: string
  suggestedId?: string | null
}

export interface ConnectedSource {
  key: 'cgm' | 'watch' | 'camera'
  label: string
  model: string | null
  status: 'connected' | 'connected_no_data' | 'not_connected' | 'on_device'
  statusLabel: string
  lastDataAt: string | null
  freshness: 'up_to_date' | 'old' | 'none'
  note: string
}

const userKey = () => useUi.getState().userKey

export const careKeys = {
  plan: () => ['care', userKey(), 'plan'] as const,
  sources: () => ['care', userKey(), 'sources'] as const,
  appointments: () => ['care', userKey(), 'appointments'] as const,
}

/** Refetch everything the care screens show, after any write. */
function useInvalidateCare() {
  const qc = useQueryClient()
  return () => {
    void qc.invalidateQueries({ queryKey: ['care'] })
  }
}

export function useCarePlan() {
  return useQuery({ queryKey: careKeys.plan(), queryFn: () => request<CarePlan>('/care/plan') })
}

export function useConnectedSources() {
  return useQuery({
    queryKey: careKeys.sources(),
    queryFn: async () => (await request<{ sources: ConnectedSource[] }>('/care/sources')).sources,
  })
}

export function useAppointments() {
  return useQuery({ queryKey: careKeys.appointments(), queryFn: () => request<Appointment[]>('/care/appointments') })
}

export function useAddQuestion() {
  const invalidate = useInvalidateCare()
  return useMutation({
    mutationFn: ({ text, suggestedKey }: { text: string; suggestedKey?: string }) =>
      request<DoctorQuestion>('/care/questions', { method: 'POST', body: JSON.stringify({ text, suggestedKey }) }),
    onSuccess: invalidate,
  })
}

export function useSetQuestionDone() {
  const invalidate = useInvalidateCare()
  return useMutation({
    mutationFn: ({ id, done }: { id: string; done: boolean }) =>
      request<DoctorQuestion>(`/care/questions/${encodeURIComponent(id)}/done`, { method: 'POST', body: JSON.stringify({ done }) }),
    onSuccess: invalidate,
  })
}

export function useRemoveQuestion() {
  const invalidate = useInvalidateCare()
  return useMutation({
    mutationFn: (id: string) => request<{ id: string; status: 'archived' }>(`/care/questions/${encodeURIComponent(id)}`, { method: 'DELETE' }),
    onSuccess: invalidate,
  })
}

export function useSaveAppointment() {
  const invalidate = useInvalidateCare()
  return useMutation({
    mutationFn: (body: NewAppointment) => request<Appointment>('/care/appointments', { method: 'POST', body: JSON.stringify(body) }),
    onSuccess: invalidate,
  })
}

export function useCancelAppointment() {
  const invalidate = useInvalidateCare()
  return useMutation({
    mutationFn: (id: string) => request<Appointment>(`/care/appointments/${encodeURIComponent(id)}/cancel`, { method: 'POST' }),
    onSuccess: invalidate,
  })
}
