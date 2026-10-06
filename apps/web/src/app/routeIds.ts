/**
 * Route registry: the single list of every screen and sheet.
 * The router, the bottom bar, the screen index page and the link checks all read this file,
 * so the index can never drift from the app. Add a screen here first.
 */
export type RouteKind = 'tab' | 'screen' | 'sheet' | 'external'

export interface RouteLink {
  label: string
  to: string
}

export interface RouteDef {
  path: string
  title: string
  kind: RouteKind
  group: string
  from: string
  links: RouteLink[]
  note?: string
}

const l = (label: string, to: string): RouteLink => ({ label, to })

export const ROUTES = {
  A1: { path: '/welcome', title: 'Welcome', kind: 'screen', group: 'Onboarding', from: 'App start, Me (Replay onboarding)', links: [l('Next', 'A2'), l('Skip to Home', 'B1')], note: 'Language and the two consents. The data-use consent is required.' },
  A2: { path: '/welcome/eligibility', title: 'Is this app right for you?', kind: 'screen', group: 'Onboarding', from: 'A1', links: [l('Continue', 'A3'), l('Back', 'A1')], note: 'Out-of-scope answers (type 1, pregnancy, under 18) stop here with a clear message.' },
  A3: { path: '/welcome/about', title: 'About you', kind: 'screen', group: 'Onboarding', from: 'A2, A4', links: [l('Scan a label', 'H2'), l('Add by hand', 'H8'), l('Chat instead', 'A4'), l('Next', 'A5')] },
  A4: { path: '/welcome/chat', title: 'Set up by chat', kind: 'screen', group: 'Onboarding', from: 'A3', links: [l('Use the form instead', 'A3'), l('Next', 'A5')] },
  A5: { path: '/welcome/connect', title: 'Connect your data', kind: 'screen', group: 'Onboarding', from: 'A3, A4', links: [l('Finish', 'B1'), l('Back', 'A3')] },

  B1: { path: '/', title: 'Home', kind: 'tab', group: 'Home', from: 'A5, bottom bar, J1', links: [l('Alert strip', 'C2'), l('Tiles', 'C2'), l('Taken (marks the dose)', 'B1'), l('Tell us why', 'H7'), l('Log a walk', 'F1'), l('Check-in answer', 'B1'), l('What changed', 'C4'), l('Prepare for the visit', 'K3'), l('Notifications', 'B2'), l('Ask', 'I1')] },
  B2: { path: '/notifications', title: 'Notifications', kind: 'screen', group: 'Home', from: 'B1', links: [l('Each item opens its screen', 'B1')] },

  C1: { path: '/insights', title: 'Overview', kind: 'tab', group: 'Insights', from: 'Bottom bar, D1, I1', links: [l('A day in Your week', 'D1'), l('What changed', 'C2'), l('Why am I seeing this?', 'C7'), l('Ask', 'I1')] },
  C2: { path: '/insights/glucose', title: 'Glucose', kind: 'screen', group: 'Insights', from: 'B1, D1, K2, C1', links: [l('Sprint details', 'C8'), l('Why am I seeing this?', 'C7')] },
  C3: { path: '/insights/food', title: 'Food', kind: 'screen', group: 'Insights', from: 'E6, K2', links: [l('A meal', 'D1'), l('Why am I seeing this?', 'C7')] },
  C4: { path: '/insights/activity', title: 'Activity', kind: 'screen', group: 'Insights', from: 'B1, E6, K2, C1', links: [l('Log a workout', 'F1'), l('A workout', 'D1'), l('Why am I seeing this?', 'C7')] },
  C5: { path: '/insights/sleep', title: 'Sleep and stress', kind: 'screen', group: 'Insights', from: 'B1, E6, K2', links: [l('Why am I seeing this?', 'C7')] },
  C6: { path: '/insights/medication', title: 'Medication', kind: 'screen', group: 'Insights', from: 'K2, C1', links: [l('Open my medicines', 'H1'), l('Why am I seeing this?', 'C7')] },
  C7: { path: '#why', title: 'Why am I seeing this?', kind: 'sheet', group: 'Insights', from: 'Every chart in C1 to C6', links: [l('Got it', 'C1')] },
  C8: { path: '/insights/sprint', title: 'Glucose sensor sprint', kind: 'screen', group: 'Insights', from: 'C2, K4', links: [l('Your gentlest and spikiest foods', 'C3')], note: 'Start, status and end summary of a 14-day sensor sprint.' },

  D1: { path: '/day/:date', title: 'Your day', kind: 'screen', group: 'Day', from: 'C1, C3, C4, E6, E7, B1', links: [l('Any marker', 'D2'), l('Back to your week', 'C1'), l('Glucose insights', 'C2')] },
  D2: { path: '#marker', title: 'Marker detail', kind: 'sheet', group: 'Day', from: 'D1', links: [l('Close', 'D1')] },

  E1: { path: '/log', title: 'Log', kind: 'tab', group: 'Log', from: 'Centre Log button', links: [l('Workout', 'F1'), l('Meal', 'E2'), l('Symptom', 'E4'), l('Mood and sleep check-in', 'E5'), l('A recent entry', 'E7')] },
  E2: { path: '/log/meal', title: 'Log a meal', kind: 'screen', group: 'Log', from: 'E1', links: [l('Save', 'E6')] },
  E4: { path: '/log/symptom', title: 'Log a symptom', kind: 'screen', group: 'Log', from: 'E1, F1, H7', links: [l('Save', 'E6'), l('Red-flag symptom', 'J1')], note: 'Fills in the sensor reading and the time; detail is optional.' },
  E5: { path: '/log/checkin', title: 'Mood and sleep check-in', kind: 'screen', group: 'Log', from: 'E1', links: [l('Save', 'E6')] },
  E6: { path: '/log/done', title: 'Saved', kind: 'screen', group: 'Log', from: 'E2, E4, E5, F1', links: [l('See your day', 'D1'), l('The related insight', 'C2'), l('Get help now', 'J1'), l('Done', 'B1')] },
  E8: { path: '/log/ideas', title: 'Lunch ideas', kind: 'screen', group: 'Log', from: 'B1, B2 (lunch reminder)', links: [l('Log my meal', 'E2')], note: 'Up to 3 options from your own history or the Singapore food database, each with the reason.' },
  E7: { path: '#entry', title: 'Edit or delete an entry', kind: 'sheet', group: 'Log', from: 'E1 (Recent entries)', links: [l('See it in your day', 'D1')] },

  F1: { path: '/log/workout', title: 'Log a workout', kind: 'screen', group: 'Log workout', from: 'B1, E1, C4', links: [l('Live strength tracker', 'F2'), l('Log a symptom', 'E4'), l('Save', 'E6')] },

  F2: { path: '/log/workout/live', title: 'Workout tracker', kind: 'screen', group: 'Log workout', from: 'F1, E1', links: [l('Back to log', 'E1')], note: 'Live strength session: timer, exercises, sets with reps and weight, rest timer, finish and summary. Heart-rate effort is computed by the server (services/api/app/services/workout_effort.py).' },

  H1: { path: '/meds', title: 'Medications', kind: 'tab', group: 'Medications', from: 'Bottom bar, C6', links: [l('Scan a label', 'H2'), l('Add by hand', 'H8'), l('A medicine', 'H6'), l('A badge', 'H5')] },
  H2: { path: '/meds/scan', title: 'Scan a label', kind: 'screen', group: 'Medications', from: 'H1, A3', links: [l('Take photo', 'H3')] },
  H3: { path: '/meds/scan/review', title: 'Check what we read', kind: 'screen', group: 'Medications', from: 'H2', links: [l('Confirm', 'H4'), l('Retake photo', 'H2')] },
  H4: { path: '/meds/scan/plan', title: 'Your dose plan', kind: 'screen', group: 'Medications', from: 'H3', links: [l('Add to my medicines', 'H1')] },
  H5: { path: '#interaction', title: 'Possible interaction', kind: 'sheet', group: 'Medications', from: 'H4, H1 badges', links: [l('Add to my doctor questions', 'K3')] },
  H6: { path: '/meds/:id', title: 'Medicine detail', kind: 'screen', group: 'Medications', from: 'H1, I1', links: [l('Add a question', 'K3')] },
  H7: { path: '#missed', title: 'Why was it missed?', kind: 'sheet', group: 'Medications', from: 'B1 (Tell us why)', links: [l('Add a symptom', 'E4'), l('Save or skip', 'B1')] },
  H8: { path: '/meds/add', title: 'Add a medicine by hand', kind: 'screen', group: 'Medications', from: 'H1, A3', links: [l('Save', 'H1')] },

  I1: { path: '/chat', title: 'Ask Smart Health', kind: 'screen', group: 'Chat', from: 'Ask button on B1 and C1', links: [l('Add to my doctor questions', 'K3'), l('See your week', 'C1'), l('Open the Metformin page', 'H6')] },
  J1: { path: '/urgent', title: 'Low glucose alert', kind: 'screen', group: 'Urgent', from: 'E4 (red-flag symptom), the sensor alert, demo panel', links: [l('Add an emergency contact', 'K9'), l('Log a symptom', 'E4'), l("I'm okay now", 'B1')], note: 'Two tiers: low (below 4.0, treat and recheck in 15 minutes) and very low (below 3.0, call 995 and the emergency contact is alerted). No AI is involved.' },

  K1: { path: '/me', title: 'Me', kind: 'tab', group: 'Me', from: 'Bottom bar', links: [l('What Smart Health has learned', 'K2'), l('Doctor brief', 'L1'), l('Care plan', 'K3'), l('Connected sources', 'K4'), l('Language and display', 'K5'), l('Privacy and consent', 'K6'), l('Emergency contact', 'K9'), l('Data and account', 'K8'), l('Replay onboarding', 'A1')] },
  K10: { path: '/me/progress', title: 'How it is going', kind: 'screen', group: 'Me', from: 'K1', links: [l('What Smart Health has learned', 'K2')], note: 'Week by week, what the person logged and did. Not proof that the app caused a change.' },
  K2: { path: '/me/learned', title: 'What Smart Health has learned', kind: 'screen', group: 'Me', from: 'K1', links: [l('A fact\'s evidence', 'C4')] },
  K3: { path: '/me/care', title: 'Care plan', kind: 'screen', group: 'Me', from: 'K1, B1, H5, I1, H6', links: [l('Plan an appointment', 'K7'), l('Generate my doctor brief', 'L1')] },
  K4: { path: '/me/sources', title: 'Connected sources', kind: 'screen', group: 'Me', from: 'K1, B1', links: [l('Sensor sprint', 'C8')] },
  K5: { path: '/me/language', title: 'Language and display', kind: 'screen', group: 'Me', from: 'K1', links: [] },
  K6: { path: '/me/privacy', title: 'Privacy and consent', kind: 'screen', group: 'Me', from: 'K1', links: [l('Revoke access', 'K6')] },
  K7: { path: '/me/appointment', title: 'Plan an appointment', kind: 'screen', group: 'Me', from: 'K3', links: [l('Add to calendar', 'K3')] },
  K8: { path: '/me/data', title: 'Data and account', kind: 'screen', group: 'Me', from: 'K1', links: [] },

  K9: { path: '/me/contact', title: 'Emergency contact', kind: 'screen', group: 'Me', from: 'K1, J1', links: [], note: 'Who is alerted on a very low reading, and how. Needs the patient\'s consent.' },

  L1: { path: '/brief', title: 'Doctor brief', kind: 'screen', group: 'Doctor brief', from: 'K3, K1', links: [l('Share with my doctor', 'L2'), l('Open the A4 page', 'L3')] },
  L2: { path: '#share', title: 'Share with my doctor', kind: 'sheet', group: 'Doctor brief', from: 'L1', links: [l('Create link', 'L2')] },
  L3: { path: '/brief/a4', title: 'Doctor brief, A4 page', kind: 'external', group: 'Doctor brief', from: 'L1', links: [], note: 'Printable in grayscale. This is the page the doctor sees.' },

  X1: { path: '/screens', title: 'Screen index', kind: 'external', group: 'Prototype', from: 'Demo panel', links: [], note: 'Generated from the route registry.' },
} as const satisfies Record<string, RouteDef>

export type RouteId = keyof typeof ROUTES

export const routeIds = Object.keys(ROUTES) as RouteId[]

/** Builds a URL for a route id. Sheets have no URL and return the current path. */
export function href(id: RouteId, params?: Record<string, string>): string {
  const p: string = ROUTES[id].path
  if (p.startsWith('#')) return ''
  return params ? p.replace(/:([A-Za-z]+)/g, (_, k: string) => params[k] ?? '') : p
}

/** Startup check: every link in the registry points at a real id. */
export function checkRegistry(): string[] {
  const bad: string[] = []
  for (const id of routeIds) for (const link of (ROUTES[id].links as readonly RouteLink[])) if (!(link.to in ROUTES)) bad.push(`${id} -> ${link.to}`)
  return bad
}
