import i18n from '@/i18n'
import { dateLocale } from '@/lib/locale'

/** Quick checks on the phone; the server has the final say. Spaces and dashes are allowed, as the server allows them. */
export const PHONE_RE = /^\+?\d{7,15}$/
export const EMAIL_RE = /^[^@\s]+@[^@\s]+\.[^@\s]+$/

export const cleanPhone = (raw: string) => raw.replace(/[ -]/g, '')

export function phoneError(raw: string): string | undefined {
  if (!raw.trim()) return undefined
  return PHONE_RE.test(cleanPhone(raw))
    ? undefined
    : i18n.t('me.rules.phone', 'Check the phone number. Use digits only, with an optional + at the start.')
}

export function emailError(raw: string): string | undefined {
  const v = raw.trim()
  if (!v) return undefined
  return v.length <= 254 && EMAIL_RE.test(v) ? undefined : i18n.t('me.rules.email', 'Check the email address. It should look like name@example.com.')
}

/** Mirrors the server rule: a contact needs a name plus a phone or an email, or nothing at all. */
export function contactProblem(f: { name: string; relation: string; phone: string; email: string }): string | undefined {
  const anything = [f.name, f.relation, f.phone, f.email].some((v) => v.trim())
  if (!anything) return undefined
  if (!f.name.trim()) return i18n.t('me.rules.contactName', 'Add the name of your emergency contact.')
  if (!f.phone.trim() && !f.email.trim()) return i18n.t('me.rules.contactReach', 'Add a phone number or an email address, so we can reach this person.')
  return undefined
}

const dateFmt = () => new Intl.DateTimeFormat(dateLocale('en-SG'), { day: 'numeric', month: 'short', year: 'numeric' })

/** "3 Oct 2026". Dates are shown in words, never as numbers only. */
export const fmtDate = (iso: string) => dateFmt().format(new Date(iso))
