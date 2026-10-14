import { useState } from 'react'
import { Navigate, useLocation, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useScan, useConfirmScan } from '@/data/hooks'
import type { NewMedication } from '@/data/repositories/types'
import { useUi } from '@/state/store'
import { href } from '@/app/routeIds'
import { useMedicineScope } from '@/features/meds/useMedicineScope'
import { Footer, Header, Screen } from '@/ui/layout'
import { Segmented } from '@/ui/controls'
import { Alert, Button, Card, Chip, SectionTitle, Skeleton } from '@/ui/primitives'
import { CheckCircle, Info, Pill } from '@/ui/icons'

type Kind = NewMedication['kind']
type Meal = 'before_meal' | 'after_meal' | 'na'
const KIND_FOR_ITEM: Record<string, Kind> = { prescription_label: 'prescription', otc: 'otc', supplement: 'supplement', tcm: 'tcm' }

const inputClass =
  'min-h-12 w-full rounded-field border-[1.5px] border-line bg-card px-3.5 py-2 text-body font-bold text-ink focus:border-brand focus:outline-none'

/**
 * H4 — Your dose plan. A label says "twice a day", not "8 am and 8 pm", so the times here are SUGGESTIONS the person changes to
 * suit their day. Every new medicine is saved as a daily one (the "only when needed" choice was removed). Choosing the kind of product
 * matters (adherence counts prescription medicines only), so it is shown and can be changed. "Add to my medicines" is the only place a
 * scanned medicine is saved: POST /scans/{id}/confirm, one transaction.
 */
