import { useEffect, useRef, type ReactNode } from 'react'
import { createPortal } from 'react-dom'
import { motion, useDragControls } from 'motion/react'
import { duration, ease } from '@/motion/tokens'
import { X } from './icons'

/**
 * Bottom sheet. Slides up on the drawer curve, leaves faster than it arrives, closes on a quick flick
 * (velocity) and not only on distance, and keeps focus inside while open.
 * It is drawn into the app frame (the element with data-ts), not where it is written, so it always covers the screen even when the page
 * behind it is scrolled (inside a scrolled page it used to appear at the top of the page's content).
 */
export function Sheet({ title, onClose, children, label }: { title: ReactNode; onClose: () => void; children: ReactNode; label?: string }) {
  const controls = useDragControls()
  const panel = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const prev = document.activeElement as HTMLElement | null
    panel.current?.focus({ preventScroll: true })      // the panel starts below the frame; a plain focus() would scroll the frame up to it
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => {
      window.removeEventListener('keydown', onKey)
      prev?.focus?.()
    }
  }, [onClose])

  const host = typeof document !== 'undefined' ? document.querySelector('[data-ts]') : null
  const sheet = (
    <div className="absolute inset-0 z-40 flex flex-col justify-end">
      <motion.button
        type="button"
        aria-label="Close"
        tabIndex={-1}
        className="absolute inset-0 bg-overlay"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0, transition: { duration: duration.sheetExit } }}
        transition={{ duration: duration.page }}
        onClick={onClose}
      />
      <motion.div
        ref={panel}
        role="dialog"
        aria-modal="true"
        aria-label={label ?? (typeof title === 'string' ? title : 'Details')}
        tabIndex={-1}
        className="relative mx-auto flex max-h-[90%] w-full flex-col rounded-t-sheet border border-b-0 border-line bg-card shadow-sheet outline-none md:mb-8 md:max-w-[560px] md:rounded-b-sheet md:border-b"
        initial={{ y: '100%' }}
        animate={{ y: 0 }}
        exit={{ y: '100%', transition: { duration: duration.sheetExit, ease: ease.drawer } }}
        transition={{ duration: duration.sheet, ease: ease.drawer }}
        drag="y"
        dragListener={false}
        dragControls={controls}
        dragConstraints={{ top: 0, bottom: 0 }}
        dragElastic={{ top: 0, bottom: 0.5 }}
        onDragEnd={(_, info) => {
          if (info.offset.y > 120 || info.velocity.y > 500) onClose()
        }}
      >
        <div className="flex-none cursor-grab touch-none px-5 pb-1 pt-3" onPointerDown={(e) => controls.start(e)}>
          <div className="mx-auto h-1.5 w-11 rounded-full bg-line" />
          <div className="mt-3 flex items-start justify-between gap-3">
            <h2 className="font-serif text-h1 font-medium tracking-tight text-ink">{title}</h2>
            <button type="button" aria-label="Close" onClick={onClose} className="press -mr-2 flex h-12 w-12 flex-none items-center justify-center rounded-full text-ink2 hover:bg-well">
              <X size={24} aria-hidden />
            </button>
          </div>
        </div>
        <div className="hide-scroll scroll-area flex-1 overflow-y-auto px-5 pb-[max(2rem,env(safe-area-inset-bottom))] pt-2">{children}</div>
      </motion.div>
    </div>
  )
  return host ? createPortal(sheet, host) : sheet
}
