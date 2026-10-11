import { useEffect, useRef, useState } from 'react'
import { Outlet, useLocation, useNavigate } from 'react-router-dom'
import { AnimatePresence, motion } from 'motion/react'
import { appConfig } from '@/config/app'
import { useUi } from '@/state/store'
import { cn } from '@/lib/cn'
import { ChartLineUp, ChatCircleDots, House, Pill, Plus, UserCircle, type IconType } from '@/ui/icons'
import { duration, ease } from '@/motion/tokens'
import { SheetHost } from './SheetHost'
import { href, type RouteId } from './routeIds'
import { useGo } from './navigation'
import { built } from './screens'

function useMedia(q: string) {
  const [m, setM] = useState(() => (typeof window === 'undefined' ? false : window.matchMedia(q).matches))
  useEffect(() => {
    const mq = window.matchMedia(q)
    const on = () => setM(mq.matches)
    mq.addEventListener('change', on)
    on()
    return () => mq.removeEventListener('change', on)
  }, [q])
  return m
}

/** Fits the 390 x 844 device into short laptop screens without cropping it. */
function useFit(enabled: boolean) {
  const [s, setS] = useState(1)
  useEffect(() => {
    if (!enabled) return
    const f = () => setS(Math.min(1, (window.innerHeight - 40) / 844))
    f()
    window.addEventListener('resize', f)
    return () => window.removeEventListener('resize', f)
  }, [enabled])
  return s
}

type TabKey = 'home' | 'insights' | 'log' | 'meds' | 'me'
const TAB_ROUTE: Record<TabKey, RouteId> = { home: 'B1', insights: 'C1', log: 'E1', meds: 'H1', me: 'K1' }

function activeTab(p: string): TabKey | null {
  if (p === '/') return 'home'
  if (p.startsWith('/insights') || p.startsWith('/day')) return 'insights'
  if (p.startsWith('/log')) return 'log'
  if (p.startsWith('/meds')) return 'meds'
  if (p.startsWith('/me') || p.startsWith('/brief')) return 'me'
  return null
}
/** The tab bar belongs to the five roots and to Insights pages. Pushed screens use the whole height. */
function showTabs(p: string) {
  return p === '/' || p.startsWith('/insights') || p.startsWith('/day') || p === '/log' || p === '/meds' || p === '/me'
}
/** Setup and the urgent screen have no side rail: nothing to wander off to while a person answers questions or needs help now. */
const showRail = (p: string) => !p.startsWith('/welcome') && !p.startsWith('/urgent')
const isTabRoot = (p: string) => p === '/' || p.startsWith('/insights') || p === '/log' || p === '/meds' || p === '/me'

export function Shell() {
  const wide = useMedia('(min-width: 1000px) and (min-height: 700px)')
  const device = appConfig.frame === 'device' && wide
  const fit = useFit(device)

  if (device)
    return (
      <div className="flex h-full items-center justify-center bg-well/60 p-6">
        <div style={{ width: 390 * fit + 24, height: 844 * fit + 24 }} className="flex-none">
          <div style={{ transform: `scale(${fit})`, transformOrigin: 'top left' }} className="rounded-[54px] bg-[#0B100E] p-3 shadow-[0_30px_80px_-30px_rgba(0,0,0,0.55)]">
            <div className="relative h-[844px] w-[390px] overflow-hidden rounded-[42px]">
              <AppFrame />
            </div>
          </div>
        </div>
      </div>
    )

  return (
    <div className="fixed inset-0 flex h-dvh justify-center bg-well/60">
      <div className="relative h-full w-full max-w-[480px] bg-canvas md:max-w-none">
        <AppFrame fullBleed />
      </div>
    </div>
  )
}

