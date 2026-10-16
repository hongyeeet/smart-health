import { useEffect, useRef } from 'react'
import { createPortal } from 'react-dom'
import { motion } from 'motion/react'
import { useTranslation } from 'react-i18next'
import { useUi } from '@/state/store'
import { useStartNewPerson } from '@/features/onboarding/newPerson'
import { Button } from '@/ui/primitives'
import { Logo } from '@/ui/Logo'
import { X } from '@/ui/icons'
import { duration } from '@/motion/tokens'
import { useGo } from './navigation'

/**
 * A short welcome for anyone who opens the app (a reviewer, a first visitor): who Mr Tan is, where to try the memory agent, how to make your own
 * user, and where the doctor link is. It can be closed (the X, Escape, the dark area or a button) and comes back the next time the app is opened,
 * because it is kept in memory only. It is not shown while set-up or the urgent screen is open.
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

  const steps = [
    {
      title: t('welcome.tan.title', 'Mr Tan is a demo user'),
      body: t('welcome.tan.body', 'You are looking at his example record, about 90 days of data. It is read-only, so look around freely: Home, Insights, Log, Meds and Me.'),
    },
    {
      title: t('welcome.memory.title', 'Try the memory agent'),
      body: t('welcome.memory.body', 'Open Me, then "What Equinox has learned". It shows the patterns the app noticed, with the evidence. Create your own user to confirm or delete one.'),
    },
    {
      title: t('welcome.own.title', 'Create your own user'),
      body: t('welcome.own.body', 'Use the round avatar at the top of Home, then "Create a new user". You can try the set-up, logging meals, scanning a medicine, meal suggestions and the assistant.'),
    },
    {
      title: t('welcome.brief.title', 'Make a doctor link'),
      body: t('welcome.brief.body', 'Open Me, then "Doctor brief", and create a private link. Opening it shows a dedicated report, the way a doctor would see it.'),
    },
  ]

  const host = typeof document !== 'undefined' ? document.querySelector('[data-ts]') : null
  const view = (
    <div className="absolute inset-0 z-50 flex items-center justify-center p-4">
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
        className="relative flex max-h-full w-full max-w-[460px] flex-col overflow-hidden rounded-[26px] border border-line bg-card shadow-sheet outline-none"
        initial={{ opacity: 0, y: 12, scale: 0.98 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ duration: duration.page }}
      >
        <div className="flex items-start gap-3 px-5 pb-3 pt-5">
          <Logo size={34} className="mt-0.5" />
          <div className="min-w-0 flex-1">
            <h2 id="reviewer-welcome-title" className="font-serif text-h2 font-medium leading-tight text-ink">
              {t('welcome.title', 'Welcome to Equinox')}
            </h2>
            <p className="text-sub leading-snug text-ink2">{t('welcome.sub', 'A quick guide for reviewers. It takes a minute.')}</p>
          </div>
          <button type="button" aria-label={t('common.close', 'Close')} onClick={onClose} className="press -mr-2 -mt-1 flex h-12 w-12 flex-none items-center justify-center rounded-full text-ink2 hover:bg-well">
            <X size={22} aria-hidden />
          </button>
        </div>

        <ol className="scroll-area flex-1 space-y-3 overflow-y-auto px-5 pb-3">
          {steps.map((s, i) => (
            <li key={s.title} className="flex gap-3 rounded-card border border-line bg-canvas p-3">
              <span className="flex h-7 w-7 flex-none items-center justify-center rounded-full bg-brand text-sub font-bold text-on-brand" aria-hidden>
                {i + 1}
              </span>
              <div className="min-w-0">
                <p className="text-body font-bold leading-snug text-ink">{s.title}</p>
                <p className="text-sub leading-snug text-ink2">{s.body}</p>
              </div>
            </li>
          ))}
        </ol>

        <div className="space-y-2 border-t border-line px-5 pb-5 pt-4">
          <Button onClick={onClose}>{t('welcome.explore', "Explore Mr Tan's record")}</Button>
          <div className="grid grid-cols-2 gap-2">
            <Button
              variant="secondary"
              size="md"
              onClick={() => {
                onClose()
                startNew(t('switch.newUserN', 'New User {{n}}', { n: people.length + 1 }))
              }}
            >
              {t('welcome.create', 'Create my user')}
            </Button>
            <Button
              variant="secondary"
              size="md"
              onClick={() => {
                onClose()
                go('K2')
              }}
            >
              {t('welcome.memory.go', 'Memory agent')}
            </Button>
          </div>
        </div>
      </motion.div>
    </div>
  )
  return host ? createPortal(view, host) : view
}
