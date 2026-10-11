/**
 * The "See more" fold on Home. Collapsed by default; the choice is remembered per device (localStorage). If storage is blocked the
 * fold simply starts closed each visit.
 */
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { cn } from '@/lib/cn'
import { CaretDown } from '@/ui/icons'

const KEY = 'smart-health-home-more'

export function useSeeMore(): [boolean, () => void] {
  const [open, setOpen] = useState(() => {
    try {
      return window.localStorage.getItem(KEY) === 'open'
    } catch {
      return false
    }
  })
  const toggle = () => {
    const next = !open
    setOpen(next)
    try {
      window.localStorage.setItem(KEY, next ? 'open' : 'closed')
    } catch {
      /* storage is blocked: the fold still works for this visit */
    }
  }
  return [open, toggle]
}

export function SeeMoreButton({ open, onToggle }: { open: boolean; onToggle: () => void }) {
  const { t } = useTranslation()
  return (
    <button
      type="button"
      onClick={onToggle}
      aria-expanded={open}
      aria-controls="home-more"
      className="press flex min-h-12 w-full items-center justify-between gap-3 rounded-card border border-line bg-card px-4 py-3 text-left text-body font-bold"
    >
      {open ? t('home.more.less', 'See less') : t('home.more.more', 'See more')}
      <CaretDown size={20} className={cn('flex-none text-ink3 transition-transform duration-200', open && 'rotate-180')} aria-hidden />
    </button>
  )
}