export function ScanPlan() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const location = useLocation()
  const state = location.state as { scanId?: string; edits?: Record<string, string> } | null
  const scanId = state?.scanId
  const edits = state?.edits ?? {}
  const { data, isLoading, isError, refetch } = useScan(scanId)
  const confirm = useConfirmScan()
  const showToast = useUi((s) => s.showToast)
  const [times, setTimes] = useState<string[] | null>(null)
  const [kind, setKind] = useState<Kind | null>(null)
  const [meal, setMeal] = useState<Meal | null>(null)

  const kinds: { value: Kind; label: string }[] = [
    { value: 'prescription', label: t('scanPlan.kind.prescription', 'Prescription') },
    { value: 'otc', label: t('scanPlan.kind.otc', 'Over the counter') },
    { value: 'supplement', label: t('scanPlan.kind.supplement', 'Supplement') },
    { value: 'tcm', label: t('scanPlan.kind.tcm', 'Herbal') },
  ]
  const meals: { value: Meal; label: string }[] = [
    { value: 'before_meal', label: t('scanPlan.meal.before', 'Before') },
    { value: 'after_meal', label: t('scanPlan.meal.after', 'After') },
    { value: 'na', label: t('scanPlan.meal.either', 'Either') },
  ]

  // Computed before any early return, so the hook order never changes.
  const medName = edits['name'] ?? data?.drug ?? ''
  const chosenKind = kind ?? KIND_FOR_ITEM[data?.itemType ?? ''] ?? 'prescription'
  const outOfScope = useMedicineScope(medName, chosenKind)

  if (!scanId) return <Navigate to={href('H2')} replace />
  if (isError) {
    return (
      <Screen narrow>
        <Header title={t('scanPlan.title', 'Your dose plan')} back backTo="H3" />
        <Alert tone="warn" title={t('scanPlan.offline', 'We could not reach Equinox')}>
          {t('scanPlan.offlineBody', 'Check your connection and try again. Nothing has been saved.')}
        </Alert>
        <Footer>
          <Button onClick={() => void refetch()}>{t('scanPlan.retry', 'Try again')}</Button>
          <Button variant="secondary" onClick={() => navigate(href('H2'))}>
            {t('scanPlan.retake', 'Retake')}
          </Button>
        </Footer>
      </Screen>
    )
  }
  if (isLoading || !data) {
    return (
      <Screen narrow>
        <Header title={t('scanPlan.title', 'Your dose plan')} back backTo="H3" />
        <Skeleton className="h-48" />
      </Screen>
    )
  }
  // A scan that needs typing never gets this far (H3 sends it to the form), but a bookmarked address might.
  if (data.reviewMode === 'manual') {
    return <Navigate to={href('H8')} replace state={{ scanId: data.scanId, notice: data.notice }} />
  }

  const suggested = data.schedule.map((s) => s.time)
  const chosen = times ?? (suggested.length > 0 ? suggested : ['08:00'])
  const fromLabel = data.fields.find((f) => f.key === 'meal_relation')?.value
  const chosenMeal: Meal = meal ?? (fromLabel === 'before_meal' || fromLabel === 'after_meal' ? fromLabel : 'na')
  const distinct = new Set(chosen).size === chosen.length
  const valid = chosen.length > 0 && chosen.every(Boolean) && distinct
  const problem = chosen.length === 0
    ? t('scanPlan.noTimes', 'No dose times were found on the label. Add at least one time.')
    : !chosen.every(Boolean)
      ? t('scanPlan.pickTime', 'Choose a time for each dose.')
      : !distinct
        ? t('scanPlan.duplicateTime', 'Each time of day can only be listed once.')
        : null

  const save = () => {
    if (!valid) return
    const fields: Record<string, string | null> = { ...edits, meal_relation: chosenMeal }
    confirm.mutate(
      { scanId: data.scanId, fields, times: [...chosen].sort(), kind: chosenKind, asNeeded: false },
      {
        onSuccess: () => {
          showToast(t('scanPlan.added', 'Added to your medicines'))
          navigate(href('H1'), { replace: true })
        },
      },
    )
  }

  return (
    <Screen narrow>
      <Header title={t('scanPlan.title', 'Your dose plan')} back backTo="H3" sub={t('scanPlan.sub', 'Step 3 of 3. Nothing is saved until you add it.')} />

      <Card className="flex flex-col gap-3">
        <div className="flex items-start gap-3">
          <span className="flex h-11 w-11 flex-none items-center justify-center rounded-full bg-brand-soft text-brand">
            <Pill size={22} aria-hidden />
          </span>
          <div className="min-w-0 flex-1">
            <p className="break-words text-h2 font-bold leading-tight">{medName}</p>
          </div>
        </div>
        <div className="flex flex-col gap-1.5">
          <p id="plan-kind" className="text-sub font-bold text-ink">
            {t('scanPlan.whatKind', 'What kind is it?')}
          </p>
          <div role="group" aria-labelledby="plan-kind" className="flex flex-wrap gap-2">
            {kinds.map((k) => (
              <Chip key={k.value} on={chosenKind === k.value} onClick={() => setKind(k.value)}>
                {k.label}
              </Chip>
            ))}
          </div>
        </div>
      </Card>

      {outOfScope && (
        <Alert tone="info" title={t('scanPlan.scope.title', 'Is this one for Equinox?')}>
          {t('scanPlan.scope.body', 'Equinox is for diabetes medicines and the medicines or supplements you take every day. We do not recognise this name, so please check it is right. You can still add it.')}
        </Alert>
      )}

      {data.asNeeded && (
        <Alert tone="info">
          {t('scanPlan.asNeeded', 'Your label says to take this when it is needed. Equinox saves it as a daily medicine, so choose the times it should appear.')}
        </Alert>
      )}

      <Card className="flex flex-col gap-3">
        <SectionTitle>{t('scanPlan.doseTimes', 'Dose times')}</SectionTitle>
        <div className="flex flex-col gap-1.5">
          <p className="text-sub font-bold text-ink">{t('scanPlan.beforeAfter', 'Before or after food?')}</p>
          <Segmented label={t('scanPlan.beforeAfter', 'Before or after food?')} options={meals} value={chosenMeal} onChange={setMeal} />
        </div>
        <ul className="flex flex-col gap-3">
          {chosen.map((tm, i) => (
            <li key={i} className="flex items-center justify-between gap-3">
              <label htmlFor={`dose-${i}`} className="text-body text-ink2">
                {data.schedule[i]?.label ?? t('scanPlan.dose', 'Dose {{n}}', { n: i + 1 })}
              </label>
              <input
                id={`dose-${i}`}
                type="time"
                value={tm}
                onChange={(e) => setTimes(chosen.map((x, j) => (j === i ? e.target.value : x)))}
                className={`${inputClass} !w-40 text-right`}
              />
              {chosen.length > 1 && (
                <button
                  type="button"
                  aria-label={t('scanPlan.remove', 'Remove dose {{n}}', { n: i + 1 })}
                  onClick={() => setTimes(chosen.filter((_, j) => j !== i))}
                  className="press -mr-1 flex h-10 w-10 flex-none items-center justify-center rounded-full text-ink2 hover:bg-well"
                >
                  ×
                </button>
              )}
            </li>
          ))}
        </ul>
        {chosen.length < 6 && (
          <button type="button" onClick={() => setTimes([...chosen, '20:00'])} className="press self-start text-sub font-bold text-brand underline underline-offset-4">
            {t('scanPlan.addTime', 'Add another time')}
          </button>
        )}
        <p className="text-sub text-ink3">{t('scanPlan.suggested', 'These are suggested times, worked out from your label. Change them to suit your day.')}</p>
      </Card>

      {problem && <Alert tone="warn">{problem}</Alert>}
      {confirm.isError && (
        <Alert tone="danger" title={t('scanPlan.couldNotAdd', 'Could not add it')}>
          {confirm.error instanceof TypeError
            ? t('scanPlan.offlineBody', 'Check your connection and try again. Nothing has been saved.')
            : confirm.error instanceof Error && confirm.error.message && !/^\d{3}/.test(confirm.error.message)
              ? confirm.error.message
              : t('scanPlan.tryAgain', 'Please try again.')}
        </Alert>
      )}

      <Card tone="soft" className="flex items-start gap-3">
        <Info size={20} className="mt-0.5 flex-none text-ink3" aria-hidden />
        <p className="text-sub text-ink2">{t('scanPlan.asPrinted', 'We save it as printed on your label. Checking it against your other medicines is not part of this step yet.')}</p>
      </Card>

      <Footer>
        <Button icon={CheckCircle} disabled={!valid || confirm.isPending} onClick={save}>
          {confirm.isPending ? t('scanPlan.adding', 'Adding…') : t('scanPlan.add', 'Add to my medicines')}
        </Button>
      </Footer>
    </Screen>
  )
}
