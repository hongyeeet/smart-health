import { useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { useScan } from '@/data/hooks'
import { href } from '@/app/routeIds'
import type { ScanField } from '@/data/types'
import { Footer, Header, Screen } from '@/ui/layout'
import { Button, Card, Chip, ConfidenceChip, Field, SectionTitle, Skeleton, StatusPill } from '@/ui/primitives'
import { CheckCircle, PencilSimple, Warning } from '@/ui/icons'

/**
 * H3 — Check what we read: the AI extraction review screen.
 *
 * Every field shows a confidence chip. Fields below 0.85 confidence (level 'check') must be
 * tapped to confirm before the Confirm button enables. Any field can be edited inline — tap
 * the pencil and type the correction. Fields that are unreadable show a text input.
 *
 * Nothing saves until the user clicks Confirm and goes to H4.
 */
export function ScanReview() {
  const navigate = useNavigate()
  const location = useLocation()
  const scanId = (location.state as { scanId?: string } | null)?.scanId
  const { data, isLoading } = useScan(scanId)
  const [confirmed, setConfirmed] = useState<Record<string, boolean>>({})
  const [editing, setEditing] = useState<Record<string, boolean>>({})
  const [edits, setEdits] = useState<Record<string, string>>({})

  const fields = data?.fields ?? []
  const lowConfidenceFields = fields.filter((f) => f.level === 'check')
  const allLowConfirmed = lowConfidenceFields.every((f) => confirmed[f.key])
  const canConfirm = data != null && allLowConfirmed && data.status !== 'failed'

  const getDisplayValue = (f: ScanField): string => {
    if (editing[f.key]) return edits[f.key] ?? f.value ?? ''
    return f.value ?? ''
  }

  const handleConfirm = () => {
    // Build the edited-fields map to pass to H4 → confirm
    const edited: Record<string, string | null> = {}
    for (const f of fields) {
      if (editing[f.key]) {
        edited[f.key] = edits[f.key] ?? null
      }
    }
    navigate(href('H4'), { state: { scanId: data!.scanId, edits } })
  }

  if (isLoading || !data) {
    return (
      <Screen>
        <Header title="Check what we read" back backTo="H2" sub="Step 2 of 3" />
        <Skeleton className="h-64" />
      </Screen>
    )
  }

  if (data.status === 'failed') {
    return (
      <Screen>
        <Header title="Check what we read" back backTo="H2" />
        <Card tone="soft" className="flex flex-col gap-3">
          <StatusPill tone="warn" icon={Warning}>Could not read the label</StatusPill>
          <p className="text-body text-ink2">{data.error ?? 'The AI could not extract any fields from this photo.'}</p>
          <p className="text-sub text-ink3">Try retaking the photo with better light, or add the medicine by hand.</p>
        </Card>
        <Footer>
          <Button variant="secondary" onClick={() => navigate(href('H2'))}>
            Retake photo
          </Button>
        </Footer>
      </Screen>
    )
  }

  return (
    <Screen>
      <Header
        title="Check what we read"
        back
        backTo="H2"
        sub="Step 2 of 3 — nothing is saved until you confirm"
      />

      {data.description && (
        <Card tone="soft" className="flex flex-col gap-2">
          <SectionTitle>What the AI thinks this is</SectionTitle>
          <p className="text-body font-bold text-ink">{data.drug}</p>
          <p className="text-sub text-ink2">{data.description}</p>
        </Card>
      )}

      <ul className="flex flex-col gap-3">
        {fields.map((f) => (
          <li key={f.key}>
            <FieldCard
              field={f}
              isEditing={editing[f.key] ?? false}
              displayValue={getDisplayValue(f)}
              confirmed={confirmed[f.key] ?? false}
              onToggleEdit={() => {
                setEditing((p) => ({ ...p, [f.key]: !p[f.key] }))
                if (!editing[f.key]) {
                  setEdits((p) => ({ ...p, [f.key]: f.value ?? '' }))
                }
              }}
              onValueChange={(v) => setEdits((p) => ({ ...p, [f.key]: v }))}
              onToggleConfirm={() => setConfirmed((p) => ({ ...p, [f.key]: !p[f.key] }))}
            />
          </li>
        ))}
      </ul>

      {lowConfidenceFields.length > 0 && !allLowConfirmed && (
        <Card tone="soft" className="flex items-start gap-3">
          <Warning size={20} className="mt-0.5 flex-none text-warn" aria-hidden />
          <p className="text-sub text-ink2">
            {lowConfidenceFields.length} field{lowConfidenceFields.length > 1 ? 's' : ''} need{lowConfidenceFields.length === 1 ? 's' : ''} your
            confirmation. Tap each "Tap to confirm" to verify.
          </p>
        </Card>
      )}

      <Footer>
        <Button icon={CheckCircle} disabled={!canConfirm} onClick={handleConfirm}>
          Confirm
        </Button>
        <Button variant="secondary" onClick={() => navigate(href('H2'))}>
          Retake photo
        </Button>
      </Footer>
    </Screen>
  )
}

function FieldCard({
  field,
  isEditing,
  displayValue,
  confirmed,
  onToggleEdit,
  onValueChange,
  onToggleConfirm,
}: {
  field: ScanField
  isEditing: boolean
  displayValue: string
  confirmed: boolean
  onToggleEdit: () => void
  onValueChange: (v: string) => void
  onToggleConfirm: () => void
}) {
  const isUnreadable = field.level === 'unreadable'
  const isLowConfidence = field.level === 'check'
  const showEdit = !isUnreadable && !isEditing

  return (
    <Card className="flex flex-col gap-2">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="text-sub font-bold text-ink2">{field.label}</span>
        <ConfidenceChip level={field.level} />
      </div>

      {isUnreadable || isEditing ? (
        <Field
          label={isUnreadable ? "I can't read this, please type it" : 'Edit value'}
          value={displayValue}
          onChange={onValueChange}
          hint={isUnreadable ? 'You can leave this empty.' : undefined}
        />
      ) : (
        <div className="flex items-center justify-between gap-2">
          <p className="text-h2 font-bold">{field.value ?? '—'}</p>
          {showEdit && (
            <button
              type="button"
              onClick={onToggleEdit}
              className="press flex h-10 w-10 flex-none items-center justify-center rounded-full bg-well text-ink2"
              aria-label="Edit this field"
            >
              <PencilSimple size={18} aria-hidden />
            </button>
          )}
        </div>
      )}

      {field.sourceText && (
        <p className="text-micro text-ink3">Label text: "{field.sourceText}"</p>
      )}

      {isLowConfidence && (
        <Chip on={confirmed} onClick={onToggleConfirm} className="self-start">
          {confirmed ? 'Confirmed' : 'Tap to confirm'}
        </Chip>
      )}

      {isEditing && (
        <Button variant="ghost" size="md" onClick={onToggleEdit}>
          Done editing
        </Button>
      )}
    </Card>
  )
}
