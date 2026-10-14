import { useState } from 'react'
import { dateLocale } from '@/lib/locale'
import { Navigate, useLocation, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useScan } from '@/data/hooks'
import { href } from '@/app/routeIds'
import type { ScanField } from '@/data/types'
import { Footer, Header, Screen } from '@/ui/layout'
import { Alert, Button, Card, Chip, ConfidenceChip, Field, SectionTitle, Skeleton } from '@/ui/primitives'
import { CheckCircle, PencilSimple, Warning } from '@/ui/icons'
import { NOT_READ_CODES, useScanFailureText } from './scanMessages'

/** The standard bar for a field. The medicine NAME is read with a lower bar (0.6), so below this bar it still needs a tick here. */
const STANDARD_BAR = 0.85

/** A field the person must tick before Confirm: every "check" field, and the name whenever it is below the standard bar. */
function needsTick(f: ScanField): boolean {
  return f.level === 'check' || (f.key === 'name' && f.value != null && f.confidence < STANDARD_BAR)
}

/**
 * H3 — Check what we read: shown for ONE medicine read clearly (reviewMode "confirm"). Every field is listed with its confidence; the
 * person can correct any field with the pencil. The printed name from the label photo is always shown beside the read name, and the
 * name needs a tick ("This is the right name") when it is below the standard bar. Anything else goes on: a photo that gave no medicine
 * shows what happened with Retake and Type it in; a partial read goes straight to the typed form (H8), which says why (D-064).
 * Nothing is saved on this screen: Confirm goes on to H4, where the dose times are chosen.
 */
