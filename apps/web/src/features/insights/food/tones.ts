/**
 * Colour coding for the Food page: the same tokens as the Health overview (ok, brass, warn) and a neutral well. Colour carries the
 * status; no words are added here.
 */
export type Tone = 'ok' | 'brass' | 'warn' | 'neutral'
export type RiseTone = Exclude<Tone, 'neutral'>

export const TONE: Record<Tone, { bg: string; fg: string }> = {
  ok: { bg: 'bg-ok-soft', fg: 'text-ok' },
  brass: { bg: 'bg-brass-soft', fg: 'text-brass' },
  warn: { bg: 'bg-warn-soft', fg: 'text-warn' },
  neutral: { bg: 'bg-well', fg: 'text-ink2' },
}

/** The colour of a rise after a meal, in mmol/L: 5 and up warn, 3 and up brass, under 3 ok. */
export const riseTone = (rise: number): RiseTone => (rise >= 5 ? 'warn' : rise >= 3 ? 'brass' : 'ok')
