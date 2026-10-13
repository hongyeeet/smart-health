/**
 * What every onboarding page does when Continue is pressed: save this page's answers to the record, then move on.
 *
 * - A save that works moves on. A save that fails shows the reason in plain words and keeps the person on the page; the next press
 *   is "Continue anyway", which moves on with the answers kept on this device. Nothing is shown as saved that the server did not take.
 * - A reminder email that cannot be stored yet (there is no profile until the first save) holds the person on the page with a plain
 *   note: "We will save your email when your profile is created". The next press is "Continue anyway". The email stays in the answers
 *   and is saved with the next save that creates the profile (page 3, or Finish).
 * - The demo patient (Mr Tan) is never written: the page moves on and says so.
 * - Answers the server holds for later (the history before migration 0032) are not an error: they are kept on this device for now.
 */
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useUi } from '@/state/store'
import { READ_ONLY_USER, useSaveStep, type ProfileBody } from './api'

export interface EmailSave {
  email: string | null
  optIn: boolean
}

export function usePageSave(cannotRead = false) {
  const { t } = useTranslation()
  const save = useSaveStep()
  const readOnly = useUi((s) => s.userKey) === READ_ONLY_USER
  /** the last save failed: the person can fix the point, or continue anyway */
  const [error, setError] = useState<string | null>(null)
  /** the reminder email could not be stored yet (no profile): the person is told and can continue anyway */
  const [emailWaiting, setEmailWaiting] = useState(false)
  /** a note on a save that worked in part (a field kept on this device for now) */
  const [notice, setNotice] = useState<string | null>(null)

  /** Saves what it is given. Returns true when the page may move on. */
  const commit = async (profile: ProfileBody | null, email: EmailSave | null): Promise<boolean> => {
    setNotice(null)
    if (readOnly || (!profile && !email)) {
      setError(null)
      setEmailWaiting(false)
      return true
    }
    /* With the saved answers unread, a save could blank them: nothing is written until they are read again */
    if (cannotRead) {
      setError(t('onboarding.noRead', 'Your saved answers could not be read, so nothing is saved right now. Your answers stay on this device.'))
      return false
    }
    try {
      const res = await save.mutateAsync({ profile, email })
      setError(null)
      const parts: string[] = []
      /* only an answer the person actually gave counts: an empty field sent as null is not "kept" */
      const given = (key: string) => {
        const v = (profile as Record<string, unknown> | null)?.[key]
        return v !== null && v !== undefined && !(Array.isArray(v) && v.length === 0)
      }
      if (res.saved && res.saved.notSaved.some(given)) {
        parts.push(t('onboarding.keptHere', 'Some answers are kept on this device for now. They are added to your record once it is ready for them.'))
      }
      if (res.email === 'waiting') {
        setEmailWaiting(true)
        setNotice(t('onboarding.email.waiting', 'We will save your email when your profile is created. It is kept on this device until then.'))
        return false
      }
      setEmailWaiting(false)
      if (res.email === 'failed') parts.push(t('onboarding.email.notSavedV2', 'We could not save your reminder email just now. It is kept on this device. You can add it later in Me, Data and account.'))
      setNotice(parts.length ? parts.join(' ') : null)
      return true
    } catch (e) {
      const detail = e instanceof Error ? e.message : ''
      setError(detail ? `${t('onboarding.saveFailed', 'We could not save this page just now. Your answers are kept on this device.')} ${detail}` : t('onboarding.saveFailed', 'We could not save this page just now. Your answers are kept on this device.'))
      return false
    }
  }

  const reset = () => {
    setError(null)
    setEmailWaiting(false)
    setNotice(null)
  }

  /** the page is held: a failed save or a waiting email. The next press continues anyway. */
  const holding = error !== null || emailWaiting

  return { commit, saving: save.isPending, error, emailWaiting, holding, notice, readOnly, reset }
}
