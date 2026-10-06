/**
 * Who the app is showing: the demo user or Mr Tan. A round initials button that opens a small menu. The choice is kept on the
 * device and sent with every request, and switching reloads everything for the new person.
 */
import { useEffect, useRef, useState } from 'react'
import { useSwitchUser, useUsers } from '@/data/hooks'
import { useUi } from '@/state/store'
import { cn } from '@/lib/cn'
import { Check } from '@/ui/icons'

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
  const current = useUi((s) => s.userKey)
  const { data } = useUsers()
  const users = data?.users ?? FALLBACK
  const me = users.find((u) => u.key === current) ?? users[0]
  const switchTo = useSwitchUser()
  const [open, setOpen] = useState(false)
  const box = useRef<HTMLDivElement>(null)

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
        aria-label={`Viewing as ${me.label}. Switch person`}
        className="press flex h-12 w-12 items-center justify-center rounded-full bg-brand-soft font-serif text-sub font-semibold text-brand ring-1 ring-line"
      >
        {initials(me.label)}
      </button>
      {open && (
        <div role="menu" aria-label="Switch person" className="absolute right-0 top-14 z-30 w-[min(18rem,calc(100vw-2.5rem))] rounded-card border border-line bg-card p-1.5 shadow-lift">
          <p className="px-3 pb-1 pt-2 text-micro font-bold uppercase tracking-wide text-ink3">Viewing as</p>
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
                  if (!on) switchTo(u.key)
                }}
                className={cn('press flex min-h-14 w-full items-center gap-3 rounded-[12px] px-3 py-2', on ? 'bg-brand-soft' : 'hover:bg-well')}
              >
                <span className={cn('flex h-10 w-10 flex-none items-center justify-center rounded-full font-serif text-sub font-semibold', on ? 'bg-brand text-on-brand' : 'bg-well text-ink2')}>{initials(u.label)}</span>
                <span className="min-w-0 flex-1">
                  <span className="block text-body font-bold leading-snug">{u.label}</span>
                  <span className="block text-sub leading-snug text-ink2">{u.sub}</span>
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
