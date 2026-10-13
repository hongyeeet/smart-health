/**
 * The details shown at the top of Data and account, and how each one is edited.
 *
 * Each entry is one answer from the set-up questions: its label, how it reads on the list, the starting value for the pop-up, the
 * editor, the check on what was typed and the part of the saved profile it writes (PUT /onboarding/profile writes only the keys it is
 * given). The list is data, so a question can be dropped or added here without touching the screen: Joely is deciding which set-up
 * questions stay, and what stays is edited from here.
 */
import type { ReactNode } from 'react'
import i18n from '@/i18n'
import { Button, Field } from '@/ui/primitives'
import { fmtDate } from '../settings/rules'
import { PickMany, PickOne, type Option } from '@/features/onboarding/parts'
import { RACE_OTHERS, labelOf } from '@/features/onboarding/options'
import { LIMITS, inRange, num, pastDateOk, yearOk, type OnboardingAnswers } from '@/features/onboarding/useOnboarding'
import type { ProfileBody, SavedOnboarding } from '@/features/onboarding/api'
import { Plus } from '@/ui/icons'

export type Group = 'about' | 'care' | 'health' | 'results' | 'devices' | 'work'

type Opts = ReturnType<typeof import('@/features/onboarding/options').useOptions>

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export interface FieldDef<D = any> {
  id: string
  group: Group
  label: string
  /** how the answer reads on the list; null shows "Not set" */
  show: (a: OnboardingAnswers, saved: SavedOnboarding) => string | null
  init: (a: OnboardingAnswers, saved: SavedOnboarding) => D
  body: (d: D) => ProfileBody
  problem?: (d: D) => string | undefined
  editor: (d: D, set: (d: D) => void) => ReactNode
}

const t = (key: string, en: string, vars?: Record<string, unknown>) => i18n.t(key, en, vars) as string

const trimmed = (v: string) => v.trim() || null
const whole = (v: string) => {
  const n = num(v)
  return n === null ? null : Math.trunc(n)
}

/* ------------------------------------------------------------------ builders */
function text(id: string, group: Group, label: string, key: 'name' | 'race' | 'otherConditions', toBody: (v: string | null) => ProfileBody, o: { required?: boolean; noDigits?: boolean; multiline?: boolean; placeholder?: string } = {}): FieldDef<string> {
  return {
    id, group, label,
    show: (a) => a[key].trim() || null,
    init: (a) => a[key],
    body: (d) => toBody(trimmed(d)),
    problem: (d) =>
      o.required && !d.trim()
        ? t('me.account.needValue', 'This cannot be empty.')
        : o.noDigits && /\d/.test(d)
          ? t('me.account.nameDigits', 'Enter a name you would like us to call you, without numbers (an ID number is not a name).')
          : undefined,
    editor: (d, set) => <Field label={label} value={d} onChange={set} multiline={o.multiline} placeholder={o.placeholder} />,
  }
}

function numeric(id: string, group: Group, label: string, key: 'heightCm' | 'weightKg' | 'waistCm' | 'fastingInsulin', range: readonly [number, number], suffix: string, toBody: (v: number | null) => ProfileBody): FieldDef<string> {
  return {
    id, group, label,
    show: (a) => (a[key].trim() ? `${a[key]} ${suffix}` : null),
    init: (a) => a[key],
    body: (d) => toBody(num(d)),
    problem: (d) => (inRange(d, range) ? undefined : t('me.account.range', 'Enter a number from {{lo}} to {{hi}}.', { lo: range[0], hi: range[1] })),
    editor: (d, set) => <Field label={label} value={d} onChange={set} inputMode="decimal" suffix={suffix} hint={t('me.account.leaveEmpty', 'Leave it empty to clear it.')} />,
  }
}

function year(id: string, group: Group, label: string, key: 'birthYear' | 'diagnosedYear', required: boolean, toBody: (v: number | null) => ProfileBody): FieldDef<string> {
  return {
    id, group, label,
    show: (a) => a[key].trim() || null,
    init: (a) => a[key],
    body: (d) => toBody(whole(d)),
    problem: (d) => (yearOk(d, { required }) ? undefined : t('me.account.year', 'Enter a four-digit year, such as 1962.')),
    editor: (d, set) => <Field label={label} value={d} onChange={set} inputMode="numeric" placeholder="1962" />,
  }
}

