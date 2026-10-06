import { useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { useScan, useConfirmScan } from '@/data/hooks'
import { useUi } from '@/state/store'
import { href } from '@/app/routeIds'
import { useGo } from '@/app/navigation'
import { Footer, Header, Screen } from '@/ui/layout'
import { Alert, Button, Card, SectionTitle, Skeleton } from '@/ui/primitives'
import { CheckCircle, Info, Pill, WarningCircle } from '@/ui/icons'

/**
 * H4 — Your dose plan: shows the parsed schedule and medicine description.
 * The user can adjust dose times and the "with food" toggle, then click "Add to my medicines"
 * to save. The confirm mutation sends the edited fields to POST /scans/{id}/confirm, which
 * (in E3-2) saves patient_medications + dose_events + clash check in one transaction.
 */
export function ScanPlan() {
  const navigate = useNavigate()
  const go = useGo()
  const location = useLocation()
  const scanId = (location.state as { scanId?: string } | null)?.scanId
  const edits = (location.state as { edits?: Record<string, string> } | null)?.edits ?? {}
  const { data, isLoading } = useScan(scanId)
  const confirm = useConfirmScan()
  const showToast = useUi((s) => s.showToast)
  const [timeEdits, setTimeEdits] = useState<Record<number, string>>({})
  const [purpose] = useState('')

  if (isLoading || !data) {
    return (
      <Screen>
        <Header title="Your dose plan" back backTo="H3" />
        <Skeleton className="h-48" />
      </Screen>
    )
  }

  if (data.status === 'failed') {
    return (
      <Screen>
        <Header title="Your dose plan" back backTo="H3" />
        <Alert tone="warn" title="No plan available">
          The scan could not be read. Please go back and retake the photo, or add the medicine by hand.
        </Alert>
        <Footer>
          <Button variant="secondary" onClick={() => navigate(href('H2'))}>
            Retake photo
          </Button>
        </Footer>
      </Screen>
    )
  }

  const schedule = data.schedule
  const medName = edits['name'] ?? data.drug
  const description = data.description

  const handleConfirm = () => {
    // Merge the field edits from H3 + any time edits here into the confirm payload
    const allEdits: Record<string, string | null> = { ...edits }
    if (purpose) allEdits['purpose'] = purpose
    // Time edits are part of the schedule, sent as a separate key
    const timeOverrides = Object.entries(timeEdits)
      .filter(([, v]) => v.trim())
      .map(([i, v]) => ({ index: Number(i), time: v }))
    if (timeOverrides.length) {
      allEdits['schedule_times'] = JSON.stringify(timeOverrides)
    }

    confirm.mutate(
      { scanId: data.scanId, fields: allEdits },
      {
        onSuccess: () => {
          navigate(href('H1'), { replace: true })
          showToast('Added to your medicines')
          // If there's an interaction, show the sheet after a brief delay
          if (data.interaction) {
            setTimeout(() => go('H5'), 350)
          }
        },
      },
    )
  }

  return (
    <Screen>
      <Header title="Your dose plan" back backTo="H3" sub="Step 3 of 3" />

      <Card className="flex flex-col gap-3">
        <div className="flex items-start gap-3">
          <span className="flex h-11 w-11 flex-none items-center justify-center rounded-full bg-brand-soft text-brand">
            <Pill size={22} aria-hidden />
          </span>
          <div className="min-w-0 flex-1">
            <p className="text-h2 font-bold leading-tight">{medName}</p>
            {data.itemType !== 'unknown' && (
              <p className="text-sub text-ink2">{itemTypeLabel(data.itemType)}</p>
            )}
          </div>
        </div>

        {description && (
          <div className="rounded-card bg-well p-3">
            <SectionTitle>What it's for</SectionTitle>
            <p className="text-body text-ink2">{description}</p>
          </div>
        )}
      </Card>

      {schedule.length > 0 && (
        <Card className="flex flex-col gap-3">
          <SectionTitle>Dose schedule</SectionTitle>
          <ul className="divide-y divide-line">
            {schedule.map((s, i) => (
              <li key={i} className="flex items-center justify-between gap-3 py-3 text-body">
                <span className="text-ink2">{s.label}</span>
                <input
                  value={timeEdits[i] ?? s.time}
                  onChange={(e) => setTimeEdits((p) => ({ ...p, [i]: e.target.value }))}
                  className="w-32 rounded-field border-[1.5px] border-line bg-card px-2.5 py-1.5 text-right font-bold text-ink focus:border-brand focus:outline-none"
                  aria-label={`Dose time for ${s.label}`}
                />
              </li>
            ))}
          </ul>
          <p className="text-sub text-ink3">Tap a time to adjust it. Times come from your label.</p>
        </Card>
      )}

      {schedule.length === 0 && (
        <Card tone="soft" className="flex items-start gap-3">
          <Info size={20} className="mt-0.5 flex-none text-ink3" aria-hidden />
          <p className="text-sub text-ink2">
            No dose schedule was found on the label. You can add the medicine and set the times yourself later.
          </p>
        </Card>
      )}

      {data.interaction && (
        <Alert tone="warn" title="Possible interaction" icon={WarningCircle}>
          <strong>{data.interaction.a}</strong> may interact with <strong>{data.interaction.b}</strong>. Please check
          with your pharmacist or doctor before continuing.
        </Alert>
      )}

      <Card tone="soft" className="flex items-start gap-3">
        <Info size={20} className="mt-0.5 flex-none text-ink3" aria-hidden />
        <p className="text-sub text-ink2">
          When you add it, we check it against your other medicines and tell you if there is something to ask about.
        </p>
      </Card>

      <Footer>
        <Button icon={CheckCircle} disabled={confirm.isPending} onClick={handleConfirm}>
          {confirm.isPending ? 'Adding…' : 'Add to my medicines'}
        </Button>
      </Footer>
    </Screen>
  )
}

function itemTypeLabel(type: string): string {
  const labels: Record<string, string> = {
    prescription_label: 'Prescription',
    blister_or_box: 'Box / blister pack',
    supplement: 'Supplement',
    tcm: 'Traditional medicine',
    otc: 'Over-the-counter',
    unknown: 'Unknown type',
  }
  return labels[type] ?? type
}
