/**
 * E3 — Log blood pressure (manual entry only).
 *
 * Two large number fields (the top number, which is the higher one, and the bottom number), an optional pulse, the date and
 * time taken (now by default) and an optional note. The limits are the server's (services/api/app/schemas/log.py) and the
 * messages say what to change, in plain words. The screen records the numbers only: it never says whether a reading is
 * normal, high or low. Save goes to E6 (Saved).
 *
 * `BloodPressureForm` is also used by the edit sheet (E7), which passes the reading to change as `initial`.
 */
import { useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import type { TFunction } from 'i18next'
import { useNavigate } from 'react-router-dom'
import { useLog } from '@/data/hooks'
import type { BloodPressureEntry } from '@/data/types'
import type { BloodPressureLogInput } from '@/data/repositories/types'
import { href } from '@/app/routeIds'
import { useUi } from '@/state/store'
import { Header, Footer, Screen } from '@/ui/layout'
import { Alert, Button, Card, Field } from '@/ui/primitives'

/** Limits used here must match the server's (schemas/log.py). */
const SYSTOLIC = [60, 260] as const
const DIASTOLIC = [30, 150] as const
const PULSE = [30, 220] as const
const NOTE_MAX = 300
/** the server's sentence when a reading already exists at that time (routers/logs.py BP_DUPLICATE) */
const DUPLICATE = 'You already have a reading saved at that time.'

interface Values {
  top: string
  bottom: string
  pulse: string
  date: string
  time: string
  note: string
}
type FieldName = keyof Values
type Errors = Partial<Record<FieldName, string>>

const pad = (n: number) => String(n).padStart(2, '0')
const dayText = (d: Date) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
const clockText = (d: Date) => `${pad(d.getHours())}:${pad(d.getMinutes())}`
const WHOLE = /^\d+$/

/** The number typed as a whole number, or null when it is not one. */
function whole(s: string): number | null {
  const x = s.trim()
  return WHOLE.test(x) ? Number(x) : null
}

function startValues(e?: BloodPressureEntry | null): Values {
  const when = e ? new Date(e.measuredAt) : new Date()
  return {
    top: e ? String(e.systolic) : '',
    bottom: e ? String(e.diastolic) : '',
    pulse: e?.pulse != null ? String(e.pulse) : '',
    date: dayText(when),
    time: clockText(when),
    note: e?.note ?? '',
  }
}

/** Every rule that stops a save, each with a plain message. A field with no message can be saved. */
function checkValues(v: Values, t: TFunction): Errors {
  const e: Errors = {}
  const top = whole(v.top)
  if (!v.top.trim()) e.top = t('log.bp.errTopMissing', 'Type the top number.')
  else if (top === null) e.top = t('log.bp.errWhole', 'Use whole numbers only.')
  else if (top < SYSTOLIC[0] || top > SYSTOLIC[1]) e.top = t('log.bp.errTop', 'The top number should be between {{min}} and {{max}}.', { min: SYSTOLIC[0], max: SYSTOLIC[1] })

  const bottom = whole(v.bottom)
  if (!v.bottom.trim()) e.bottom = t('log.bp.errBottomMissing', 'Type the bottom number.')
  else if (bottom === null) e.bottom = t('log.bp.errWhole', 'Use whole numbers only.')
  else if (bottom < DIASTOLIC[0] || bottom > DIASTOLIC[1]) e.bottom = t('log.bp.errBottom', 'The bottom number should be between {{min}} and {{max}}.', { min: DIASTOLIC[0], max: DIASTOLIC[1] })
  else if (top !== null && bottom >= top) e.bottom = t('log.bp.errPair', 'The bottom number must be lower than the top number.')

  if (v.pulse.trim()) {
    const pulse = whole(v.pulse)
    if (pulse === null) e.pulse = t('log.bp.errWhole', 'Use whole numbers only.')
    else if (pulse < PULSE[0] || pulse > PULSE[1]) e.pulse = t('log.bp.errPulse', 'The pulse should be between {{min}} and {{max}} beats a minute.', { min: PULSE[0], max: PULSE[1] })
  }

  const taken = new Date(`${v.date}T${v.time}`)
  if (!v.date || !v.time || Number.isNaN(taken.getTime())) e.time = t('log.bp.errTime', 'Choose a date and time.')
  else if (taken.getTime() > Date.now() + 60_000) e.time = t('log.bp.errFuture', 'The time taken cannot be in the future. Choose a time that has passed.')

  if (v.note.trim().length > NOTE_MAX) e.note = t('log.bp.errNote', 'Keep the note to {{max}} characters or fewer.', { max: NOTE_MAX })
  return e
}

/** The message to show when a save fails: the server's plain sentence for a clash, otherwise the general one. */
export function saveErrorText(e: Error | null, t: TFunction): string | null {
  if (!e) return null
  return e.message.startsWith(DUPLICATE) ? e.message : t('log.bp.saveError', 'It could not be saved just now. Check your connection and try again.')
}

export interface BloodPressureFormProps {
  /** the reading being edited; omitted for a new reading */
  initial?: BloodPressureEntry | null
  submitLabel: string
  pending: boolean
  error: string | null
  onSave: (input: BloodPressureLogInput) => void
}

export function BloodPressureForm({ initial, submitLabel, pending, error, onSave }: BloodPressureFormProps) {
  const { t } = useTranslation()
  const [v, setV] = useState<Values>(() => startValues(initial))
  /** a message is shown for a field only after the person has changed it */
  const [touched, setTouched] = useState<Partial<Record<FieldName, true>>>({})
  const errors = checkValues(v, t)
  const ok = Object.keys(errors).length === 0
  const shown = (k: FieldName) => (touched[k] ? errors[k] : undefined)
  const set = (k: FieldName) => (value: string) => {
    setV((prev) => ({ ...prev, [k]: value }))
    setTouched((prev) => ({ ...prev, [k]: true }))
  }

  const submit = (e: FormEvent) => {
    e.preventDefault()
    if (!ok || pending) return
    onSave({
      kind: 'blood_pressure',
      systolic: Number(v.top),
      diastolic: Number(v.bottom),
      ...(v.pulse.trim() ? { pulse: Number(v.pulse) } : {}),
      measuredAt: new Date(`${v.date}T${v.time}`).toISOString(),
      ...(v.note.trim() ? { note: v.note.trim() } : {}),
    })
  }

  return (
    <form onSubmit={submit} noValidate className="flex flex-col gap-4">
      <Card className="flex flex-col gap-5">
        <div className="grid gap-4 sm:grid-cols-2">
          <Field
            large
            inputMode="numeric"
            label={t('log.bp.top', 'Top number')}
            suffix="mmHg"
            value={v.top}
            onChange={set('top')}
            hint={t('log.bp.topHint', 'The top number is the higher one.')}
            error={shown('top')}
          />
          <Field
            large
            inputMode="numeric"
            label={t('log.bp.bottom', 'Bottom number')}
            suffix="mmHg"
            value={v.bottom}
            onChange={set('bottom')}
            hint={t('log.bp.bottomHint', 'The bottom number is the lower one.')}
            error={shown('bottom')}
          />
        </div>
        <Field
          inputMode="numeric"
          label={t('log.bp.pulse', 'Pulse (optional)')}
          value={v.pulse}
          onChange={set('pulse')}
          hint={t('log.bp.pulseHint', 'Beats a minute. Leave it empty if you did not measure it.')}
          error={shown('pulse')}
        />
        <div className="grid gap-4 sm:grid-cols-2">
          <Field type="date" label={t('log.bp.date', 'Date taken')} value={v.date} onChange={set('date')} />
          <Field
            type="time"
            label={t('log.bp.time', 'Time taken')}
            value={v.time}
            onChange={set('time')}
            hint={shown('time') ? undefined : t('log.bp.timeHint', 'Now, unless you change it.')}
            error={shown('time')}
          />
        </div>
        <Field
          multiline
          label={t('log.bp.note', 'Note (optional)')}
          value={v.note}
          onChange={set('note')}
          hint={t('log.bp.noteHint', 'For example: after a walk, or sitting down for five minutes first.')}
          error={shown('note')}
        />
      </Card>
      {error && <Alert tone="danger">{error}</Alert>}
      <Footer>
        <Button type="submit" disabled={!ok || pending}>
          {pending ? t('log.bp.saving', 'Saving…') : submitLabel}
        </Button>
      </Footer>
    </form>
  )
}

export function LogBloodPressure() {
  const { t } = useTranslation()
  const log = useLog()
  const navigate = useNavigate()
  const setLast = useUi((s) => s.setLastLog)
  return (
    <Screen narrow>
      <Header title={t('log.bp.title', 'Log blood pressure')} back backTo="E1" sub={t('log.bp.sub', 'Type the two numbers from your monitor. It takes about 20 seconds.')} />
      <BloodPressureForm
        submitLabel={t('log.bp.save', 'Save reading')}
        pending={log.isPending}
        error={saveErrorText(log.error, t)}
        onSave={(input) =>
          log.mutate(input, {
            onSuccess: (res) => {
              setLast(res)
              navigate(href('E6'), { replace: true })
            },
          })
        }
      />
    </Screen>
  )
}