function AppFrame({ fullBleed }: { fullBleed?: boolean }) {
  const { pathname } = useLocation()
  const textScale = useUi((s) => s.textScale)
  const tab = activeTab(pathname)
  /** the Ask button belongs to Home and Insights; the layout reads `has-ask` to leave room for it (index.css) */
  const rail = showRail(pathname)
  const askOn = !!built.I1 && (pathname === '/' || pathname === '/insights')
  const prevRoot = useRef(isTabRoot(pathname))
  const animate = !(prevRoot.current && isTabRoot(pathname))
  useEffect(() => {
    prevRoot.current = isTabRoot(pathname)
  }, [pathname])

  return (
    <div data-ts={textScale} style={{ ['--ts' as string]: textScale }} className={cn('relative h-full w-full overflow-hidden bg-canvas text-ink', askOn && 'has-ask', fullBleed && 'pt-[env(safe-area-inset-top)] pl-[env(safe-area-inset-left)] pr-[env(safe-area-inset-right)]')}>
      <div className="absolute inset-x-0 top-0 z-30 h-3" aria-hidden />
      <main className={cn('absolute inset-x-0 bottom-0', pathname.startsWith('/urgent') ? 'top-0' : 'top-3 md:top-4', rail && 'md:left-24 lg:left-60')}>
        <motion.div key={pathname} className="absolute inset-0" initial={animate ? { opacity: 0, y: 8 } : false} animate={{ opacity: 1, y: 0 }} transition={{ duration: duration.page, ease: ease.out }}>
          <Outlet />
        </motion.div>
      </main>
      {showTabs(pathname) && <TabBar active={tab} />}
      {rail && <SideRail active={tab} ask={askOn} />}
      {askOn && <AskButton />}
      <SheetHost />
      <Toast rail={rail} />
    </div>
  )
}

/**
 * Phone only: a compact pill above the tab bar. The page keeps a matching space at its end (`--ask-space`), so it never hides the last card,
 * and while the person scrolls down to read it steps out of the way; it returns when they scroll up, or reach the top or the end.
 * Tablet and laptop have it in the side rail.
 */
function useAskVisible() {
  const [visible, setVisible] = useState(true)
  useEffect(() => {
    let last = 0
    const onScroll = (e: Event) => {
      const el = e.target as HTMLElement
      if (!(el instanceof HTMLElement) || !el.classList.contains('scroll-area')) return
      const top = el.scrollTop
      const atEnd = top + el.clientHeight >= el.scrollHeight - 80
      if (top < 80 || atEnd || top < last - 6) setVisible(true)
      else if (top > last + 6) setVisible(false)
      last = top
    }
    document.addEventListener('scroll', onScroll, true)
    return () => document.removeEventListener('scroll', onScroll, true)
  }, [])
  return visible
}

function AskButton({ inRail }: { inRail?: boolean }) {
  const go = useGo()
  const visible = useAskVisible()
  const away = !inRail && !visible
  return (
    <button
      type="button"
      onClick={() => go('I1')}
      aria-label="Ask Smart Health"
      tabIndex={away ? -1 : undefined}
      className={cn(
        'press flex min-h-12 items-center gap-2 bg-ink px-4 text-ctl font-bold text-canvas',
        inRail ? 'w-full justify-center rounded-card' : 'absolute bottom-[calc(var(--tab-space)+0.75rem)] right-5 z-20 rounded-chip shadow-lift transition-[opacity,translate] duration-200 md:hidden',
        away && 'pointer-events-none translate-y-3 opacity-0',
      )}
    >
      <ChatCircleDots size={22} weight="regular" aria-hidden />
      Ask
    </button>
  )
}

const TABS: { key: TabKey; label: string; icon: IconType }[] = [
  { key: 'home', label: 'Home', icon: House },
  { key: 'insights', label: 'Insights', icon: ChartLineUp },
  { key: 'log', label: 'Log', icon: Plus },
  { key: 'meds', label: 'Medications', icon: Pill },
  { key: 'me', label: 'Me', icon: UserCircle },
]

