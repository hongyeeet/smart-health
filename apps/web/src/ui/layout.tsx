import { useEffect, useRef, type ReactNode } from 'react'
import { motion } from 'motion/react'
import { useTranslation } from 'react-i18next'
import { cn } from '@/lib/cn'
import { duration, ease } from '@/motion/tokens'
import { useBack } from '@/app/navigation'
import type { RouteId } from '@/app/routeIds'
import { ArrowLeft } from './icons'

/**
 * Scroll container for one screen. Padding at the bottom leaves room for the tab bar, and on tab screens for the floating Ask button above it
 * (a page with a Footer or Dock has no bottom padding: that bar carries its own, and sticks to the true bottom edge).
 * Content is centred and capped: 720 px on a tablet, 1040 px on a laptop and above. A form or a single-task page passes `narrow` to stay at 640 px; a page of wide charts passes `wide` to grow to 1280 px on a big screen.
 */
export function Screen({ children, tabs = false, className, tone = 'canvas', narrow = false, wide = false }: { children: ReactNode; tabs?: boolean; className?: string; tone?: 'canvas' | 'urgent'; narrow?: boolean; wide?: boolean }) {
  const ref = useRef<HTMLDivElement>(null)
  useEffect(() => {
    ref.current?.scrollTo({ top: 0 })
  }, [])
  return (
    <div ref={ref} className={cn('hide-scroll scroll-area absolute inset-0 overflow-y-auto overflow-x-hidden px-5 pt-1', tabs ? 'pb-[calc(var(--tab-space)+var(--ask-space,0px)+1rem)] md:pb-10' : 'pb-[calc(2.5rem+env(safe-area-inset-bottom))]', 'has-[[data-dock]]:pb-0 md:px-8', tone === 'urgent' && 'bg-urgent pt-4', className)}>
      <div className={cn('mx-auto flex w-full flex-col gap-4', narrow ? 'md:max-w-[640px]' : cn('md:max-w-[720px] lg:max-w-[1040px]', wide && 'xl:max-w-[1280px]'))}>{children}</div>
    </div>
  )
}

/** Title row (back button, title, trailing control). The one-line description sits under the row and runs the full width, so a trailing control never squeezes it. */
export function Header({ title, back, backTo, trailing, sub }: { title: ReactNode; back?: boolean; backTo?: RouteId; trailing?: ReactNode; sub?: ReactNode }) {
  const goBack = useBack(backTo)
  const { t } = useTranslation()
  return (
    <header className="flex flex-col pb-1 pt-1">
      <div className="flex items-start gap-2">
        {back && (
          <button type="button" onClick={goBack} aria-label={t('common.back', 'Back')} className="press -ml-3 flex h-12 w-12 flex-none items-center justify-center rounded-full text-ink hover:bg-well">
            <ArrowLeft size={26} aria-hidden />
          </button>
        )}
        <div className="min-w-0 flex-1 pt-1.5">
          <h1 className="break-words font-serif text-h1 font-medium tracking-tight text-ink">{title}</h1>
        </div>
        {trailing && <div className="flex-none pt-0.5">{trailing}</div>}
      </div>
      {sub && <p className={cn('mt-1 text-sub text-ink2', back && 'pl-11')}>{sub}</p>}
    </header>
  )
}

/** Bottom action area that stays on screen above the keyboard-free bottom edge. */
export function Footer({ children }: { children: ReactNode }) {
  return (
    <div data-dock className="sticky bottom-0 -mx-5 mt-2 flex flex-col gap-2 bg-gradient-to-t from-canvas from-70% to-transparent px-5 pb-[max(1.5rem,env(safe-area-inset-bottom))] pt-6 md:-mx-8 md:flex-row md:items-center md:px-8 md:[&>*]:flex-1 md:[&>p]:flex-none">
      {children}
    </div>
  )
}

/** Stacks on a phone and tablet, two columns on a laptop. Put the main content first. */
export function Split({ children, className }: { children: ReactNode; className?: string }) {
  // min-w-0: a grid item will not shrink below its content by default, so one wide chart could push the whole page past a phone's edge
  return <div className={cn('grid gap-4 lg:grid-cols-2 lg:items-start lg:gap-6 [&>*]:min-w-0', className)}>{children}</div>
}

/**
 * A list of tiles: one column on a phone, two on a tablet, three on a laptop (`cols={2}`: two on both), every tile in a row the same height.
 * With `spread`, a last row that would leave a gap is filled: one tile left takes the whole row, and with three columns two left take half each.
 * Children must be `<li>`.
 */
export function TileGrid({ children, spread = false, cols = 3, className }: { children: ReactNode; spread?: boolean; cols?: 2 | 3; className?: string }) {
  return (
    <ul
      className={cn(
        'grid grid-cols-1 items-stretch gap-3 md:grid-cols-2 md:gap-4 [&>li]:min-w-0',
        cols === 3 && 'lg:grid-cols-6 lg:[&>li]:col-span-2',
        spread && 'md:[&>li:last-child:nth-child(odd)]:col-span-2',
        spread && cols === 3 && 'lg:[&>li:last-child:nth-child(3n+1)]:col-span-6! lg:[&>li:last-child:nth-child(3n+2)]:col-span-3! lg:[&>li:nth-last-child(2):nth-child(3n+1)]:col-span-3!',
        className,
      )}
    >
      {children}
    </ul>
  )
}

const seen = new Set<string>()
/** Entrance for the first time a section is seen. Rare, so it can be a little decorative; never on revisits. */
export function Reveal({ id, i = 0, children, className }: { id: string; i?: number; children: ReactNode; className?: string }) {
  const first = !seen.has(id)
  useEffect(() => {
    seen.add(id)
  }, [id])
  return (
    <motion.div className={className} initial={first ? { opacity: 0, y: 8 } : false} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3, ease: ease.out, delay: first ? i * duration.stagger : 0 }}>
      {children}
    </motion.div>
  )
}
