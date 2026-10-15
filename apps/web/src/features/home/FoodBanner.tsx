/**
 * The data and the "dismissed today" storage behind Home's food banner (the banner itself is in HomeBanners.tsx).
 * The choice of meal or habit is made by the server (GET /home/banner); the words are written in HomeBanners, with no advice in them.
 * A dismissed banner is hidden for the rest of the day for that person on this device only.
 */
import { useQuery } from '@tanstack/react-query'
import { request } from '@/data/repositories/http'

export interface HomeFoodBanner {
  /** the mealtime that is open now and not logged yet, or null */
  meal: 'breakfast' | 'lunch' | 'dinner' | null
  /** a food habit high in salt or sugar (the same habits as GET /nutrition/flags), or null */
  flag: { kind: 'salt' | 'sugar'; type: string; label: string; n: number } | null
}

export function useFoodBanner() {
  return useQuery({ queryKey: ['homeBanner'], queryFn: () => request<HomeFoodBanner>('/home/banner'), refetchInterval: 60_000 })
}

/** One copy per person on this device, so one person's "Not now" never hides the banner for another. */
const STORE = 'smart-health-home-banners'
const storeKey = (user: string) => `${STORE}:${user}`

// the old copy had no person in its key; it is dropped, not moved
try {
  window.localStorage.removeItem(STORE)
} catch {
  /* storage is blocked: nothing to remove */
}

function todayKey(): string {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

/** Banner ids this person dismissed today on this device, read from { [bannerId]: 'YYYY-MM-DD' }. If storage is blocked, nothing is hidden. */
export function dismissedToday(user: string): Set<string> {
  try {
    const map = JSON.parse(window.localStorage.getItem(storeKey(user)) ?? '{}') as Record<string, string>
    const today = todayKey()
    return new Set(Object.entries(map).filter(([, day]) => day === today).map(([id]) => id))
  } catch {
    return new Set()
  }
}

export function rememberDismissed(user: string, id: string) {
  try {
    const map = JSON.parse(window.localStorage.getItem(storeKey(user)) ?? '{}') as Record<string, string>
    window.localStorage.setItem(storeKey(user), JSON.stringify({ ...map, [id]: todayKey() }))
  } catch {
    /* storage is blocked: the banner comes back on the next visit, which is harmless */
  }
}
