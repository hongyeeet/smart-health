import { useState } from 'react'
import { Navigate, useLocation, useNavigate } from 'react-router-dom'
import { useScan, useConfirmScan } from '@/data/hooks'
import type { NewMedication } from '@/data/repositories/types'
import { useUi } from '@/state/store'
import { href } from '@/app/routeIds'
import { Footer, Header, Screen } from '@/ui/layout'
import { Segmented } from '@/ui/controls'
import { Alert, Button, Card, Chip, SectionTitle, Skeleton } from '@/ui/primitives'
import { CheckCircle, Info, Pill } from '@/ui/icons'

type Kind = NewMedication['kind']
const KINDS: { value: Kind; label: string }[] = [
  { value: 'prescription', label: 'Prescription' },
  { value: 'otc', label: 'Over the counter' },
  { value: 'supplement', label: 'Supplement' },
  { value: 'tcm', label: 'Herbal' },
]
const MEALS: { value: 'before_meal' | 'after_meal' | 'na'; label: string }[] = [
  { value: 'before_meal', label: 'Before' },
  { value: 'after_meal', label: 'After' },
  { value: 'na', label: 'Either' },
]
const KIND_FOR_ITEM: Record<string, Kind> = { prescription_label: 'prescription', otc: 'otc', supplement: 'supplement', tcm: 'tcm' }

const inputClass =
  'min-h-12 w-full rounded-field border-[1.5px] border-line bg-card px-3.5 py-2 text-body font-bold text-ink focus:border-brand focus:outline-none'

/**
 * H4 — Your dose plan. A label says "twice a day", not "8 am and 8 pm", so the times here are SUGGESTIONS the person changes to
 * suit their day. Choosing the kind of product matters (adherence counts prescription medicines only), so it is shown and can be
 * changed. "Add to my medicines" is the only place a scanned medicine is saved: POST /scans/{id}/confirm, one transaction.
 */
export function ScanPlan() {
  const navigate = useNavigate()
  const location = useLocation()
  const state = location.state as { scanId?: string; edits?: Record<string, string> } | null
  const scanId = state?.scanId
  const edits = state?.edits ?? {}
  const { data, isLoading } = useScan(scanId)
  const confirm = useConfirmScan()
  const showToast = useUi((s) => s.showToast)
  const [times, setTimes] = useState<string[] | null>(null)
  const [kind, setKind] = useState<Kind | null>(null)
  const [meal, setMeal] = useState<'before_meal' | 'after_meal' | 'na' | null>(null)

  if (!scanId) return <Navigate to={href('H2')} replace />
  if (isLoading || !data) {
    return (
      <Screen>
        <Header title="Your dose plan" back backTo="H3" />
        <Skeleton className="h-48" />
      </Screen>
    )
  }
  // A scan that needs typing never gets this far (H3 sends it to the form), but a bookmarked address might.
  if (data.reviewMode === 'manual') {
    return <Navigate to={href('H8')} replace state={{ scanId: data.scanId, notice: data.notice }} />
  }

  const suggested = data.schedule.map((s) => s.time)
  const chosen = times ?? suggested
  const chosenKind = kind ?? KIND_FOR_ITEM[data.itemType] ?? 'prescription'
  const fromLabel = data.fields.find((f) => f.key === 'meal_relation')?.value
  const chosenMeal = meal ?? (fromLabel === 'before_meal' || fromLabel === 'after_meal' ? fromLabel : 'na')
  const medName = edits['name'] ?? data.drug
  const distinct = new Set(chosen).size === chosen.length
  const valid = data.asNeeded || (chosen.length > 0 && chosen.every(Boolean) && distinct)
  const problem = data.asNeeded ? null : chosen.length === 0
    ? 'No dose times were found on the label. Go back and type the medicine in.'
    : !chosen.every(Boolean)
      ? 'Choose a time for each dose.'
      : !distinct
        ? 'Each time of day can only be listed once.'
        : null

  const save = () => {
    if (!valid) return
    const fields: Record<string, string | null> = { ...edits, meal_relation: chosenMeal }
    confirm.mutate(
      { scanId: data.scanId, fields, times: data.asNeeded ? [] : [...chosen].sort(), kind: chosenKind },
      {
        onSuccess: () => {
          showToast('Added to your medicines')
          navigate(href('H1'), { replace: true })
        },
      },
    )
  }

  return (
    <Screen>
      <Header title="Your dose plan" back backTo="H3" sub="Step 3 of 3. Nothing is saved until you add it." />

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
            What kind is it?
          </p>
          <div role="group" aria-labelledby="plan-kind" className="flex flex-wrap gap-2">
            {KINDS.map((k) => (
              <Chip key={k.value} on={chosenKind === k.value} onClick={() => setKind(k.value)}>
                {k.label}
              </Chip>
            ))}
          </div>
        </div>
      </Card>

      {data.asNeeded && (
        <Card tone="soft" className="flex flex-col gap-1.5">
          <SectionTitle>Dose times</SectionTitle>
          <p className="text-body text-ink2">Your label says to take this when it is needed, so there are no set times and no reminders.</p>
        </Card>
      )}

      {suggested.length > 0 && !data.asNeeded && (
        <Card className="flex flex-col gap-3">
          <SectionTitle>Dose times</SectionTitle>
          <div className="flex flex-col gap-1.5">
            <p className="text-sub font-bold text-ink">Before or after food?</p>
            <Segmented label="Before or after food" options={MEALS} value={chosenMeal} onChange={setMeal} />
          </div>
          <ul className="flex flex-col gap-3">
            {chosen.map((t, i) => (
              <li key={i} className="flex items-center justify-between gap-3">
                <label htmlFor={`dose-${i}`} className="text-body text-ink2">
                  {data.schedule[i]?.label ?? `Dose ${i + 1}`}
                </label>
                <input
                  id={`dose-${i}`}
                  type="time"
                  value={t}
                  onChange={(e) => setTimes(chosen.map((x, j) => (j === i ? e.target.value : x)))}
                  className={`${inputClass} !w-40 text-right`}
                />
              </li>
            ))}
          </ul>
          <p className="text-sub text-ink3">These are suggested times. Your label says how many times a day, not when, so change them to suit your day.</p>
        </Card>
      )}

      {problem && <Alert tone="warn">{problem}</Alert>}
      {confirm.isError && (
        <Alert tone="danger" title="Could not add it">
          {confirm.error instanceof Error ? confirm.error.message : 'Please try again.'}
        </Alert>
      )}

      <Card tone="soft" className="flex items-start gap-3">
        <Info size={20} className="mt-0.5 flex-none text-ink3" aria-hidden />
        <p className="text-sub text-ink2">When you add it, we check it against your other medicines. If we cannot find it, it shows as Not checked.</p>
      </Card>

      <Footer>
        <Button icon={CheckCircle} disabled={!valid || confirm.isPending} onClick={save}>
          {confirm.isPending ? 'Adding…' : 'Add to my medicines'}
        </Button>
      </Footer>
    </Screen>
  )
}
