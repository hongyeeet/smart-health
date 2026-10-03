/**
 * App-level configuration. Anything a deployment or a demo may want to change lives here,
 * not inside screens. Clinical thresholds are placeholders and are marked as pending clinical review.
 */
export const appConfig = {
  name: 'Smart Health',
  /** the demo clock: Thursday 1 October 2026, 7:50 pm */
  demo: { today: '2026-10-01', nowMinutes: 19 * 60 + 50, weekday: 'Thursday', dateLabel: 'Thursday 1 October' },
  /** clinical review pending: these are placeholders, never presented as advice */
  glucoseRanges: { veryLow: 3.0, low: 3.9, high: 10.0, veryHigh: 13.9, unit: 'mmol/L' },
  /** alert tiers for low glucose. Placeholders from the owner (2026-10-03); clinical validation pending, never shown as advice */
  hypoTiers: { low: 4.0, veryLow: 3.0, recheckMinutes: 15, contactCallAfterMinutes: 5 },
  goals: { moderateMinutes: 150, strengthSessions: 2, source: 'Default. Set with your doctor.' },
  shareLinkHours: 72,
  reminderRecheckMinutes: 15,
  emergencyNumber: '995',
  /** prototype-only controls, shown in the Demo panel and never inside the phone */
  demoTools: true,
  locales: [
    { code: 'en', label: 'English', native: 'English' },
    { code: 'zh', label: 'Chinese', native: '中文' },
    { code: 'ms', label: 'Malay', native: 'Bahasa Melayu' },
    { code: 'ta', label: 'Tamil', native: 'தமிழ்' },
  ],
} as const
