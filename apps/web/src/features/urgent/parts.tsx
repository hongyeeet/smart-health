import { useEffect, useState } from 'react'
import i18n from '@/i18n'

/** A clock that ticks every second so countdowns and "minutes ago" stay true between the 15-second polls. */
export function useNow(everyMs = 1000) {
  const [now, setNow] = useState(() => Date.now())
  useEffect(() => {
    const t = window.setInterval(() => setNow(Date.now()), everyMs)
    return () => window.clearInterval(t)
  }, [everyMs])
  return now
}

export function minutesAgo(since: string | null, now: number): number | null {
  if (!since) return null
  return Math.max(0, Math.floor((now - new Date(since).getTime()) / 60_000))
}

export function agoText(min: number | null): string {
  if (min === null) return ''
  if (min < 1) return i18n.t('urgent.justNow', 'just now')
  // Two sentences, not a plural join, so each language can word its own plural.
  return min === 1 ? i18n.t('urgent.oneMinuteAgo', '1 minute ago') : i18n.t('urgent.minutesAgo', '{{n}} minutes ago', { n: min })
}

/** Seconds left until a time, never below zero. */
export function secondsUntil(iso: string | null, now: number): number {
  if (!iso) return 0
  return Math.max(0, Math.ceil((new Date(iso).getTime() - now) / 1000))
}

export function clock(totalSeconds: number): string {
  const m = Math.floor(totalSeconds / 60)
  const s = totalSeconds % 60
  return `${m}:${String(s).padStart(2, '0')}`
}

/** Strip anything but digits and a leading plus so a stored phone number always makes a valid tel: link. */
export function telHref(phone: string): string {
  return `tel:${phone.replace(/[^\d+]/g, '')}`
}

/** A link that looks like a Button (a real <a> so the phone dialler opens). */
export function CallLink({ href, children, primary, label }: { href: string; children: React.ReactNode; primary?: boolean; label?: string }) {
  return (
    <a
      href={href}
      aria-label={label}
      className={`press flex min-h-14 w-full items-center justify-center gap-2 rounded-[14px] border-2 px-4 py-3 text-center text-body font-bold ${
        primary ? 'border-transparent bg-danger text-card' : 'border-danger bg-card text-danger'
      }`}
    >
      {children}
    </a>
  )
}
