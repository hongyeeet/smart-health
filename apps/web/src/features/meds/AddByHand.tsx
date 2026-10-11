import { useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useAddMed } from '@/data/hooks'
import type { NewMedication } from '@/data/repositories/types'
import { href } from '@/app/routeIds'
import { useUi } from '@/state/store'
import { Footer, Header, Screen } from '@/ui/layout'
import { Segmented } from '@/ui/controls'
import { Alert, Button, Card, Chip, Field, Stepper, TextLink } from '@/ui/primitives'
import { Camera, Info, Plus, Trash } from '@/ui/icons'
import { useMedicineScope } from './useMedicineScope'

type Kind = NewMedication['kind']
type Meal = NewMedication['doses'][number]['mealRelation']
const MAX_TIMES = 6
const FIRST_TIMES = ['08:00', '13:00', '18:00', '21:00', '07:00', '22:00']

/** Local calendar date as YYYY-MM-DD (not UTC, so late evening in Singapore is still today). */
const today = () => new Date().toLocaleDateString('sv-SE')

const inputClass =
  'min-h-12 w-full rounded-field border-[1.5px] border-line bg-card px-3.5 py-2 text-body text-ink focus:border-brand focus:outline-none'

/**
 * H8 — Add a medicine by hand. The same save as the scan path; nothing is guessed and every value is the person's own. Every medicine
 * is saved as a daily one, with its times. It also opens from a scan that needs typing (H3 sends it here with the scan id and the
 * reason): the form is blank, says why, and saving completes that scan.
 */
