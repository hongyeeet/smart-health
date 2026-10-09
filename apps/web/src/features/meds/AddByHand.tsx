import { useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { useAddMed } from '@/data/hooks'
import type { NewMedication } from '@/data/repositories/types'
import { href } from '@/app/routeIds'
import { useUi } from '@/state/store'
import { Footer, Header, Screen } from '@/ui/layout'
import { Segmented } from '@/ui/controls'
import { Alert, Button, Chip, Field, Stepper, TextLink, Toggle } from '@/ui/primitives'
import { Camera, Plus, Trash } from '@/ui/icons'

type Kind = NewMedication['kind']
type Meal = NewMedication['doses'][number]['mealRelation']

const KINDS: { value: Kind; label: string }[] = [
  { value: 'prescription', label: 'Prescription' },
  { value: 'otc', label: 'Over the counter' },
  { value: 'supplement', label: 'Supplement' },
  { value: 'tcm', label: 'Herbal' },
]
const MEALS: { value: Meal; label: string }[] = [
  { value: 'before_meal', label: 'Before' },
  { value: 'after_meal', label: 'After' },
  { value: 'na', label: 'Either' },
]
const MAX_TIMES = 6
const FIRST_TIMES = ['08:00', '13:00', '18:00', '21:00', '07:00', '22:00']

/** Local calendar date as YYYY-MM-DD (not UTC, so late evening in Singapore is still today). */
const today = () => new Date().toLocaleDateString('sv-SE')

const inputClass =
  'min-h-12 w-full rounded-field border-[1.5px] border-line bg-card px-3.5 py-2 text-body text-ink focus:border-brand focus:outline-none'

/**
 * H8 — Add a medicine by hand. The same save as the scan path; nothing is guessed and every value is the person's own.
 * It also opens from a scan that needs typing (H3 sends it here with the scan id and the reason): the form is blank, says why, and
 * saving completes that scan.
 */
export function AddByHand() {
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
  const [asNeeded, setAsNeeded] = useState(false)
  const [meal, setMeal] = useState<Meal>('na')
  const [total, setTotal] = useState('')
  const [startDate, setStartDate] = useState(today())
  const [directions, setDirections] = useState('')

  const totalNumber = /^\d{1,6}$/.test(total.trim()) ? Number(total.trim()) : 0
  const filled = times.filter(Boolean)
  const distinct = new Set(filled).size === filled.length

  // The first thing still missing, in the order the form is read. It is shown under the button, so a disabled button is never a mystery.
  const missing = !name.trim()
    ? 'Type the medicine name to continue.'
    : !asNeeded && (filled.length === 0 || filled.length !== times.length)
      ? 'Choose a time for each dose, or remove the empty one.'
      : !asNeeded && !distinct
        ? 'Each time of day can only be listed once.'
        : totalNumber < 1
          ? 'Type the total you were given, for example 30.'
          : startDate > today()
            ? 'The start date cannot be in the future.'
            : null

  const save = () => {
    if (missing) return
    const body: NewMedication = {
      name: name.trim(),
      kind,
      strength: strength.trim(),
      // Taken only when needed: one dose with no clock time, so no reminder and no missed dose.
      doses: asNeeded ? [{ time: null, quantity, mealRelation: meal }] : [...filled].sort().map((time) => ({ time, quantity, mealRelation: meal })),
      totalQuantity: totalNumber,
      startDate: startDate || null,
      directions: directions.trim(),
      ...(scanId ? { scanId } : {}),
    }
    add.mutate(body, {
      onSuccess: () => {
        toast('Added to your medicines')
        navigate(href('H1'), { replace: true })
      },
    })
  }

  const setTime = (i: number, v: string) => setTimes(times.map((t, j) => (j === i ? v : t)))
  const addTime = () => setTimes([...times, FIRST_TIMES.find((t) => !times.includes(t)) ?? ''])

  return (
    <Screen>
      <Header title="Add a medicine" back backTo={scanId ? 'H2' : 'H1'} sub="Type in what is on your label. We never guess." />

      {scanId && (
        <Alert tone="info" title="Please type this one in">
          {fromScan?.notice ?? 'We could not read this label clearly enough.'}{' '}
          <TextLink onClick={() => navigate(href('H2'))}>Retake the photo</TextLink>
        </Alert>
      )}

      <Field label="Medicine name" value={name} onChange={setName} placeholder="As written on the label" />

      <div className="flex flex-col gap-1.5">
        <p id="kind-label" className="text-sub font-bold text-ink">
          What kind is it?
        </p>
        <div role="group" aria-labelledby="kind-label" className="flex flex-wrap gap-2">
          {KINDS.map((k) => (
            <Chip key={k.value} on={kind === k.value} onClick={() => setKind(k.value)}>
              {k.label}
            </Chip>
          ))}
        </div>
        {kind !== 'prescription' && <p className="text-sub text-ink3">Supplements and herbal products show as "Not checked" for interactions.</p>}
      </div>

      <Field label="Strength (optional)" value={strength} onChange={setStrength} placeholder="For example, 500 mg" />

      <div className="flex flex-col gap-1.5">
        <p className="text-sub font-bold text-ink">Amount each time</p>
        <Stepper
          label="amount each time"
          value={quantity}
          onChange={setQuantity}
          min={0.5}
          max={20}
          step={0.5}
          format={(v) => (Number.isInteger(v) ? String(v) : v.toFixed(1))}
        />
        <p className="text-sub text-ink3">Number of tablets, capsules or measures.</p>
      </div>

      <div className="flex items-center justify-between gap-4 rounded-card border border-line bg-card p-3.5">
        <div className="min-w-0">
          <p className="text-body font-bold">Only when needed</p>
          <p className="text-sub text-ink3">No set times, no reminders. For medicines you take when you need them.</p>
        </div>
        <Toggle on={asNeeded} onChange={setAsNeeded} label="Only when needed" />
      </div>

      {!asNeeded && (
        <div className="flex flex-col gap-2">
          <p className="text-sub font-bold text-ink">Times each day</p>
          <ul className="flex flex-col gap-2">
            {times.map((t, i) => (
              <li key={i} className="flex items-center gap-2">
                <input
                  type="time"
                  aria-label={`Dose time ${i + 1}`}
                  value={t}
                  onChange={(e) => setTime(i, e.target.value)}
                  className={inputClass}
                />
                {times.length > 1 && (
                  <button
                    type="button"
                    aria-label={`Remove dose time ${i + 1}`}
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
            Add another time
          </TextLink>
        )}
      </div>
      )}

      <div className="flex flex-col gap-1.5">
        <p className="text-sub font-bold text-ink">Before or after food?</p>
        <Segmented label="Before or after food" options={MEALS} value={meal} onChange={setMeal} />
      </div>

      <Field
        label="Total you were given"
        value={total}
        onChange={(v) => setTotal(v.replace(/[^\d]/g, ''))}
        inputMode="numeric"
        placeholder="For example, 30"
        hint="Tablets, capsules or units in the pack, as printed on the label. We use it to tell you when you may run out."
      />

      <div className="flex flex-col gap-1.5">
        <label htmlFor="start-date" className="text-sub font-bold text-ink">
          Started on
        </label>
        <input id="start-date" type="date" max={today()} value={startDate} onChange={(e) => setStartDate(e.target.value)} className={inputClass} />
      </div>

      <Field label="Directions on the label (optional)" value={directions} onChange={setDirections} multiline placeholder="For example, take 1 tablet twice a day after meals" />

      <Alert tone="info">We save exactly what you type. Checking it against your other medicines is not part of this step yet.</Alert>

      {add.isError && (
        <Alert tone="danger" title="Could not save">
          {/* The server explains a refusal in plain words ("This scan was already saved..."); a bare status such as "500 Internal Server Error" is not shown. */}
          {add.error instanceof Error && add.error.message && !/^\d{3}/.test(add.error.message)
            ? add.error.message
            : 'We could not save this medicine. Check the details and try again.'}
        </Alert>
      )}

      <Footer>
        <Button disabled={!!missing || add.isPending} onClick={save}>
          {add.isPending ? 'Saving…' : 'Save medicine'}
        </Button>
        {missing && (
          <p role="status" className="text-center text-sub text-ink2">
            {missing}
          </p>
        )}
      </Footer>

      <TextLink icon={Camera} onClick={() => navigate(href('H2'))} className="self-center">
        Scan a label instead
      </TextLink>
    </Screen>
  )
}
