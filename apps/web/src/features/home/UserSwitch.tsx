/**
 * Who the app is showing: the demo user, Mr Tan, or a new person started on this device. A round initials button that opens a small
 * menu. The choice is kept on the device and sent with every request, and switching reloads everything for the new person.
 *
 * "Start as new person" opens set-up for "New User N" with the same pages as the demo user. The person is created only when set-up is
 * finished; leaving set-up first (Cancel, or choosing another person here) drops them (newPerson.ts).
 */
import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { href } from '@/app/routeIds'
import { useSwitchUser, useUsers } from '@/data/hooks'
import { useUi } from '@/state/store'
import { startsInSetup } from '@/features/onboarding/startGate'
import { useStartNewPerson } from '@/features/onboarding/newPerson'
import { cn } from '@/lib/cn'
import { Check } from '@/ui/icons'

/** Shown only until the people list has loaded (the server's labels). */
const FALLBACK = [
  { key: 'demo', label: 'Demo user', sub: 'A blank account for trying things' },
  { key: 'mr-tan', label: 'Mr Tan', sub: 'About 90 days of history' },
]

const initials = (label: string) =>
  label
    .split(/\s+/)
    .map((w) => w[0])
    .join('')
    .slice(0, 2)
    .toUpperCase()

export function UserSwitch() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const current = useUi((s) => s.userKey)
  const people = useUi((s) => s.people)
  const pending = useUi((s) => s.pending)
  const { data } = useUsers()
  const switchTo = useSwitchUser()
  const startNew = useStartNewPerson()
  const [open, setOpen] = useState(false)
  const box = useRef<HTMLDivElement>(null)

  /* the server's people, then the people started on this device, then the one whose set-up is open */
  const base = data?.users ?? FALLBACK
  const started = [
    ...people.filter((p) => !base.some((u) => u.key === p.key)).map((p) => ({ key: p.key, label: p.label, sub: t('switch.startedHere', 'Started on this device') })),
    ...(pending ? [{ key: pending.key, label: pending.label, sub: t('switch.settingUp', 'Setting up. Not saved yet') }] : []),
  ]
  const users = [...base, ...started].map((u) =>
    u.key === 'demo' ? { ...u, label: t('switch.user.demo', 'Demo user'), sub: t('switch.user.demoSub', 'A blank account for trying things') } : u.key === 'mr-tan' ? { ...u, sub: t('switch.user.tanSub', 'About 90 days of history') } : u,
  )
  const me = users.find((u) => u.key === current) ?? { key: current, label: t('switch.person', 'Person'), sub: '' }

  useEffect(() => {
    if (!open) return
    const onDown = (e: PointerEvent) => {
      if (!box.current?.contains(e.target as Node)) setOpen(false)
    }
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false)
    }
    document.addEventListener('pointerdown', onDown)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('pointerdown', onDown)
      document.removeEventListener('keydown', onKey)
    }
  }, [open])

  return (
    <div ref={box} className="relative">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label={t('switch.viewing', 'Viewing as {{name}}. Switch person', { name: me.label })}
        className="press flex h-12 min-w-12 items-center justify-center whitespace-nowrap rounded-full bg-brand-soft px-2 font-serif text-sub font-semibold text-brand ring-1 ring-line"
      >
        {initials(me.label)}
      </button>
      {open && (
        <div role="menu" aria-label={t('switch.menu', 'Switch person')} className="absolute right-0 top-14 z-30 w-[min(18rem,calc(100vw-2.5rem))] rounded-card border border-line bg-card p-1.5 shadow-lift">
          <p className="px-3 pb-1 pt-2 text-sub font-bold text-ink3">{t('switch.viewingAs', 'Viewing as')}</p>
          {users.map((u) => {
            const on = u.key === me.key
            return (
              <button
                key={u.key}
                type="button"
                role="menuitemradio"
                aria-checked={on}
                onClick={() => {
                  setOpen(false)
                  if (!on) {
                    switchTo(u.key)
                    if (startsInSetup(u.key)) navigate(href('A1'), { replace: true })      // the demo user starts in set-up, with a Skip link
                  }
                }}
                className={cn('press flex min-h-14 w-full items-center gap-3 rounded-[12px] px-3 py-2', on ? 'bg-brand-soft' : 'hover:bg-well')}
              >
                <span className={cn('flex h-10 w-10 flex-none items-center justify-center rounded-full font-serif text-sub font-semibold', on ? 'bg-brand text-on-brand' : 'bg-well text-ink2')}>{initials(u.label)}</span>
                <span className="min-w-0 flex-1">
                  <span className="block text-body font-bold leading-snug">{u.label}</span>
                  {u.sub && <span className="block text-sub leading-snug text-ink2">{u.sub}</span>}
                </span>
                {on && <Check size={20} weight="bold" className="flex-none text-brand" aria-hidden />}
              </button>
            )
          })}
          <div className="mt-1 border-t border-line pt-1">
            <button
              type="button"
              role="menuitem"
              onClick={() => {
                setOpen(false)
                startNew(t('switch.newUserN', 'New User {{n}}', { n: people.length + 1 }))
              }}
              className="press flex min-h-14 w-full flex-col items-start gap-0.5 rounded-[12px] px-3 py-2 text-left hover:bg-well"
            >
              <span className="text-body font-bold leading-snug">{t('switch.startNew', 'Start as new person')}</span>
              <span className="text-sub leading-snug text-ink2">{t('switch.startNewSubV2', 'Set-up from step 1, like the demo user. Saved only when you finish.')}</span>
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
