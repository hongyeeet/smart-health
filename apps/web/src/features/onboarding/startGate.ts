/**
 * Start-up: a person started with "Start as new person" (their key begins `person-`) who has not finished setup is taken to Welcome
 * when the app opens on Home. The demo user (`demo`) and the loaded demo patient (`mr-tan`) are never sent there.
 *
 * "Finished" is read from the saved record: the data-use consent is on and the profile exists (GET /onboarding).
 */
import type { SavedOnboarding } from './api'

export const NEW_PERSON_PREFIX = 'person-'

/** True when this person still has to finish setup. Only people started as new persons can be sent back to setup. */
export function needsSetup(userKey: string, saved: Pick<SavedOnboarding, 'dataConsent' | 'profile'>): boolean {
  if (!userKey.startsWith(NEW_PERSON_PREFIX)) return false
  return !(saved.dataConsent && saved.profile !== null)
}
