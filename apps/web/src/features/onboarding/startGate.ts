/**
 * Start-up: a person started with "Start as new person" (their key begins `person-`) who has not finished setup is taken to Welcome
 * when the app opens on Home. The loaded demo patient (`mr-tan`) is never sent there.
 *
 * The demo user (`demo`) always starts in set-up: when the app opens on Home as the demo user, and every time someone switches to the
 * demo user. Set-up shows "Skip" instead of "Finish later" for the demo user, so a tester can go straight to the app.
 *
 * "Finished" is read from the saved record: the data-use consent is on and the profile exists (GET /onboarding).
 */
import type { SavedOnboarding } from './api'

export const NEW_PERSON_PREFIX = 'person-'
export const DEMO_USER = 'demo'

/** True for the demo user: set-up opens first, and its link out reads "Skip". */
export const startsInSetup = (userKey: string) => userKey === DEMO_USER

/** True when this person still has to finish setup. Only people started as new persons can be sent back to setup. */
export function needsSetup(userKey: string, saved: Pick<SavedOnboarding, 'dataConsent' | 'profile'>): boolean {
  if (!userKey.startsWith(NEW_PERSON_PREFIX)) return false
  return !(saved.dataConsent && saved.profile !== null)
}
