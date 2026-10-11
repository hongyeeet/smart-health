import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { cn } from '@/lib/cn'
import { Button, Field } from '@/ui/primitives'
import { fmtAmount, parseAmount } from './mealMath'

interface Props {
  label: string
  /** unit shown after the number, for example g, mg or kcal */
  unit: string
  /** the number as shown (already scaled by the portion); null when the reading could not judge it */
  value: number | null
  /** where the number came from: the photo reading, the person, or nowhere (not judged) */
  source: 'estimate' | 'you'
  /** saves a new number in the same units as `value`; null means "not known" */
  onSave: (v: number | null) => void
  /** the calories line is shown large */
  big?: boolean
}

/**
 * One nutrient on the macro card. A number from the photo is marked "estimate". A value the reading could not judge
 * says "Not judged" and offers a box to type one in. Any number can be changed; a blank box puts it back to not judged.
 */
export function MacroRow({ label, unit, value, source, onSave, big = false }: Props) {
  const { t } = useTranslation()
  const [editing, setEditing] = useState(false)
  const [text, setText] = useState('')
  const [bad, setBad] = useState(false)

  const open = () => {
    setText(fmtAmount(value))
    setBad(false)
    setEditing(true)
  }
  const save = () => {
    const r = parseAmount(text)
    if (!r.ok) {
      setBad(true)
      return
    }
    onSave(r.value)
    setEditing(false)
  }

  if (editing) {
    return (
      <div className="flex flex-col gap-3 py-3">
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
          <Button size="md" variant="secondary" onClick={() => setEditing(false)}>
            {t('log.meal.cancelNumber', 'Cancel')}
          </Button>
        </div>
      </div>
    )
  }

  const sourceText = value == null ? t('log.meal.notJudgedNote', 'The photo was not clear enough to judge this.') : source === 'you' ? t('log.meal.yourNumber', 'Your number') : t('log.meal.estimate', 'Estimate')

  return (
    <div className={cn('flex flex-wrap items-center justify-between gap-x-4 gap-y-2 py-3', !big && 'border-b border-line last:border-b-0')}>
      <div className="min-w-0 flex-1">
        <p className="text-body font-bold text-ink">{label}</p>
        <p className="text-micro text-ink3">{sourceText}</p>
      </div>
      <div className="flex items-center gap-3">
        <p className={cn('num text-ink', big ? 'text-display' : 'text-h2')}>
          {value == null ? (
            <span className="text-body font-bold text-ink2">{t('log.meal.notJudged', 'Not judged')}</span>
          ) : (
            <>
              {fmtAmount(value)} <span className="text-sub text-ink2">{unit}</span>
            </>
          )}
        </p>
        <button type="button" onClick={open} className="press min-h-12 rounded-chip px-3 text-sub font-bold text-brand underline decoration-1 underline-offset-4">
          {value == null ? t('log.meal.typeIn', 'Type it in') : t('log.meal.change', 'Change')}
        </button>
      </div>
    </div>
  )
}
