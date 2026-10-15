/**
 * "Start as new person". The person's key is made on this device when set-up opens (`person-` and 12 hex digits). While they answer the
 * questions nothing is saved for them on the server: the answers stay on this device. Only when they finish does the app create them
 * (POST /users) and save everything. If they leave set-up first (Cancel, switching person, or going to another screen) they are
 * dropped: the key and the answers on this device are removed, and the app goes back to the person it was showing before.
 */
import { useNavigate } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { href } from '@/app/routeIds'
import { request } from '@/data/repositories/http'
import { useUi } from '@/state/store'
import { clearDeviceCopy } from './useOnboarding'

export function newPersonKey(): string {
  const bytes = crypto.getRandomValues(new Uint8Array(6))
  return `person-${Array.from(bytes, (b) => b.toString(16).padStart(2, '0')).join('')}`
}

/** True while the person being shown is a new person whose set-up is not finished (nothing is saved for them yet). */
export const useIsNewPerson = () => useUi((s) => s.pending !== null && s.userKey === s.pending.key)

/** Drops the new person whose set-up is open, unless `nextKey` is that person. Does not change who is shown. */
export function dropPendingPerson(nextKey?: string) {
  const { pending, setPending } = useUi.getState()
  if (!pending || pending.key === nextKey) return
  clearDeviceCopy(pending.key)
  setPending(null)
}

/** Opens set-up for a new person (label "New User N"). The person shown before comes back if set-up is cancelled. */
export function useStartNewPerson() {
  const qc = useQueryClient()
  const navigate = useNavigate()
  return (label: string) => {
    const ui = useUi.getState()
    const returnTo = ui.pending?.returnTo ?? ui.userKey
    dropPendingPerson()
    const key = newPersonKey()
    clearDeviceCopy(key)
    ui.setPending({ key, label, returnTo })
    ui.setUserKey(key)
    void qc.resetQueries()
    navigate(href('A1'), { replace: true })
  }
}

/** Leaves set-up without finishing: the new person is dropped and the person shown before comes back. */
export function useCancelNewPerson() {
  const qc = useQueryClient()
  const navigate = useNavigate()
  return () => {
    const { pending } = useUi.getState()
    if (!pending) return
    dropPendingPerson()
    useUi.getState().setUserKey(pending.returnTo)
    void qc.resetQueries()
    navigate(href('B1'), { replace: true })
  }
}

/** Finish, first part: makes the new person in the database so their answers can be saved. Throws if the server refused. */
export async function createPendingPerson(): Promise<void> {
  const { pending } = useUi.getState()
  if (!pending) return
  await request('/users', { method: 'POST', body: JSON.stringify({ key: pending.key }) })
}

/** Finish, second part (everything is saved): the new person is now a normal person on this device and is listed in the switcher. */
export function confirmPendingPerson() {
  const ui = useUi.getState()
  if (!ui.pending) return
  ui.addPerson({ key: ui.pending.key, label: ui.pending.label })
  ui.setPending(null)
}