export function ScanReview() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const location = useLocation()
  const scanId = (location.state as { scanId?: string } | null)?.scanId
  const { data, isLoading, isError, refetch } = useScan(scanId)
  const failureText = useScanFailureText()
  const [confirmed, setConfirmed] = useState<Record<string, boolean>>({})
  const [editing, setEditing] = useState<Record<string, boolean>>({})
  const [edits, setEdits] = useState<Record<string, string>>({})

  if (!scanId) return <Navigate to={href('H2')} replace />

  if (isError) {
    return (
      <Screen narrow>
        <Header title={t('scanReview.title', 'Check what we read')} back backTo="H2" />
        <Alert tone="warn" title={t('scanReview.offline', 'We could not reach Equinox')}>
          {t('scanReview.offlineBody', 'Check your connection and try again. Nothing has been saved.')}
        </Alert>
        <Footer>
          <Button onClick={() => void refetch()}>{t('scanReview.retry', 'Try again')}</Button>
          <Button variant="secondary" onClick={() => navigate(href('H2'))}>
            {t('scanReview.retake', 'Retake')}
          </Button>
        </Footer>
      </Screen>
    )
  }

  if (isLoading || !data) {
    return (
      <Screen narrow>
        <Header title={t('scanReview.title', 'Check what we read')} back backTo="H2" sub={t('scanReview.step', 'Step 2 of 3')} />
        <Skeleton className="h-64" />
      </Screen>
    )
  }

  const code = data.errorCode ?? null
  const notRead = data.status === 'failed' || (data.reviewMode === 'manual' && code != null && NOT_READ_CODES.has(code))
  if (notRead) {
    return (
      <Screen narrow>
        <Header title={t('scanReview.title', 'Check what we read')} back backTo="H2" />
        <Alert tone="warn" title={t('scanReview.photoNotRead', 'Photo not read')}>
          {failureText(code)}
        </Alert>
        <Footer>
          {/* On a paused day a new photo is refused too, so typing is the only way forward */}
          {code !== 'daily_limit' && (
            <Button variant="secondary" onClick={() => navigate(href('H2'))}>
              {t('scanReview.retake', 'Retake')}
            </Button>
          )}
          <Button onClick={() => navigate(href('H8'))}>{t('scanReview.typeIt', 'Type it in')}</Button>
        </Footer>
      </Screen>
    )
  }

  // D-064: a partial read is completed by typing, not by a tap. The form opens blank and says why.
  if (data.reviewMode === 'manual') {
    return <Navigate to={href('H8')} replace state={{ scanId: data.scanId, notice: data.notice }} />
  }

  const fields = data.fields
  const ticks = fields.filter(needsTick)
  const allTicked = ticks.every((f) => confirmed[f.key])
  const canConfirm = allTicked

  const getDisplayValue = (f: ScanField): string => {
    if (editing[f.key]) return edits[f.key] ?? f.value ?? ''
    return f.value ?? ''
  }

  const handleConfirm = () => {
    navigate(href('H4'), { state: { scanId: data.scanId, edits } })
  }

  return (
    <Screen narrow>
      <Header title={t('scanReview.title', 'Check what we read')} back backTo="H2" sub={t('scanReview.subStep', 'Step 2 of 3. Nothing is saved until you confirm.')} />

      {data.description && (
        <Card tone="soft" className="flex flex-col gap-2">
          <SectionTitle>{t('scanReview.aiThinks', 'What the AI thinks this is')}</SectionTitle>
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
              tick={needsTick(f)}
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

      {ticks.length > 0 && !allTicked && (
        <Card tone="soft" className="flex items-start gap-3">
          <Warning size={20} className="mt-0.5 flex-none text-warn" aria-hidden />
          <p className="text-sub text-ink2">
            {t('scanReview.needTicks', 'Please check the fields marked "Check this" and tick each one before you confirm.')}
          </p>
        </Card>
      )}

      <Footer>
        <Button icon={CheckCircle} disabled={!canConfirm} onClick={handleConfirm}>
          {t('scanReview.confirm', 'Confirm')}
        </Button>
        <Button variant="secondary" onClick={() => navigate(href('H2'))}>
          {t('scanReview.retake', 'Retake')}
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
  tick,
  onToggleEdit,
  onValueChange,
  onToggleConfirm,
}: {
  field: ScanField
  isEditing: boolean
  displayValue: string
  confirmed: boolean
  tick: boolean
  onToggleEdit: () => void
  onValueChange: (v: string) => void
  onToggleConfirm: () => void
}) {
  const { t } = useTranslation()
  const isUnreadable = field.level === 'unreadable'
  const isName = field.key === 'name'
  const showEdit = !isUnreadable && !isEditing && EDITABLE.has(field.key)
  const label = t(`scanReview.field.${field.key}`, field.label)

  return (
    <Card className="flex flex-col gap-2">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="text-sub font-bold text-ink2">{label}</span>
        <ConfidenceChip level={field.level} />
      </div>

      {isUnreadable || isEditing ? (
        <Field
          label={isUnreadable ? t('scanReview.cantRead', "I can't read this, please type it") : t('scanReview.editValue', 'Edit value')}
          value={displayValue}
          onChange={onValueChange}
          hint={isUnreadable ? t('scanReview.canLeaveEmpty', 'You can leave this empty.') : undefined}
        />
      ) : (
        <div className="flex items-center justify-between gap-2">
          <p className="break-words text-h2 font-bold">{pretty(field, t)}</p>
          {showEdit && (
            <button
              type="button"
              onClick={onToggleEdit}
              className="press flex h-10 w-10 flex-none items-center justify-center rounded-full bg-well text-ink2"
              aria-label={t('scanReview.editField', 'Edit this field')}
            >
              <PencilSimple size={18} aria-hidden />
            </button>
          )}
        </div>
      )}

      {isName && !isUnreadable && !isEditing && (
        <p className="break-words text-sub text-ink2">
          {t('scanReview.printedOnLabel', 'Printed on the label:')}{' '}
          <span className="font-bold text-ink">
            {field.sourceText ? `“${field.sourceText}”` : t('scanReview.notFound', 'not found on the photo')}
          </span>
        </p>
      )}

      {field.sourceText && !isName && <p className="text-micro text-ink3">{t('scanReview.labelText', 'Label text:')} "{field.sourceText}"</p>}

      {tick && (
        <Chip on={confirmed} onClick={onToggleConfirm} className="self-start">
          {isName
            ? t('scanReview.rightName', 'This is the right name')
            : confirmed
              ? t('scanReview.confirmedChip', 'Confirmed')
              : t('scanReview.tapToConfirm', 'Tap to confirm')}
        </Chip>
      )}

      {isEditing && (
        <Button variant="ghost" size="md" onClick={onToggleEdit}>
          {t('scanReview.doneEditing', 'Done editing')}
        </Button>
      )}
    </Card>
  )
}

/** Fields the person can retype here. The coded ones (when, before or after food, the date) are chosen on the next screen or in the form,
 *  and "times a day" is the number of dose times on the next screen. */
const EDITABLE = new Set(['name', 'strength', 'dose_amount', 'dose_unit', 'directions', 'prescriber', 'total_quantity'])

type Translate = ReturnType<typeof useTranslation>['t']

/** The label value in plain words: codes and ISO dates are shown the way a person says them. */
function pretty(f: ScanField, t: Translate): string {
  const v = f.value
  if (v == null) return '—'
  switch (f.key) {
    case 'meal_relation':
      return ({ before_meal: t('scanReview.meal.before', 'Before meals'), after_meal: t('scanReview.meal.after', 'After meals'),
        with_meal: t('scanReview.meal.with', 'With food'), na: t('scanReview.meal.either', 'With or without food') } as Record<string, string>)[v] ?? v
    case 'when_to_take':
      return ({ morning: t('scanReview.when.morning', 'Morning'), noon: t('scanReview.when.noon', 'Noon'), afternoon: t('scanReview.when.afternoon', 'Afternoon'),
        evening: t('scanReview.when.evening', 'Evening'), night: t('scanReview.when.night', 'Night'), bedtime: t('scanReview.when.bedtime', 'At bedtime'),
        as_needed: t('scanReview.when.needed', 'When needed') } as Record<string, string>)[v] ?? v
    case 'meal_offset_minutes':
      return t('scanReview.minutes', '{{n}} minutes', { n: v })
    case 'drowsiness_warning':
      return t('scanReview.drowsy', 'The label warns it may cause drowsiness')
    case 'times_per_day':
      return v === '1' ? t('scanReview.onceADay', 'Once a day') : t('scanReview.timesADay', '{{n}} times a day', { n: v })
    case 'start_date': {
      const d = new Date(`${v}T00:00:00`)
      return Number.isNaN(d.getTime()) ? v : d.toLocaleDateString(dateLocale('en-GB'), { day: 'numeric', month: 'short', year: 'numeric' })
    }
    default:
      return v
  }
}
