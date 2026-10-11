import { useTranslation } from 'react-i18next'
import { Alert, Card, EstimateBadge, Field, Stepper, StatusPill } from '@/ui/primitives'
import { Info, Warning } from '@/ui/icons'
import type { FoodNote, Macros } from '@/data/types'
import { fmtPortion, type NutrientKey } from './mealMath'
import { MacroRow } from './MacroRow'

interface Props {
  name: string
  onName: (v: string) => void
  items: string[]
  confidence: 'high' | 'check'
  /** the numbers for the amount eaten, already scaled by the portion */
  shown: Macros
  /** which numbers the person has typed in themselves */
  touched: Partial<Record<NutrientKey, true>>
  onAmount: (k: NutrientKey, v: number | null) => void
  flags: ('high_salt' | 'high_sugar')[]
  /** true when the person changed numbers, so the flags are from the photo reading, not the numbers shown */
  changed: boolean
  portionNote: string
  portion: number
  onPortion: (v: number) => void
  note: FoodNote | null
}

/** Step 3: the estimate as a macro card. Calories are shown large; each nutrient says whether it is an estimate, the person's number or not judged. */
export function MealResult(p: Props) {
  const { t } = useTranslation()
  const src = (k: NutrientKey) => (p.touched[k] ? 'you' : 'estimate') as 'you' | 'estimate'
  const rows: { k: NutrientKey; label: string; unit: string }[] = [
    { k: 'carbsG', label: t('log.meal.carbs', 'Carbohydrate'), unit: 'g' },
    { k: 'proteinG', label: t('log.meal.protein', 'Protein'), unit: 'g' },
    { k: 'fatG', label: t('log.meal.fat', 'Fat'), unit: 'g' },
    { k: 'sugarG', label: t('log.meal.sugar', 'Sugar'), unit: 'g' },
    { k: 'fibreG', label: t('log.meal.fibre', 'Fibre'), unit: 'g' },
    { k: 'sodiumMg', label: t('log.meal.saltSodium', 'Salt (sodium)'), unit: 'mg' },
  ]

  return (
    <>
      <Card tone="hero" className="flex flex-col gap-4">
        <div className="flex items-start justify-between gap-3">
          <p className="min-w-0 break-words text-sub font-bold text-ink3">{t('log.meal.dish', 'Dish')}</p>
          <EstimateBadge />
        </div>
        <Field label={t('log.meal.name', 'Dish name')} value={p.name} onChange={p.onName} />
        {p.items.length > 0 && (
          <div className="flex flex-col gap-2">
            <p className="text-sub font-bold text-ink3">{t('log.meal.items', 'What we can see')}</p>
            <ul className="flex flex-wrap gap-2">
              {p.items.map((item, i) => (
                <li key={`${item}-${i}`} className="break-words rounded-chip bg-well px-3 py-1 text-sub text-ink">
                  {item}
                </li>
              ))}
            </ul>
          </div>
        )}
        {p.confidence === 'check' && <StatusPill tone="warn">{t('log.meal.checkPortion', 'Check this: we are less sure about the portion')}</StatusPill>}

        <MacroRow label={t('log.meal.calories', 'Calories')} unit="kcal" value={p.shown.kcal} source={src('kcal')} big onSave={(v) => p.onAmount('kcal', v)} />

        <div className="flex flex-col">
          {rows.map((r) => (
            <MacroRow key={r.k} label={r.label} unit={r.unit} value={p.shown[r.k]} source={src(r.k)} onSave={(v) => p.onAmount(r.k, v)} />
          ))}
        </div>

        {p.flags.length > 0 && (
          <div className="flex flex-col gap-2">
            <div className="flex flex-wrap gap-2">
              {p.flags.includes('high_salt') && <StatusPill tone="warn" icon={Warning}>{t('log.meal.highSalt', 'High salt')}</StatusPill>}
              {p.flags.includes('high_sugar') && <StatusPill tone="warn" icon={Warning}>{t('log.meal.highSugar', 'High sugar')}</StatusPill>}
            </div>
            <p className="text-micro text-ink3">
              {p.changed
                ? t('log.meal.flagsBeforeChanges', 'These flags were worked out from the photo reading, before your changes.')
                : t('log.meal.flagsNote', 'These flags are worked out from the numbers. They are notes, not advice.')}
            </p>
          </div>
        )}
      </Card>

      <div className="flex flex-col gap-2">
        <p className="text-body font-bold text-ink">{t('log.meal.portion', 'Portion')}</p>
        <Stepper label={t('log.meal.portionLabel', 'portion')} value={p.portion} onChange={p.onPortion} min={0.5} max={3} step={0.5} format={fmtPortion} />
        <p className="text-sub text-ink2">{t('log.meal.portionHelp', 'Change the portion to scale every number above.')}</p>
      </div>

      {p.portionNote && <p className="text-sub text-ink2">{t('log.meal.assumed', 'What we assumed: {{note}}', { note: p.portionNote })}</p>}
      <p className="text-sub text-ink3">{t('log.meal.estimates', 'Nutrients are estimates until you confirm them. Your glucose rise will come from the sensor.')}</p>

      {p.note && (
        <Alert tone={p.note.kind === 'higher' ? 'warn' : 'info'} icon={Info} title={t('log.meal.usual', 'Your usual response')}>
          {p.note.text}
          {p.note.range && (
            <span className="mt-1 block text-ink2">
              {t('log.meal.seen', 'Seen {{n}} times, rise {{from}} to {{to}} mmol/L.', { n: p.note.n, from: p.note.range[0].toFixed(1), to: p.note.range[1].toFixed(1) })}
            </span>
          )}
        </Alert>
      )}
    </>
  )
}