function pick<T extends string>(id: string, group: Group, label: string, get: (a: OnboardingAnswers) => T | null, options: Option<T>[], toBody: (v: T | null) => ProfileBody): FieldDef<T | null> {
  return {
    id, group, label,
    show: (a) => {
      const v = get(a)
      return v === null ? null : labelOf(options, v)
    },
    init: (a) => get(a),
    body: (d) => toBody(d),
    editor: (d, set) => <PickOne label={label} options={options} value={d} onChange={set} stack />,
  }
}

/* ------------------------------------------------------------------ the list */
export function buildFields(o: Opts): FieldDef[] {
  const f: FieldDef<any>[] = [
    text('name', 'about', t('me.account.f.name', 'Name'), 'name', (v) => ({ displayName: v ?? undefined }), { required: true, noDigits: true }),
    year('birthYear', 'about', t('me.account.f.birthYear', 'Year of birth'), 'birthYear', true, (v) => ({ birthYear: v ?? undefined })),
    pick('gender', 'about', t('me.account.f.gender', 'Sex'), (a) => a.gender, o.gender, (v) => ({ gender: v })),
    {
      id: 'race', group: 'about', label: t('me.account.f.race', 'Ethnic group'),
      show: (a: OnboardingAnswers) => (a.race.trim() ? labelOf(o.race, a.race.trim()) : null),
      /* Chinese, Malay or Indian are picked; Others shows a box to say which (that word is what is saved). Any other saved word opens as Others. */
      init: (a: OnboardingAnswers) => {
        const known = o.race.some((x) => x.value !== RACE_OTHERS && x.value === a.race)
        return { pick: known ? a.race : a.race.trim() ? RACE_OTHERS : null, other: known ? '' : a.race }
      },
      body: (d: { pick: string | null; other: string }) => ({ race: d.pick === RACE_OTHERS ? trimmed(d.other) : d.pick }),
      problem: (d: { pick: string | null; other: string }) => (d.pick === RACE_OTHERS && !d.other.trim() ? t('me.account.sayWhich', 'Please say which.') : undefined),
      editor: (d: { pick: string | null; other: string }, set: (d: { pick: string | null; other: string }) => void) => (
        <div className="flex flex-col gap-3">
          <PickOne label={t('me.account.f.race', 'Ethnic group')} options={o.race} value={d.pick} onChange={(pick) => set({ pick, other: pick === RACE_OTHERS ? d.other : '' })} />
          {d.pick === RACE_OTHERS && <Field label={t('onboarding.race.otherV2', 'Please say which')} value={d.other} onChange={(other) => set({ ...d, other })} />}
        </div>
      ),
    },
    numeric('heightCm', 'about', t('me.account.f.height', 'Height'), 'heightCm', LIMITS.heightCm, 'cm', (v) => ({ heightCm: v })),
    numeric('weightKg', 'about', t('me.account.f.weight', 'Weight'), 'weightKg', LIMITS.weightKg, 'kg', (v) => ({ weightKg: v })),
    numeric('waistCm', 'about', t('me.account.f.waist', 'Waist'), 'waistCm', LIMITS.waistCm, 'cm', (v) => ({ waistCm: v })),

    year('diagnosedYear', 'care', t('me.account.f.diagnosed', 'Year diagnosed with diabetes'), 'diagnosedYear', false, (v) => ({ diagnosedYear: v })),
    pick('careSetting', 'care', t('me.account.f.care', 'Where you get your diabetes care'), (a) => a.careSetting, o.careSetting, (v) => ({ careSetting: v })),
    pick('healthierSg', 'care', t('me.account.f.hsg', 'Healthier SG'), (a) => a.healthierSg, o.healthierSg, (v) => ({ healthierSg: v })),
    pick('hypo3m', 'care', t('me.account.f.hypo3m', 'Low glucose in the last 3 months'), (a) => a.hypo3m, o.hypo3m, (v) => ({ hypoLast3m: v })),
    pick('severeHypo', 'care', t('me.account.f.severeHypo', 'Needed someone to help with a low'), (a) => a.severeHypo, o.yesNo, (v) => ({ hypoNeededHelp: v })),

    {
      id: 'conditions', group: 'health', label: t('me.account.f.conditions', 'Other conditions'),
      show: (a, s) => (a.conditions.length ? a.conditions.map((c) => labelOf(o.conditions, c)).join(', ') : s.profile ? t('me.account.noneRecorded', 'None recorded') : null),
      init: (a) => a.conditions,
      body: (d: string[]) => ({ conditions: d.filter((c) => c !== 'none') }),
      editor: (d: string[], set: (d: string[]) => void) => <PickMany label={t('me.account.f.conditions', 'Other conditions')} options={o.conditions} value={d} onChange={set} none="none" stack />,
    },
    text('otherConditions', 'health', t('me.account.f.otherConditions', 'Anything else, in your words'), 'otherConditions', (v) => ({ otherCondition: v }), { multiline: true }),
    {
      id: 'allergies', group: 'health', label: t('me.account.f.allergies', 'Allergies'),
      show: (a, s) => (a.allergies.length ? a.allergies.map((x) => x.substance).join(', ') : s.profile ? t('me.account.noneRecorded', 'None recorded') : null),
      init: (a) => (a.allergies.length ? a.allergies.map((x) => ({ ...x })) : [{ substance: '', reaction: '' }]),
      body: (d: { substance: string; reaction: string }[]) => ({ allergies: d.filter((x) => x.substance.trim()).map((x) => ({ substance: x.substance.trim(), reaction: trimmed(x.reaction) })) }),
      editor: (d: { substance: string; reaction: string }[], set: (d: { substance: string; reaction: string }[]) => void) => (
        <div className="flex flex-col gap-3">
          {d.map((row, i) => (
            <div key={i} className="grid gap-3 sm:grid-cols-2 [&>*]:min-w-0">
              <Field label={t('me.account.f.allergen', 'Allergic to')} value={row.substance} onChange={(v) => set(d.map((r, j) => (j === i ? { ...r, substance: v } : r)))} />
              <Field label={t('me.account.f.reaction', 'What happens (optional)')} value={row.reaction} onChange={(v) => set(d.map((r, j) => (j === i ? { ...r, reaction: v } : r)))} />
            </div>
          ))}
          <Button variant="ghost" size="md" icon={Plus} className="!w-auto self-start" onClick={() => set([...d, { substance: '', reaction: '' }])}>
            {t('me.account.f.addAllergy', 'Add another')}
          </Button>
          <p className="text-sub text-ink3">{t('me.account.f.allergyClear', 'Clear every box to say you have no known allergies.')}</p>
        </div>
      ),
    },
    pick('eyeCheck', 'health', t('me.account.f.eye', 'Last eye check'), (a) => a.eyeCheck, o.lastCheck, (v) => ({ eyeCheck: v })),
    pick('footCheck', 'health', t('me.account.f.foot', 'Last foot check'), (a) => a.footCheck, o.lastCheck, (v) => ({ footCheck: v })),

    {
      id: 'labDate', group: 'results', label: t('me.account.f.labDate', 'Date of your latest results'),
      show: (a) => (a.labDate ? fmtDate(a.labDate) : null),
      init: (a) => a.labDate,
      body: (d: string) => ({ labDate: d || null }),
      problem: (d: string) => (pastDateOk(d) ? undefined : t('me.account.notFuture', 'The date cannot be in the future.')),
      editor: (d: string, set: (d: string) => void) => <Field label={t('me.account.f.labDate', 'Date of your latest results')} type="date" value={d} onChange={set} />,
    },
    {
      id: 'hba1c', group: 'results', label: t('me.account.f.hba1c', 'HbA1c'),
      show: (_a, s) => (s.history.hba1c != null ? `${Number(s.history.hba1c)} %` : null),
      init: (_a, s) => (s.history.hba1c != null ? String(Number(s.history.hba1c)) : ''),
      body: (d: string) => ({ hba1c: num(d), ...(num(d) !== null ? { hba1cUnit: '%' } : {}) }),
      problem: (d: string) => (inRange(d, LIMITS.hba1cPct) ? undefined : t('me.account.range', 'Enter a number from {{lo}} to {{hi}}.', { lo: LIMITS.hba1cPct[0], hi: LIMITS.hba1cPct[1] })),
      editor: (d: string, set: (d: string) => void) => <Field label={t('me.account.f.hba1c', 'HbA1c')} value={d} onChange={set} inputMode="decimal" suffix="%" hint={t('me.account.leaveEmpty', 'Leave it empty to clear it.')} />,
    },
    {
      id: 'fastingGlucose', group: 'results', label: t('me.account.f.fasting', 'Fasting glucose'),
      show: (_a, s) => (s.history.fastingGlucose != null ? `${Number(s.history.fastingGlucose)} ${s.history.glucoseUnit ?? 'mmol/L'}` : null),
      init: (_a, s) => ({ value: s.history.fastingGlucose != null ? String(Number(s.history.fastingGlucose)) : '', unit: s.history.glucoseUnit ?? 'mmol/L' }),
      body: (d: { value: string; unit: string }) => ({ fastingGlucose: num(d.value), ...(num(d.value) !== null ? { glucoseUnit: d.unit } : {}) }),
      problem: (d: { value: string; unit: string }) => {
        const r = d.unit === 'mg/dL' ? LIMITS.glucoseMgDl : LIMITS.glucoseMmol
        return inRange(d.value, r) ? undefined : t('me.account.range', 'Enter a number from {{lo}} to {{hi}}.', { lo: r[0], hi: r[1] })
      },
      editor: (d: { value: string; unit: string }, set: (d: { value: string; unit: string }) => void) => (
        <Field label={t('me.account.f.fasting', 'Fasting glucose')} value={d.value} onChange={(v) => set({ ...d, value: v })} inputMode="decimal" suffix={d.unit} hint={t('me.account.leaveEmpty', 'Leave it empty to clear it.')} />
      ),
    },
    numeric('fastingInsulin', 'results', t('me.account.f.insulin', 'Fasting insulin'), 'fastingInsulin', LIMITS.fastingInsulin, 'mIU/L', (v) => ({ fastingInsulin: v })),

    pick('wearable', 'devices', t('me.account.f.watch', 'Watch'), (a) => a.wearable, o.wearable, (v) => ({ watchModel: v })),
    pick('cgm', 'devices', t('me.account.f.cgm', 'Glucose sensor'), (a) => a.cgm, o.cgm, (v) => ({ cgmModel: v })),

    pick('workType', 'work', t('me.account.f.work', 'Your work'), (a) => a.workType, o.work, (v) => (v === 'not_working' ? { workType: v, workDays: [], workStart: null, workEnd: null } : { workType: v })),
    {
      id: 'workDays', group: 'work', label: t('me.account.f.workDays', 'Days you work'),
      show: (a) => (a.workDays.length ? a.workDays.map((d) => labelOf(o.weekdays, String(d))).join(', ') : null),
      init: (a) => a.workDays.map(String),
      body: (d: string[]) => ({ workDays: d.map(Number).sort() }),
      editor: (d: string[], set: (d: string[]) => void) => <PickMany label={t('me.account.f.workDays', 'Days you work')} options={o.weekdays} value={d} onChange={set} />,
    },
    {
      id: 'workHours', group: 'work', label: t('me.account.f.workHours', 'Working hours'),
      show: (a) => (a.workStart && a.workEnd ? `${a.workStart} – ${a.workEnd}` : null),
      init: (a) => ({ start: a.workStart, end: a.workEnd }),
      body: (d: { start: string; end: string }) => ({ workStart: trimmed(d.start), workEnd: trimmed(d.end) }),
      problem: (d: { start: string; end: string }) => (!!d.start !== !!d.end ? t('me.account.bothTimes', 'Add both times, or leave both empty.') : undefined),
      editor: (d: { start: string; end: string }, set: (d: { start: string; end: string }) => void) => (
        <div className="grid gap-3 sm:grid-cols-2 [&>*]:min-w-0">
          <Field label={t('me.account.f.from', 'From')} type="time" value={d.start} onChange={(v) => set({ ...d, start: v })} />
          <Field label={t('me.account.f.to', 'To')} type="time" value={d.end} onChange={(v) => set({ ...d, end: v })} />
        </div>
      ),
    },
  ]
  return f
}

export function groupTitle(g: Group): string {
  return {
    about: t('me.account.g.about', 'About you'),
    care: t('me.account.g.care', 'Diabetes and care'),
    health: t('me.account.g.health', 'Health history'),
    results: t('me.account.g.results', 'Latest results'),
    devices: t('me.account.g.devices', 'Devices'),
    work: t('me.account.g.work', 'Work'),
  }[g]
}
