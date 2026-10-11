import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Footer } from '@/ui/layout'
import { Button, Card, Field, TextLink } from '@/ui/primitives'
import { Clock, CheckCircle, PencilSimple } from '@/ui/icons'
import type { Macros } from '@/data/types'
import { parseAmount } from './mealMath'
import type { MealDraft } from './mealDraft'

interface Props {
  /** back to the photo step, when there is a photo to go back to */
  onBack?: () => void
  onStart: (d: MealDraft) => void
  onFinish: (d: MealDraft) => void
}

/**
 * Enter the meal by hand. Used when the photo cannot be read, or when the person prefers to type. Saves the same way a
 * photo reading does. A blank number means "not known" (saved as null, never 0).
 */
export function MealManualForm({ onBack, onStart, onFinish }: Props) {
  const { t } = useTranslation()
  const [name, setName] = useState('')
  const [kcal, setKcal] = useState('')
  const [carbs, setCarbs] = useState('')
  const [protein, setProtein] = useState('')
  const [fat, setFat] = useState('')
  const [salt, setSalt] = useState('')
  const [submitted, setSubmitted] = useState(false)

  const parsed = {
    kcal: parseAmount(kcal),
    carbsG: parseAmount(carbs),
    proteinG: parseAmount(protein),
    fatG: parseAmount(fat),
    sodiumMg: parseAmount(salt),
  }
  const nameMissing = submitted && name.trim() === ''
  const numberMissing = (k: keyof typeof parsed) => submitted && !parsed[k].ok
  const numberError = t('log.meal.numberError', 'Please type a number, 0 or more. Leave it blank if you do not know.')

  /** The draft when everything is valid, or null (and the errors show). */
  const build = (): MealDraft | null => {
    setSubmitted(true)
    const ok = name.trim() !== '' && Object.values(parsed).every((p) => p.ok)
    if (!ok) return null
    const v = (k: keyof typeof parsed) => {
      const p = parsed[k]
      return p.ok ? p.value : null
    }
    const macros: Macros = { kcal: v('kcal'), carbsG: v('carbsG'), proteinG: v('proteinG'), fatG: v('fatG'), sugarG: null, fibreG: null, sodiumMg: v('sodiumMg') }
    return { name: name.trim(), description: '', portion: 1, macros, analysis: null, edited: true, valuesFrom: 'user' }
  }

  const amount = (label: string, k: keyof typeof parsed, value: string, set: (v: string) => void, unit: string) => (
    <Field label={label} suffix={unit} inputMode="decimal" value={value} onChange={set} hint={t('log.meal.leaveBlank', 'Leave blank if you do not know.')} error={numberMissing(k) ? numberError : undefined} />
  )

  return (
    <>
      <Card className="flex flex-col gap-4">
        <div className="flex items-start gap-3">
          <span className="flex h-11 w-11 flex-none items-center justify-center rounded-full bg-brand-soft text-brand">
            <PencilSimple size={22} aria-hidden />
          </span>
          <p className="text-sub text-ink2">{t('log.meal.byHandIntro', 'Type what you ate. The numbers are your own, so they are not marked as estimates.')}</p>
        </div>
        <Field label={t('log.meal.nameMeal', 'What did you eat?')} value={name} onChange={setName} placeholder={t('log.meal.nameMealPh', 'For example: Chicken rice')} error={nameMissing ? t('log.meal.nameRequired', 'Please type what you ate.') : undefined} />
        <div className="grid gap-4 md:grid-cols-2">
          {amount(t('log.meal.caloriesKcal', 'Calories (kcal)'), 'kcal', kcal, setKcal, 'kcal')}
          {amount(t('log.meal.carbsG', 'Carbohydrate (g)'), 'carbsG', carbs, setCarbs, 'g')}
          {amount(t('log.meal.proteinG', 'Protein (g)'), 'proteinG', protein, setProtein, 'g')}
          {amount(t('log.meal.fatG', 'Fat (g)'), 'fatG', fat, setFat, 'g')}
          {amount(t('log.meal.saltMg', 'Salt (sodium, mg)'), 'sodiumMg', salt, setSalt, 'mg')}
        </div>
        {onBack && (
          <TextLink onClick={onBack} className="self-start">
            {t('log.meal.backToPhoto', 'Back to the photo')}
          </TextLink>
        )}
      </Card>
      <Footer>
        <Button icon={Clock} onClick={() => {
          const d = build()
          if (d) onStart(d)
        }}>
          {t('log.meal.startEating', 'Start eating')}
        </Button>
        <Button variant="secondary" icon={CheckCircle} onClick={() => {
          const d = build()
          if (d) onFinish(d)
        }}>
          {t('log.meal.alreadyAte', 'I already finished eating')}
        </Button>
      </Footer>
    </>
  )
}
