import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { cn } from '@/lib/cn'
import { Button, Field } from '@/ui/primitives'
import { fmtAmount, fmtShown, parseAmount } from './mealMath'

export type AmountSource = 'estimate' | 'you'

/** The short word under a number: the person's own, the photo's estimate, or not judged. */
export function sourceWord(value: number | null, source: AmountSource, t: (k: string, d: string) => string) {
  return value == null ? t('log.meal.notJudged', 'Not judged') : source === 'you' ? t('log.meal.yourNumber', 'Your number') : t('log.meal.estimate', 'Estimate')
}

interface TileProps {
  label: string
  /** unit shown after the number, for example g, mg or kcal */
  unit: string
  /** the number as shown (already scaled by the portion); null when the reading could not judge it */
  value: number | null
  /** where the number came from: the photo reading or the person */
  source: AmountSource
  /** a photo flag (high salt or high sugar) colours the tile; colour only, no extra wording */
  flagged?: boolean
  onChange: () => void
}

/**
 * One nutrient in the totals row. A number from the photo is an estimate, the person's own number says so, and a value the
 * reading could not judge says "Not judged" with a box to type one in. The numbers never wrap.
 */
export function MacroTile({ label, unit, value, source, flagged = false, onChange }: TileProps) {
  const { t } = useTranslation()
  const word = sourceWord(value, source, t)
  return (
    <div className={cn('flex min-w-0 flex-col gap-1 rounded-card border p-3', flagged ? 'border-warn/40 bg-warn-soft' : 'border-line bg-card')}>
      <p className="break-words text-micro font-bold text-ink2">{label}</p>
      <p className="num whitespace-nowrap text-h2 font-bold text-ink">
        {value == null ? (
          <span className="text-sub font-bold text-ink2">{t('log.meal.notJudged', 'Not judged')}</span>
        ) : (
          <>
            {fmtShown(value)} <span className="text-micro font-normal text-ink2">{unit}</span>
          </>
        )}
      </p>
      <p className={cn('flex items-center gap-1.5 text-micro font-bold', flagged ? 'text-warn' : 'text-ink2')}>
        <span className="h-2 w-2 flex-none rounded-full bg-current" aria-hidden />
        {word}
      </p>
      <button
        type="button"
        onClick={onChange}
        className="press -ml-1 self-start rounded-chip px-1 text-sub font-bold text-brand underline decoration-1 underline-offset-4"
      >
        {value == null ? t('log.meal.typeIn', 'Type it in') : t('log.meal.change', 'Change')}
        <span className="sr-only"> {label}</span>
      </button>
    </div>
  )
}

interface EditorProps {
  label: string
  unit: string
  value: number | null
  /** saves a new number in the same units as `value`; a blank box means "not known" */
  onSave: (v: number | null) => void
  onCancel: () => void
}

/** The box that opens under the totals when a number is changed. Only a number from 0 to 100000 is saved. */
export function MacroEditor({ label, unit, value, onSave, onCancel }: EditorProps) {
  const { t } = useTranslation()
  const [text, setText] = useState(() => fmtAmount(value))
  const [bad, setBad] = useState(false)

  const save = () => {
    const r = parseAmount(text)
    if (!r.ok) {
      setBad(true)
      return
    }
    onSave(r.value)
  }

  return (
    <div className="flex flex-col gap-3 rounded-card border border-line bg-card p-4">
      <Field
        label={label}
        suffix={unit}
        inputMode="decimal"
        value={text}
        onChange={(v) => {
          setText(v)
          setBad(false)
        }}
        error={bad ? t('log.meal.numberError', 'Please type a number, 0 or more. Leave it blank if you do not know.') : undefined}
      />
      <div className="grid grid-cols-2 gap-2">
        <Button size="md" onClick={save}>
          {t('log.meal.saveNumber', 'Save')}
        </Button>
        <Button size="md" variant="secondary" onClick={onCancel}>
          {t('log.meal.cancelNumber', 'Cancel')}
        </Button>
      </div>
    </div>
  )
}
