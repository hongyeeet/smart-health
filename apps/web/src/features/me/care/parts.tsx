/** Small pieces shared by K3, K4 and K7: the status words, Singapore dates and the plain card for one visit. */
import { StatusPill, type Tone } from '@/ui/primitives'
import { CheckCircle, Clock, Question, WarningCircle, type IconType } from '@/ui/icons'
import type { Preventive } from './api'

const PREVENTIVE: Record<Preventive['status'], { tone: Tone; word: string; icon: IconType }> = {
  overdue: { tone: 'danger', word: 'Overdue', icon: WarningCircle },
  due_soon: { tone: 'warn', word: 'Due soon', icon: Clock },
  ok: { tone: 'ok', word: 'Up to date', icon: CheckCircle },
  unknown: { tone: 'neutral', word: 'No date yet', icon: Question },
}

/** The word and icon say the status; colour only adds emphasis. */
export function PreventiveStatusPill({ status }: { status: Preventive['status'] }) {
  const s = PREVENTIVE[status]
  return (
    <StatusPill tone={s.tone} icon={s.icon}>
      {s.word}
    </StatusPill>
  )
}

const SG_STAMP = new Intl.DateTimeFormat('en-GB', { timeZone: 'Asia/Singapore', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit', hour12: false })

/** "29 Sep, 20:00" in Singapore time, for "You confirmed this on ...". */
export function singaporeStamp(iso: string): string {
  return SG_STAMP.format(new Date(iso)).replace(',', '')
}

/** Today's date in Singapore as YYYY-MM-DD, so the form's default day is right whatever the device clock zone. */
export function singaporeToday(): string {
  return new Intl.DateTimeFormat('sv-SE', { timeZone: 'Asia/Singapore' }).format(new Date())
}

/** The form's local Singapore time as an instant. Singapore has no daylight time, so +08:00 is always right. */
export function singaporeInstant(date: string, time: string): number {
  return new Date(`${date}T${time}:00+08:00`).getTime()
}
