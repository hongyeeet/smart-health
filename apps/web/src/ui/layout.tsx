import { useEffect, useRef, type ReactNode } from 'react'
import { motion } from 'motion/react'
import { cn } from '@/lib/cn'
import { duration, ease } from '@/motion/tokens'
import { useBack } from '@/app/navigation'
import type { RouteId } from '@/app/routeIds'
import { ArrowLeft } from './icons'

/** Scroll container for one screen. Padding at the bottom leaves room for the tab bar. */
export function Screen({ children, tabs = false, className, tone = 'canvas' }: { children: ReactNode; tabs?: boolean; className?: string; tone?: 'canvas' | 'urgent' }) {
  const ref = useRef<HTMLDivElement>(null)
  useEffect(() => {
    ref.current?.scrollTo({ top: 0 })
  }, [])
  return (
    <div ref={ref} className={cn('hide-scroll scroll-area absolute inset-0 overflow-y-auto overflow-x-hidden px-5 pt-1', tabs ? 'pb-[calc(8rem+env(safe-area-inset-bottom))] md:pb-10' : 'pb-[calc(2.5rem+env(safe-area-inset-bottom))]', 'md:px-8', tone === 'urgent' && 'bg-urgent', className)}>
      <div className="mx-auto flex w-full flex-col gap-4 md:max-w-[720px] lg:max-w-[1040px]">{children}</div>
    </div>
  )
}

export function Header({ title, back, backTo, trailing, sub }: { title: ReactNode; back?: boolean; backTo?: RouteId; trailing?: ReactNode; sub?: ReactNode }) {
  const goBack = useBack(backTo)
  return (
    <header className="flex items-start gap-2 pb-1 pt-1">
      {back && (
        <button type="button" onClick={goBack} aria-label="Back" className="press -ml-3 flex h-12 w-12 flex-none items-center justify-center rounded-full text-ink hover:bg-well">
          <ArrowLeft size={26} aria-hidden />
        </button>
      )}
      <div className="min-w-0 flex-1 pt-1.5">
        <h1 className="break-words font-serif text-h1 font-medium tracking-tight text-ink">{title}</h1>
        {sub && <p className="mt-1 text-sub text-ink2">{sub}</p>}
      </div>
      {trailing && <div className="flex-none pt-0.5">{trailing}</div>}
    </header>
  )
}

/** Bottom action area that stays on screen above the keyboard-free bottom edge. */
export function Footer({ children }: { children: ReactNode }) {
  return <div className="sticky bottom-0 -mx-5 mt-2 flex flex-col gap-2 md:flex-row md:[&>*]:flex-1 bg-gradient-to-t from-canvas from-70% to-transparent px-5 pb-[max(1.5rem,env(safe-area-inset-bottom))] pt-6">{children}</div>
}

/** Stacks on a phone and tablet, two columns on a laptop. Put the main content first. */
export function Split({ children, className }: { children: ReactNode; className?: string }) {
  // min-w-0: a grid item will not shrink below its content by default, so one wide chart could push the whole page past a phone's edge
  return <div className={cn('grid gap-4 lg:grid-cols-2 lg:items-start lg:gap-6 [&>*]:min-w-0', className)}>{children}</div>
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