/** No animation on tab switches: they happen all day. Only the press acknowledges the tap. */
function TabBar({ active }: { active: TabKey | null }) {
  const navigate = useNavigate()
  return (
    <nav aria-label="Main" className="absolute inset-x-0 bottom-0 z-20 border-t border-line bg-card/95 pb-[max(1.25rem,env(safe-area-inset-bottom))] pt-2 backdrop-blur-md md:hidden">
      <ul className="grid grid-cols-[repeat(5,minmax(0,1fr))] items-end px-2">
        {TABS.map(({ key, label, icon: Icon }) => {
          const on = active === key
          const centre = key === 'log'
          return (
            <li key={key} className="flex min-w-0 justify-center">
              <button type="button" aria-label={label} aria-current={on ? 'page' : undefined} onClick={() => navigate(href(TAB_ROUTE[key]))} className="press flex min-h-14 w-full min-w-14 flex-col items-center justify-end gap-0.5 px-0.5">
                {centre ? (
                  <span className="-mt-6 flex h-14 w-14 items-center justify-center rounded-full bg-brand text-on-brand shadow-lift ring-4 ring-card">
                    <Icon size={28} weight="bold" aria-hidden />
                  </span>
                ) : (
                  <Icon size={26} weight={on ? 'fill' : 'regular'} className={on ? 'text-brand' : 'text-ink2'} aria-hidden />
                )}
                <span className={cn('text-tab font-bold', on ? 'text-brand' : 'text-ink2')}>{label === 'Medications' ? 'Meds' : label}</span>
              </button>
            </li>
          )
        })}
      </ul>
    </nav>
  )
}

/** Tablet and laptop navigation: the bottom bar is too far from the hand on a wide screen, so it becomes a rail on the left. */
function SideRail({ active, ask }: { active: TabKey | null; ask: boolean }) {
  const navigate = useNavigate()
  return (
    <nav aria-label="Main" className="absolute inset-y-0 left-0 z-20 hidden w-24 flex-col gap-1 border-r border-line bg-card px-2 py-5 md:flex lg:w-60 lg:px-4">
      <p className="mb-4 hidden px-3 font-serif text-h2 font-medium text-ink lg:block">{appConfig.name}</p>
      {TABS.map(({ key, label, icon: Icon }) => {
        const on = active === key
        return (
          <button key={key} type="button" aria-label={label} aria-current={on ? 'page' : undefined} onClick={() => navigate(href(TAB_ROUTE[key]))} className={cn('press flex min-h-14 flex-col items-center justify-center gap-0.5 rounded-card px-2 lg:flex-row lg:justify-start lg:gap-3 lg:px-4', on ? 'bg-brand/10 text-brand' : 'text-ink2 hover:bg-well')}>
            <Icon size={26} weight={on || key === 'log' ? 'fill' : 'regular'} aria-hidden />
            <span className="text-tab font-bold lg:text-btn">{label === 'Medications' ? 'Meds' : label}</span>
          </button>
        )
      })}
      {ask && (
        <div className="mt-auto pt-4">
          <AskButton inRail />
        </div>
      )}
    </nav>
  )
}

function Toast({ rail }: { rail: boolean }) {
  const toast = useUi((s) => s.toast)
  const [shown, setShown] = useState<string | null>(null)
  useEffect(() => {
    if (!toast) return
    setShown(toast.text)
    const t = setTimeout(() => setShown(null), 2300)
    return () => clearTimeout(t)
  }, [toast])
  return (
    <div className={cn('pointer-events-none absolute inset-x-0 bottom-[calc(7rem+env(safe-area-inset-bottom))] z-50 flex justify-center px-6 md:bottom-10', rail && 'md:left-24 lg:left-60')} aria-live="polite">
      <AnimatePresence>
        {shown && (
          <motion.div key={toast?.id} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, transition: { duration: 0.15 } }} transition={{ duration: 0.22, ease: ease.out }} className="rounded-chip bg-ink px-4 py-2.5 text-sub font-bold text-canvas shadow-lift">
            {shown}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

