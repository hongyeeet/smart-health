/**
 * Shared hook and helpers for the log screens (E2, E4, E5, F1 → E6).
 *
 * `useFinishLog` saves an entry via `useLog`, remembers the result for the
 * Saved screen (E6), and routes — red-flag symptoms go straight to J1.
 */
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useLog } from '@/data/hooks'
import type { LogInput } from '@/data/repositories/types'
import { href } from '@/app/routeIds'
import { useUi } from '@/state/store'

export function useFinishLog() {
  const { t } = useTranslation()
  const log = useLog()
  const navigate = useNavigate()
  const setLast = useUi((s) => s.setLastLog)
  return {
    pending: log.isPending,
    /** a plain-language message when the last save failed, otherwise null */
    error: log.isError ? t('log.finish.error', 'It could not be saved just now. Check your connection and try again.') : null,
    save: (input: LogInput, onSaved?: () => void) =>
      log.mutate(input, {
        onSuccess: (res) => {
          onSaved?.()
          setLast(res)
          navigate(res.urgent ? `${href('J1')}?tier=${res.urgentTier ?? 2}` : href('E6'), { replace: true })
        },
      }),
  }
}
