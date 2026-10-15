import { useState, type ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { Alert, Card, Field, Stepper, StatusPill } from '@/ui/primitives'
import { Segmented } from '@/ui/controls'
import { Info, Warning } from '@/ui/icons'
import type { FoodNote, Macros } from '@/data/types'
import { fmtPortion, SIZE_STEPS, type NutrientKey } from './mealMath'
import { MacroEditor, MacroTile, sourceWord, type AmountSource } from './MacroRow'

interface Props {
  /** the chosen photo, shown on the left of the card */
  photo: ReactNode
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

/**
 * Step 2, the estimate: the photo and the dish with its items, the totals as six tiles (each one can be changed), the fibre
 * line, and the notes. Changing a number opens a box under the tiles. Small, Regular and Large scale the whole meal, because
 * the analysis gives no share for each item.
 */
export function MealResult(p: Props) {
  const { t } = useTranslation()
  const [editing, setEditing] = useState<NutrientKey | null>(null)

  const src = (k: NutrientKey): AmountSource => (p.touched[k] ? 'you' : 'estimate')
  const flagged = (k: NutrientKey) => (k === 'sodiumMg' && p.flags.includes('high_salt')) || (k === 'sugarG' && p.flags.includes('high_sugar'))

  const totals: { k: NutrientKey; label: string; unit: string }[] = [
    { k: 'kcal', label: t('log.meal.calories', 'Calories'), unit: 'kcal' },
    { k: 'carbsG', label: t('log.meal.carbs', 'Carbs'), unit: 'g' },
    { k: 'proteinG', label: t('log.meal.protein', 'Protein'), unit: 'g' },
    { k: 'fatG', label: t('log.meal.fat', 'Fat'), unit: 'g' },
    { k: 'sugarG', label: t('log.meal.sugar', 'Sugar'), unit: 'g' },
    { k: 'sodiumMg', label: t('log.meal.saltSodium', 'Salt'), unit: 'mg' },
  ]
  const fibre = { k: 'fibreG' as const, label: t('log.meal.fibre', 'Fibre'), unit: 'g' }
  const editRow = [...totals, fibre].find((r) => r.k === editing)

  const sizes: { value: number; label: string }[] = SIZE_STEPS.map((v) => ({
    value: v,
    label: v === 0.5 ? t('log.meal.small', 'Small') : v === 1 ? t('log.meal.regular', 'Regular') : t('log.meal.large', 'Large'),
  }))
  const anyNotJudged = [...totals, fibre].some((r) => p.shown[r.k] == null)

  return (
    <>
      <Card className="flex flex-col gap-4">
        <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-2">
          <div className="flex min-w-0 flex-wrap items-baseline gap-x-2.5">
            <p className="text-body font-bold text-ink">{t('log.meal.found', 'What we found')}</p>
            <p className="text-sub text-ink3">{t('log.meal.justNow', 'Just now')}</p>
          </div>
          <span className="rounded-chip bg-brass-soft px-3 py-1 text-micro font-bold text-brass">
            {t('log.meal.estimatedFromPhoto', 'Estimated from your photo')}
          </span>
        </div>

        <div className="flex flex-col gap-4 sm:flex-row sm:items-start">
          <div className="w-full flex-none sm:w-[230px]">{p.photo}</div>
          <div className="flex min-w-0 flex-1 flex-col gap-3">
            <Field label={t('log.meal.name', 'Dish name')} value={p.name} onChange={p.onName} />
            {p.items.length > 0 && (
              <div className="flex flex-col gap-2">
                <p className="text-sub font-bold text-ink3">{t('log.meal.items', 'What we can see')}</p>
                <ul className="flex flex-col">
                  {p.items.map((item, i) => (
                    <li key={`${item}-${i}`} className="break-words border-t border-line py-2 text-body font-bold text-ink">
                      {item}
                    </li>
                  ))}
                </ul>
                <Segmented options={sizes} value={p.portion} onChange={p.onPortion} label={t('log.meal.sizeLabel', 'Size of the whole meal')} />
                <p className="text-micro text-ink3">{t('log.meal.wholeMealNote', 'Small, Regular and Large change the whole meal, not each item.')}</p>
              </div>
            )}
            {p.confidence === 'check' && <StatusPill tone="warn">{t('log.meal.checkPortion', 'Check this: we are less sure about the portion')}</StatusPill>}
            {p.flags.length > 0 && (
              <div className="flex flex-col gap-2">
                <div className="flex flex-wrap gap-2">
                  {p.flags.includes('high_salt') && (
                    <StatusPill tone="warn" icon={Warning}>
                      {t('log.meal.highSalt', 'High salt')}
                    </StatusPill>
                  )}
                  {p.flags.includes('high_sugar') && (
                    <StatusPill tone="warn" icon={Warning}>
                      {t('log.meal.highSugar', 'High sugar')}
                    </StatusPill>
                  )}
                </div>
                <p className="text-micro text-ink3">
                  {p.changed
                    ? t('log.meal.flagsBeforeChanges', 'These flags were worked out from the photo reading, before your changes.')
                    : t('log.meal.flagsNote', 'These flags are worked out from the numbers. They are notes, not advice.')}
                </p>
              </div>
            )}
          </div>
        </div>
      </Card>

      <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 md:gap-3 lg:grid-cols-6 xl:grid-cols-3">
        {totals.map((r) => (
          <MacroTile key={r.k} label={r.label} unit={r.unit} value={p.shown[r.k]} source={src(r.k)} flagged={flagged(r.k)} onChange={() => setEditing(r.k)} />
        ))}
      </div>

      <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-2 rounded-card border border-line bg-card px-4 py-3">
        <div className="min-w-0">
          <p className="text-sub font-bold text-ink">{fibre.label}</p>
          <p className="text-micro text-ink2">{sourceWord(p.shown.fibreG, src('fibreG'), t)}</p>
        </div>
        <div className="flex items-center gap-3">
          <p className="num whitespace-nowrap text-h2 font-bold text-ink">
            {p.shown.fibreG == null ? (
              <span className="text-sub font-bold text-ink2">{t('log.meal.notJudged', 'Not judged')}</span>
            ) : (
              <>
                {p.shown.fibreG.toLocaleString('en-US', { maximumFractionDigits: 1 })} <span className="text-micro font-normal text-ink2">g</span>
              </>
            )}
          </p>
          <button
            type="button"
            onClick={() => setEditing('fibreG')}
            className="press min-h-12 rounded-chip px-2 text-sub font-bold text-brand underline decoration-1 underline-offset-4"
          >
            {p.shown.fibreG == null ? t('log.meal.typeIn', 'Type it in') : t('log.meal.change', 'Change')}
          </button>
        </div>
      </div>

      {editRow && (
        <MacroEditor
          key={editRow.k}
          label={editRow.label}
          unit={editRow.unit}
          value={p.shown[editRow.k]}
          onSave={(v) => {
            p.onAmount(editRow.k, v)
            setEditing(null)
          }}
          onCancel={() => setEditing(null)}
        />
      )}

      <div className="flex flex-col gap-2">
        <p className="text-body font-bold text-ink">{t('log.meal.portion', 'Portion')}</p>
        <Stepper label={t('log.meal.portionLabel', 'portion')} value={p.portion} onChange={p.onPortion} min={0.5} max={3} step={0.5} format={fmtPortion} />
        <p className="text-sub text-ink2">{t('log.meal.portionHelp', 'Change the portion to scale every number above.')}</p>
      </div>

      {p.portionNote && <p className="text-sub text-ink2">{t('log.meal.assumed', 'What we assumed: {{note}}', { note: p.portionNote })}</p>}
      {anyNotJudged && (
        <p className="text-sub text-ink2">
          {t('log.meal.notJudgedNote', 'The photo was not clear enough to judge some numbers. Type them in if you know them.')}
        </p>
      )}
      <p className="text-sub text-ink3">{t('log.meal.estimates', 'Nutrients are estimates until you confirm them.')}</p>

      {p.note && (
        <Alert tone={p.note.kind === 'higher' ? 'warn' : 'info'} icon={Info} title={t('log.meal.usual', 'Your usual response')}>
          {p.note.text}
          {p.note.range && (
            <span className="mt-1 block text-ink2">
              {t('log.meal.seen', 'Seen {{n}} times, rise {{from}} to {{to}} mmol/L.', {
                n: p.note.n,
                from: p.note.range[0].toFixed(1),
                to: p.note.range[1].toFixed(1),
              })}
            </span>
          )}
        </Alert>
      )}
    </>
  )
}
