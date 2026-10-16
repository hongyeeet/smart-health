import { useEffect, useRef, type ReactNode } from 'react'
import { createPortal } from 'react-dom'
import { motion } from 'motion/react'
import { useTranslation } from 'react-i18next'
import { useUi } from '@/state/store'
import { useStartNewPerson } from '@/features/onboarding/newPerson'
import { Logo } from '@/ui/Logo'
import { X } from '@/ui/icons'
import { duration } from '@/motion/tokens'
import { useGo } from './navigation'

/** A word or phrase inside a sentence that acts as a link (it is a button, so it works with a keyboard and a screen reader). */
function InlineLink({ onClick, children }: { onClick: () => void; children: ReactNode }) {
  return (
    <button type="button" onClick={onClick} className="press inline font-bold text-brand underline decoration-1 underline-offset-4">
      {children}
    </button>
  )
}

/**
 * A short welcome for anyone who opens the app (a reviewer, a first visitor): three lines and no buttons. It can be closed with the X, Escape or a
 * tap outside it, and comes back the next time the app is opened, because it is kept in memory only. It is not shown while set-up or the urgent
 * screen is open. It sizes itself to the screen: a narrow card on a phone, a little wider on a tablet or laptop.
 */
export function ReviewerWelcome({ onClose }: { onClose: () => void }) {
  const { t } = useTranslation()
  const go = useGo()
  const startNew = useStartNewPerson()
  const people = useUi((s) => s.people)
  const panel = useRef<HTMLDivElement>(null)

  useEffect(() => {
    panel.current?.focus({ preventScroll: true })
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  const row = 'flex gap-3'
  const dot = 'mt-0.5 flex h-6 w-6 flex-none items-center justify-center rounded-full bg-brand text-[13px] font-bold leading-none text-on-brand'

  const host = typeof document !== 'undefined' ? document.querySelector('[data-ts]') : null
  const view = (
    <div className="absolute inset-0 z-50 flex items-center justify-center p-4 sm:p-6">
      <motion.button
        type="button"
        aria-label={t('common.close', 'Close')}
        tabIndex={-1}
        className="absolute inset-0 bg-overlay"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: duration.page }}
        onClick={onClose}
      />
      <motion.div
        ref={panel}
        role="dialog"
        aria-modal="true"
        aria-labelledby="reviewer-welcome-title"
        tabIndex={-1}
        className="relative w-full max-w-[min(100%,400px)] rounded-[22px] border border-line bg-card p-4 shadow-sheet outline-none sm:max-w-[440px] sm:p-5"
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: duration.page }}
      >
        <div className="flex items-center gap-2.5 pr-10">
          <Logo size={26} />
          <h2 id="reviewer-welcome-title" className="font-serif text-h2 font-medium leading-tight text-ink">
            {t('welcome.title', 'Welcome to Equinox')}
          </h2>
        </div>
        <button type="button" aria-label={t('common.close', 'Close')} onClick={onClose} className="press absolute right-1.5 top-1.5 flex h-12 w-12 items-center justify-center rounded-full text-ink2 hover:bg-well">
          <X size={22} aria-hidden />
        </button>

        <ol className="mt-3 space-y-3 text-sub leading-snug text-ink2 sm:text-body">
          <li className={row}>
            <span className={dot} aria-hidden>1</span>
            <p>
              <b className="text-ink">{t('welcome.tan.a', 'Mr Tan is a demo user.')}</b> {t('welcome.tan.b', 'Study his example record to see how the app works.')}
            </p>
          </li>
          <li className={row}>
            <span className={dot} aria-hidden>2</span>
            <p>
              {t('welcome.try', 'Try the')}{' '}
              <InlineLink
                onClick={() => {
                  onClose()
                  go('K2')
                }}
              >
                {t('welcome.memory', 'memory agent')}
              </InlineLink>{' '}
              {t('welcome.and', 'and the')}{' '}
              <InlineLink
                onClick={() => {
                  onClose()
                  go('I1')
                }}
              >
                {t('welcome.chat', 'chatbot')}
              </InlineLink>
              .
            </p>
          </li>
          <li className={row}>
            <span className={dot} aria-hidden>3</span>
            <p>
              <InlineLink
                onClick={() => {
                  onClose()
                  startNew(t('switch.newUserN', 'New User {{n}}', { n: people.length + 1 }))
                }}
              >
                {t('welcome.create', 'Create a new user')}
              </InlineLink>{' '}
              {t('welcome.createRest', 'from the avatar at the top of Home to try set-up and every other feature.')}
            </p>
          </li>
        </ol>
      </motion.div>
    </div>
  )
  return host ? createPortal(view, host) : view
}
