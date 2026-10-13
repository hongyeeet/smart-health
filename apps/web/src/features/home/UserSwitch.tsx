/**
 * Who the app is showing: the demo user or Mr Tan. A round initials button that opens a small menu. The choice is kept on the device
 * and sent with every request, and switching reloads everything for the other person. (There is no "Start as new person" any more:
 * the demo user is the one to try set-up with, and it opens in set-up.)
 */
import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { href } from '@/app/routeIds'
import { useSwitchUser, useUsers } from '@/data/hooks'
import { useUi } from '@/state/store'
import { startsInSetup } from '@/features/onboarding/startGate'
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
  const { data } = useUsers()
  const switchTo = useSwitchUser()
  const [open, setOpen] = useState(false)
  const box = useRef<HTMLDivElement>(null)

  const base = data?.users ?? FALLBACK
  const users = base.map((u) =>
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
        </div>
      )}
    </div>
  )
}
