/**
 * Which banner the Log page opens with. One banner, chosen from what is true right now, in this order:
 *   eating   a meal was started and not finished (the timer banner)
 *   meal     it is a meal's usual window and no meal is logged yet
 *   symptom  a symptom was logged in the last 24 hours: ask for an update
 *   due      another log is inside its usual window (mood and sleep, workout) and not done
 *   bp       no blood pressure reading today, from mid-morning
 *   done     everything for today is logged
 *   calm     nothing is due: a plain invitation
 * A pure function, so the order is easy to read and to test.
 */
import type { LogProgress, MenuMeal, ProgressItem, RecentEntry } from '@/data/types'

export type Banner =
  | { kind: 'eating' }
  | { kind: 'meal'; meal: MenuMeal; window: string | null }
  | { kind: 'symptom'; entry: RecentEntry }
  | { kind: 'due'; item: ProgressItem }
  | { kind: 'bp' }
  | { kind: 'done' }
  | { kind: 'calm' }

export interface BannerInput {
  progress: LogProgress | undefined
  recent: RecentEntry[] | undefined
  eating: boolean
  /** the meal that fits the time of day */
  nowMeal: MenuMeal
  /** hour of the day in Singapore, 0 to 23 */
  hour: number
  /** today and yesterday as YYYY-MM-DD in Singapore */
  today: string
  yesterday: string
  /** the time now as minutes since midnight, to tell if a symptom is within 24 hours when it was yesterday */
  nowMin: number
}

export function pickBanner(i: BannerInput): Banner {
  if (i.eating) return { kind: 'eating' }
  const items = i.progress?.items ?? []
  const meals = items.find((x) => x.key === 'meals')
  if (meals && meals.status === 'due') return { kind: 'meal', meal: i.nowMeal, window: meals.window ?? null }

  // a symptom from the last 24 hours (today, or yesterday and not earlier than the same clock time)
  const sym = (i.recent ?? []).find((e) => e.kind === 'symptom' && (e.date === i.today || (e.date === i.yesterday && clockMin(e.when) >= i.nowMin)))
  if (sym) return { kind: 'symptom', entry: sym }

  const due = items.find((x) => x.key !== 'meals' && x.key !== 'symptom' && x.status === 'due')
  if (due) return { kind: 'due', item: due }

  if (i.progress && i.progress.bloodPressure.count === 0 && i.hour >= 9) return { kind: 'bp' }
  if (i.progress && i.progress.total > 0 && i.progress.done >= i.progress.total) return { kind: 'done' }
  return { kind: 'calm' }
}

/** "6:40 pm" to minutes since midnight; 0 when the text is not a clock time (older entries show a date). */
export function clockMin(when: string): number {
  const m = /^(\d{1,2}):(\d{2})\s*(am|pm)$/i.exec(when.trim())
  if (!m) return 0
  return ((Number(m[1]) % 12) + (m[3]!.toLowerCase() === 'pm' ? 12 : 0)) * 60 + Number(m[2])
}
