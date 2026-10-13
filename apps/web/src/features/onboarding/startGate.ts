/**
 * Start-up: the demo user (`demo`) always starts in set-up: when the app opens on Home as the demo user, and every time someone
 * switches to the demo user. Set-up shows "Skip" instead of "Finish later" for the demo user, so a tester can go straight to the app.
 * The loaded demo patient (`mr-tan`) is never sent there. There is no "Start as new person" any more (removed 2026-10-13).
 */
export const DEMO_USER = 'demo'

/** True for the demo user: set-up opens first, and its link out reads "Skip". */
export const startsInSetup = (userKey: string) => userKey === DEMO_USER
