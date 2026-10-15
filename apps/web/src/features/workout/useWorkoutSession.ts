import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { Felt, WorkoutExercise, WorkoutSession, WorkoutSet } from '@/data/types'

const uid = () => (typeof crypto !== 'undefined' && 'randomUUID' in crypto ? crypto.randomUUID() : String(Date.now() + Math.random()))

interface State {
  session: WorkoutSession | null
  /** finished sessions that have not reached the server yet */
  pending: WorkoutSession[]
  clearPending: (id: string) => void
  /** when the current rest period ends (epoch ms), or null */
  restUntil: number | null
  start: () => void
  addExercise: (name: string) => string
  removeExercise: (id: string) => void
  addSet: (exerciseId: string, reps: number, weightKg: number | null) => void
  removeSet: (exerciseId: string, setId: string) => void
  startRest: (seconds: number) => void
  stopRest: () => void
  finish: (felt?: Felt, note?: string) => WorkoutSession | null
  discard: () => void
}

/**
 * The live session lives on the device (and survives a refresh) until it is finished and saved. It holds only
 * what the person typed and the times; every calculated number comes back from the server after saving.
 */
export const useWorkoutSession = create<State>()(
  persist(
    (set, get) => ({
      session: null,
      pending: [],
      clearPending: (id) => set((s) => ({ pending: s.pending.filter((p) => p.id !== id) })),
      restUntil: null,
      start: () => set({ session: { id: uid(), startedAt: new Date().toISOString(), exercises: [] }, restUntil: null }),
      addExercise: (name) => {
        const id = uid()
        set((s) => (s.session ? { session: { ...s.session, exercises: [...s.session.exercises, { id, name, sets: [] } as WorkoutExercise] } } : s))
        return id
      },
      removeExercise: (id) => set((s) => (s.session ? { session: { ...s.session, exercises: s.session.exercises.filter((e) => e.id !== id) } } : s)),
      addSet: (exerciseId, reps, weightKg) =>
        set((s) =>
          s.session
            ? {
                session: {
                  ...s.session,
                  exercises: s.session.exercises.map((e) => (e.id === exerciseId ? { ...e, sets: [...e.sets, { id: uid(), reps, weightKg, doneAt: new Date().toISOString() } as WorkoutSet] } : e)),
                },
              }
            : s,
        ),
      removeSet: (exerciseId, setId) =>
        set((s) => (s.session ? { session: { ...s.session, exercises: s.session.exercises.map((e) => (e.id === exerciseId ? { ...e, sets: e.sets.filter((x) => x.id !== setId) } : e)) } } : s)),
      startRest: (seconds) => set({ restUntil: Date.now() + seconds * 1000 }),
      stopRest: () => set({ restUntil: null }),
      finish: (felt, note) => {
        const s = get().session
        if (!s) return null
        const done: WorkoutSession = { ...s, endedAt: new Date().toISOString(), felt, note }
        set((st) => ({ session: null, restUntil: null, pending: [...st.pending, done] }))
        return done
      },
      discard: () => set({ session: null, restUntil: null }),
    }),
    { name: 'smart-health-workout', partialize: (s) => ({ session: s.session, pending: s.pending }) },
  ),
)