export function AddByHand() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const fromScan = useLocation().state as { scanId?: string; notice?: string | null } | null
  const scanId = fromScan?.scanId
  const add = useAddMed()
  const toast = useUi((s) => s.showToast)

  const [name, setName] = useState('')
  const [kind, setKind] = useState<Kind>('prescription')
  const [strength, setStrength] = useState('')
  const [quantity, setQuantity] = useState(1)
  const [times, setTimes] = useState<string[]>(['08:00'])
  const [meal, setMeal] = useState<Meal>('na')
  const [total, setTotal] = useState('')
  const [startDate, setStartDate] = useState(today())
  const [directions, setDirections] = useState('')
  const outOfScope = useMedicineScope(name, kind)

  const kinds: { value: Kind; label: string }[] = [
    { value: 'prescription', label: t('addByHand.kind.prescription', 'Prescription') },
    { value: 'otc', label: t('addByHand.kind.otc', 'Over the counter') },
    { value: 'supplement', label: t('addByHand.kind.supplement', 'Supplement') },
    { value: 'tcm', label: t('addByHand.kind.tcm', 'Herbal') },
  ]
  const meals: { value: Meal; label: string }[] = [
    { value: 'before_meal', label: t('addByHand.meal.before', 'Before') },
    { value: 'after_meal', label: t('addByHand.meal.after', 'After') },
    { value: 'na', label: t('addByHand.meal.either', 'Either') },
  ]

  const totalNumber = /^\d{1,6}$/.test(total.trim()) ? Number(total.trim()) : 0
  const filled = times.filter(Boolean)
  const distinct = new Set(filled).size === filled.length

  // The first thing still missing, in the order the form is read. It is shown under the button, so a disabled button is never a mystery.
  const missing = !name.trim()
    ? t('addByHand.missing.name', 'Type the medicine name to continue.')
    : filled.length === 0 || filled.length !== times.length
      ? t('addByHand.missing.times', 'Choose a time for each dose, or remove the empty one.')
      : !distinct
        ? t('addByHand.missing.duplicate', 'Each time of day can only be listed once.')
        : totalNumber < 1
          ? t('addByHand.missing.total', 'Type the total you were given, for example 30.')
          : startDate > today()
            ? t('addByHand.missing.future', 'The start date cannot be in the future.')
            : null

  const save = () => {
    if (missing) return
    const body: NewMedication = {
      name: name.trim(),
      kind,
      strength: strength.trim(),
      doses: [...filled].sort().map((time) => ({ time, quantity, mealRelation: meal })),
      totalQuantity: totalNumber,
      startDate: startDate || null,
      directions: directions.trim(),
      ...(scanId ? { scanId } : {}),
    }
    add.mutate(body, {
      onSuccess: () => {
        toast(t('addByHand.added', 'Added to your medicines'))
        navigate(href('H1'), { replace: true })
      },
    })
  }

  const setTime = (i: number, v: string) => setTimes(times.map((x, j) => (j === i ? v : x)))
  const addTime = () => setTimes([...times, FIRST_TIMES.find((x) => !times.includes(x)) ?? ''])

  return (
    <Screen narrow>
      <Header title={t('addByHand.title', 'Add a medicine')} back backTo={scanId ? 'H2' : 'H1'} sub={t('addByHand.sub', 'Type in what is on your label. We never guess.')} />

      <Card tone="soft" className="flex items-start gap-3">
        <Info size={20} className="mt-0.5 flex-none text-ink3" aria-hidden />
        <p className="text-sub text-ink2">
          {t('addByHand.scope', 'Smart Health is for diabetes medicines and the medicines or supplements you take every day.')}
        </p>
      </Card>

      {scanId && (
        <Alert tone="info" title={t('addByHand.typeThisOne', 'Please type this one in')}>
          {fromScan?.notice ?? t('addByHand.couldNotRead', 'We could not read this label clearly enough.')}{' '}
          <TextLink onClick={() => navigate(href('H2'))}>{t('addByHand.retakePhoto', 'Retake the photo')}</TextLink>
        </Alert>
      )}

      <Field label={t('addByHand.name', 'Medicine name')} value={name} onChange={setName} placeholder={t('addByHand.namePlaceholder', 'As written on the label')} />

      {outOfScope && (
        <Alert tone="info" title={t('addByHand.scopeNoteTitle', 'Is this one for Smart Health?')}>
          {t('addByHand.scopeNote', 'We do not recognise this name yet, so please check it is right. You can still save it as printed on your label.')}
        </Alert>
      )}

      <div className="flex flex-col gap-1.5">
        <p id="kind-label" className="text-sub font-bold text-ink">
          {t('addByHand.whatKind', 'What kind is it?')}
        </p>
        <div role="group" aria-labelledby="kind-label" className="flex flex-wrap gap-2">
          {kinds.map((k) => (
            <Chip key={k.value} on={kind === k.value} onClick={() => setKind(k.value)}>
              {k.label}
            </Chip>
          ))}
        </div>
        {kind !== 'prescription' && (
          <p className="text-sub text-ink3">{t('addByHand.notChecked', 'Supplements and herbal products show as "Not checked" for interactions.')}</p>
        )}
      </div>

      <Field label={t('addByHand.strength', 'Strength (optional)')} value={strength} onChange={setStrength} placeholder={t('addByHand.strengthPlaceholder', 'For example, 500 mg')} />

      <div className="flex flex-col gap-1.5">
        <p className="text-sub font-bold text-ink">{t('addByHand.amount', 'Amount each time')}</p>
        <Stepper
          label={t('addByHand.amountLabel', 'amount each time')}
          value={quantity}
          onChange={setQuantity}
          min={0.5}
          max={20}
          step={0.5}
          format={(v) => (Number.isInteger(v) ? String(v) : v.toFixed(1))}
        />
        <p className="text-sub text-ink3">{t('addByHand.amountHint', 'Number of tablets, capsules or measures.')}</p>
      </div>

      <div className="flex flex-col gap-2">
        <p className="text-sub font-bold text-ink">{t('addByHand.timesEachDay', 'Times each day')}</p>
        <ul className="flex flex-col gap-2">
          {times.map((tm, i) => (
            <li key={i} className="flex items-center gap-2">
              <input
                type="time"
                aria-label={t('addByHand.doseTime', 'Dose time {{n}}', { n: i + 1 })}
                value={tm}
                onChange={(e) => setTime(i, e.target.value)}
                className={inputClass}
              />
              {times.length > 1 && (
                <button
                  type="button"
                  aria-label={t('addByHand.removeTime', 'Remove dose time {{n}}', { n: i + 1 })}
                  onClick={() => setTimes(times.filter((_, j) => j !== i))}
                  className="press flex h-12 w-12 flex-none items-center justify-center rounded-full bg-well text-ink2"
                >
                  <Trash size={20} aria-hidden />
                </button>
              )}
            </li>
          ))}
        </ul>
        {times.length < MAX_TIMES && (
          <TextLink icon={Plus} onClick={addTime} className="self-start">
            {t('addByHand.addAnother', 'Add another time')}
          </TextLink>
        )}
      </div>

      <div className="flex flex-col gap-1.5">
        <p className="text-sub font-bold text-ink">{t('addByHand.beforeAfter', 'Before or after food?')}</p>
        <Segmented label={t('addByHand.beforeAfter', 'Before or after food?')} options={meals} value={meal} onChange={setMeal} />
      </div>

      <Field
        label={t('addByHand.total', 'Total you were given')}
        value={total}
        onChange={(v) => setTotal(v.replace(/[^\d]/g, ''))}
        inputMode="numeric"
        placeholder={t('addByHand.totalPlaceholder', 'For example, 30')}
        hint={t('addByHand.totalHint', 'Tablets, capsules or units in the pack, as printed on the label. We use it to tell you when you may run out.')}
      />

      <div className="flex flex-col gap-1.5">
        <label htmlFor="start-date" className="text-sub font-bold text-ink">
          {t('addByHand.startedOn', 'Started on')}
        </label>
        <input id="start-date" type="date" max={today()} value={startDate} onChange={(e) => setStartDate(e.target.value)} className={inputClass} />
      </div>

      <Field
        label={t('addByHand.directions', 'Directions on the label (optional)')}
        value={directions}
        onChange={setDirections}
        multiline
        placeholder={t('addByHand.directionsPlaceholder', 'For example, take 1 tablet twice a day after meals')}
      />

      <Alert tone="info">{t('addByHand.asTyped', 'We save exactly what you type. Checking it against your other medicines is not part of this step yet.')}</Alert>

      {add.isError && (
        <Alert tone="danger" title={t('addByHand.couldNotSave', 'Could not save')}>
          {/* The server explains a refusal in plain words ("This scan was already saved..."); a bare status such as "500 Internal Server Error" is not shown. */}
          {add.error instanceof TypeError
            ? t('addByHand.offline', 'We could not reach Smart Health. Check your connection and try again. Nothing has been saved.')
            : add.error instanceof Error && add.error.message && !/^\d{3}/.test(add.error.message)
              ? add.error.message
              : t('addByHand.saveFailed', 'We could not save this medicine. Check the details and try again.')}
        </Alert>
      )}

      <Footer>
        <Button disabled={!!missing || add.isPending} onClick={save}>
          {add.isPending ? t('addByHand.saving', 'Saving…') : t('addByHand.save', 'Save medicine')}
        </Button>
        {missing && (
          <p role="status" className="text-center text-sub text-ink2">
            {missing}
          </p>
        )}
      </Footer>

      <TextLink icon={Camera} onClick={() => navigate(href('H2'))} className="self-center">
        {t('addByHand.scanInstead', 'Scan a label instead')}
      </TextLink>
    </Screen>
  )
}
