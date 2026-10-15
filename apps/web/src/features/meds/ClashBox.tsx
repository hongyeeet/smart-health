import { useTranslation } from 'react-i18next'
import { useClash, useRunClashCheck } from '@/data/hooks'
import { Alert, Button } from '@/ui/primitives'
import { InteractionCard } from '@/features/alerts/InteractionCard'

/**
 * The medicine clash notices on the Meds page (prd F5): one clean card per open alert (the same card as on the alerts page), each with a
 * link to the review page. They appear only when two of the person's medicines may clash, found by the drug-pair rules or by the AI check
 * that runs after every medicine is added. With nothing found there is no card, which is not the same as "safe": supplements and herbal
 * products still say "Not checked". The wording never tells the person to stop a medicine.
 */
export function ClashBox() {
  const { t } = useTranslation()
  const { data } = useClash()
  const rerun = useRunClashCheck()
  if (!data) return null

  return (
    <>
      {data.checking && <p className="px-1 text-sub text-ink3">{t('alerts.checking', 'Checking your medicines for clashes…')}</p>}
      {/* No card can mean "nothing found" or "could not check": when the check did not finish, say so instead of looking like all clear. */}
      {!data.checking && data.checkIncomplete && data.alerts.length === 0 && (
        <Alert tone="info" title={t('meds.clash.incompleteTitle', 'We could not finish checking for clashes')}>
          <p>{t('meds.clash.incompleteBody', 'This is not the same as all clear. Please try again, or ask your pharmacist to look at your list.')}</p>
          <div className="mt-2">
            <Button size="md" variant="secondary" className="!w-auto" disabled={rerun.isPending} onClick={() => rerun.mutate()}>
              {t('meds.clash.checkAgain', 'Check again')}
            </Button>
          </div>
        </Alert>
      )}
      {data.alerts.map((a) => (
        <InteractionCard key={a.id} alert={a} />
      ))}
      {data.alerts.length > 0 && data.checkIncomplete && <p className="px-1 text-sub text-ink2">{t('meds.clash.partial', 'The full check could not finish just now, so there may be more to see later.')}</p>}
    </>
  )
}
