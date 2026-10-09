/**
 * A6 — Your profile summary. An editable read-back of what the person entered.
 *
 * Damien's Stitch design ends on a "clinical target profile" with stages, risk tiers and personal targets. Those are left
 * out: Smart Health does not classify the person or set targets (rules.md 1.1, 1.6, 1.15). What is kept is the read-back,
 * the plain arithmetic (age, BMI, unit conversions, with no category attached), a short list of gaps worth raising with
 * the doctor, and the safety messages.
 */
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { href } from '@/app/routeIds'
import { useBack } from '@/app/navigation'
import { useUi } from '@/state/store'
import { appConfig } from '@/config/app'
import { Screen } from '@/ui/layout'
import { Alert, Card, TextLink } from '@/ui/primitives'
import { PencilSimple } from '@/ui/icons'
import { Dock, TopBar, clock } from './parts'
import { labelOf, useOptions } from './options'
import { SafetyAlerts } from './SafetyAlerts'
import { ABOUT_STEPS } from './AboutYou'
import { convert, num, useOnboarding } from './useOnboarding'

interface Row {
  label: string
  value: string
}

export function Summary() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const back = useBack('A3')
  const locale = useUi((s) => s.locale)
  const toast = useUi((s) => s.showToast)
  const a = useOnboarding((s) => s.answers)
  const set = useOnboarding((s) => s.set)
  const reset = useOnboarding((s) => s.reset)
  const o = useOptions()

  const on = t('onboarding.sum.on', 'On')
  const off = t('onboarding.sum.off', 'Off')
  const unit = (v: string, u: string) => (v.trim() ? `${v.trim()} ${u}` : '')
  const list = (xs: string[]) => xs.filter(Boolean).join(', ')
  const many = <T extends string>(options: { value: T; label: string }[], values: T[]) => list(values.map((v) => labelOf(options, v)))
  const step = (n: number) => `${href('A3')}?step=${n}&review=1`
  const date = (iso: string) => (iso ? new Date(`${iso}T00:00:00`).toLocaleDateString('en-SG', { day: 'numeric', month: 'short', year: 'numeric' }) : '')

  const sections: { title: string; edit: string; rows: Row[] }[] = [
    {
      title: t('onboarding.welcome.step', 'Welcome'),
      edit: `${href('A1')}?review=1`,
      rows: [
        { label: t('onboarding.sum.name', 'Name'), value: a.name.trim() },
        { label: t('onboarding.language', 'Language'), value: appConfig.locales.find((l) => l.code === locale)?.native ?? locale },
        { label: t('onboarding.consent.data', 'Use my health data'), value: a.consentData ? on : off },
        { label: t('onboarding.consent.share', 'Share a doctor brief'), value: a.consentShare ? on : off },
        { label: t('onboarding.consent.research', 'Use my data for research'), value: a.consentResearch ? on : off },
      ],
    },
    {
      title: t('onboarding.s1.name', 'Body measurements'),
      edit: step(1),
      rows: [
        { label: t('onboarding.birthYear', 'Year of birth'), value: a.birthYear.trim() },
        { label: t('onboarding.gender.label', 'Gender'), value: labelOf(o.gender, a.gender) },
        { label: t('onboarding.race.label', 'Ethnic group'), value: a.race.trim() ? labelOf(o.race, a.race.trim()) : '' },
        { label: t('onboarding.height', 'Height'), value: unit(a.heightCm, 'cm') },
        { label: t('onboarding.weight', 'Weight'), value: unit(a.weightKg, 'kg') },
        { label: t('onboarding.sum.waist', 'Waist'), value: unit(a.waistCm, 'cm') },
      ],
    },
    {
      title: t('onboarding.s2.name', 'Diabetes history'),
      edit: step(2),
      rows: [
        { label: t('onboarding.sum.diagYear', 'Year of diagnosis'), value: a.diagnosedYear.trim() },
        { label: t('onboarding.sum.family', 'Type 2 diabetes in close family'), value: labelOf(o.yesNoUnsure, a.familyHistory) },
        { label: t('onboarding.sum.care', 'Usual place of care'), value: labelOf(o.careSetting, a.careSetting) },
        { label: t('onboarding.sum.hsg', 'Healthier SG'), value: labelOf(o.healthierSg, a.healthierSg) },
      ],
    },
    {
      title: t('onboarding.s3.name', 'Medicines'),
      edit: step(3),
      rows: [
        { label: t('onboarding.med.label', 'Diabetes medicines'), value: many(o.diabetesMeds, a.diabetesMeds) },
        { label: t('onboarding.omed.label', 'Other regular medicines'), value: many(o.otherMeds, a.otherMeds) },
      ],
    },
    {
      title: t('onboarding.s4.name', 'Low glucose'),
      edit: step(4),
      rows: [
        { label: t('onboarding.sum.hypo3m', 'Hypos in the last 3 months'), value: labelOf(o.hypo3m, a.hypo3m) },
        { label: t('onboarding.sum.severe', 'Needed help with a hypo in the last 12 months'), value: labelOf(o.yesNo, a.severeHypo) },
        { label: t('onboarding.sum.gold', 'Knows when a hypo is starting (1 always, 7 never)'), value: a.gold ?? '' },
      ],
    },
    {
      title: t('onboarding.s5.name', 'Other conditions'),
      edit: step(5),
      rows: [
        { label: t('onboarding.sum.conditions', 'Conditions'), value: list([...a.conditions.map((c) => labelOf(o.conditions, c)), a.otherConditions.trim()]) },
        {
          label: t('onboarding.allergy.label', 'Allergies'),
          value: a.noAllergies ? t('onboarding.sum.noAllergies', 'No known allergies') : list(a.allergies.map((x) => (x.reaction.trim() ? `${x.substance.trim()} (${x.reaction.trim()})` : x.substance.trim()))),
        },
        { label: t('onboarding.sum.eye', 'Last eye check'), value: labelOf(o.lastCheck, a.eyeCheck) },
        { label: t('onboarding.sum.foot', 'Last foot check'), value: labelOf(o.lastCheck, a.footCheck) },
      ],
    },
    {
      title: t('onboarding.s6.name', 'Lab results'),
      edit: step(6),
      rows: [
        { label: t('onboarding.sum.labDate', 'Date of the blood test'), value: date(a.labDate) },
        { label: t('onboarding.hba1c', 'HbA1c'), value: unit(a.hba1c, a.hba1cUnit) },
        { label: t('onboarding.fpg', 'Fasting glucose'), value: unit(a.fastingGlucose, a.glucoseUnit) },
        { label: t('onboarding.sum.insulin', 'Fasting insulin'), value: unit(a.fastingInsulin, 'µIU/mL') },
        { label: t('onboarding.sum.egfr', 'Kidney function (eGFR)'), value: unit(a.egfr, 'mL/min/1.73 m²') },
        { label: t('onboarding.bp.label', 'Blood pressure'), value: a.systolic.trim() && a.diastolic.trim() ? `${a.systolic.trim()} / ${a.diastolic.trim()} mmHg` : '' },
      ],
    },
    {
      title: t('onboarding.s7.name', 'Devices and routine'),
      edit: step(7),
      rows: [
        { label: t('onboarding.sum.cgm', 'Glucose sensor'), value: labelOf(o.cgm, a.cgm) },
        { label: t('onboarding.sum.watch', 'Smart watch'), value: labelOf(o.wearable, a.wearable) },
        { label: t('onboarding.sum.wake', 'Wakes at'), value: a.wakeTime ? clock(a.wakeTime) : '' },
        { label: t('onboarding.sum.sleep', 'Sleeps at'), value: a.sleepTime ? clock(a.sleepTime) : '' },
        { label: t('onboarding.sum.work', 'Work'), value: labelOf(o.work, a.workType) },
        { label: t('onboarding.sum.workDays', 'Work days'), value: many(o.weekdays, a.workDays.map(String)) },
        { label: t('onboarding.sum.workHours', 'Work hours'), value: a.workStart && a.workEnd ? `${clock(a.workStart)} to ${clock(a.workEnd)}` : '' },
        { label: t('onboarding.sum.fasting', 'Fasting'), value: many(o.fasting, a.fasting) },
        { label: t('onboarding.sum.reminders', 'Reminder times'), value: list(a.reminderTimes.map(clock)) },
      ],
    },
    {
      title: t('onboarding.s8.name', 'Lifestyle'),
      edit: step(8),
      rows: [
        { label: t('onboarding.sum.eatOut', 'Meals out a week'), value: labelOf(o.eatOut, a.eatOut) },
        { label: t('onboarding.sum.sweet', 'Sweet drinks'), value: labelOf(o.sweetDrinks, a.sweetDrinks) },
        { label: t('onboarding.sum.active', 'Active days a week'), value: labelOf(o.activeDays, a.activeDays) },
        { label: t('onboarding.sum.smoke', 'Smoking'), value: labelOf(o.smoking, a.smoking) },
        { label: t('onboarding.alcohol.label', 'Alcohol'), value: labelOf(o.alcohol, a.alcohol) },
      ],
    },
    {
      title: t('onboarding.s9.name', 'Safety check'),
      edit: step(ABOUT_STEPS),
      rows: [
        { label: t('onboarding.sum.redFlags', 'Happening now'), value: many(o.redFlags, a.redFlags) },
        { label: t('onboarding.sum.contact', 'Emergency contact'), value: list([a.contactName.trim(), a.contactRelation.trim(), a.contactPhone.trim()]) },
      ],
    },
  ]

  /* ---- plain arithmetic on the person's own numbers: no category, stage or target ---- */
  const calc: Row[] = []
  const birth = num(a.birthYear)
  if (birth) calc.push({ label: t('onboarding.calc.age', 'Age this year'), value: String(new Date().getFullYear() - birth) })
  const h = num(a.heightCm)
  const w = num(a.weightKg)
  if (h && w) calc.push({ label: t('onboarding.calc.bmi', 'Body mass index (BMI)'), value: `${convert.bmi(w, h).toFixed(1)} kg/m²` })
  const a1c = num(a.hba1c)
  if (a1c !== null) calc.push({ label: t('onboarding.calc.hba1c', 'HbA1c in the other unit'), value: a.hba1cUnit === '%' ? `${Math.round(convert.hba1cToMmolMol(a1c))} mmol/mol` : `${convert.hba1cToPct(a1c).toFixed(1)} %` })
  const fpg = num(a.fastingGlucose)
  if (fpg !== null) calc.push({ label: t('onboarding.calc.fpg', 'Fasting glucose in the other unit'), value: a.glucoseUnit === 'mmol/L' ? `${Math.round(convert.glucoseToMgDl(fpg))} mg/dL` : `${convert.glucoseToMmol(fpg).toFixed(1)} mmol/L` })

  /* ---- gaps in what was entered, restated as things to raise with the doctor ---- */
  const mention: string[] = []
  if (a1c === null) mention.push(t('onboarding.mention.hba1c', 'You did not enter an HbA1c result.'))
  if (a.eyeCheck && a.eyeCheck !== 'within_year') mention.push(t('onboarding.mention.eye', 'Your last diabetic eye check was more than a year ago, or you are not sure when it was.'))
  if (a.footCheck && a.footCheck !== 'within_year') mention.push(t('onboarding.mention.foot', 'Your last diabetic foot check was more than a year ago, or you are not sure when it was.'))

  const notGiven = t('onboarding.sum.notGiven', 'Not given')
  const title = a.name.trim() ? t('onboarding.sum.titleFor', 'Your profile summary, {{name}}', { name: a.name.trim() }) : t('onboarding.sum.title', 'Your profile summary')

  const finish = () => {
    set({ completedAt: new Date().toISOString() })
    toast(t('onboarding.sum.done', 'Setup finished'))
    navigate(href('B1'), { replace: true })
  }

  const table = (rows: Row[]) => (
    <dl className="flex flex-col divide-y divide-line">
      {rows.map((r) => (
        <div key={r.label} className="flex flex-wrap justify-between gap-x-4 gap-y-0.5 py-2.5">
          <dt className="text-sub text-ink2">{r.label}</dt>
          <dd className={r.value ? 'break-words text-right text-body font-bold' : 'text-body text-ink3'}>{r.value || notGiven}</dd>
        </div>
      ))}
    </dl>
  )

  return (
    <Screen>
      <TopBar />
      <div>
        <p className="text-sub font-bold text-brand">{t('onboarding.sum.step', 'All steps done')}</p>
        <h1 className="mt-1 break-words font-serif text-h1 font-medium tracking-tight text-ink">{title}</h1>
        <p className="mt-1.5 text-sub text-ink2">{t('onboarding.sum.sub', 'This is what you told us. Change anything that is not right.')}</p>
      </div>

      <SafetyAlerts flags={a.redFlags} />

      {calc.length > 0 && (
        <Card as="section" tone="hero" className="flex flex-col gap-1">
          <h2 className="font-serif text-h2 font-medium tracking-tight">{t('onboarding.calc.title', 'Worked out from your answers')}</h2>
          {table(calc)}
          <p className="pt-1 text-sub text-ink3">{t('onboarding.calc.note', 'Simple arithmetic and unit conversion only. Smart Health does not judge these numbers; your doctor does.')}</p>
        </Card>
      )}

      {mention.length > 0 && (
        <Card as="section" tone="soft" className="flex flex-col gap-2">
          <h2 className="font-serif text-h2 font-medium tracking-tight">{t('onboarding.mention.title', 'Worth mentioning to your doctor')}</h2>
          <ul className="flex list-disc flex-col gap-1.5 pl-5 text-body">
            {mention.map((m) => (
              <li key={m}>{m}</li>
            ))}
          </ul>
        </Card>
      )}

      {sections.map((s) => (
        <Card key={s.title} as="section" className="flex flex-col gap-1">
          <div className="flex flex-wrap items-center justify-between gap-x-3">
            <h2 className="font-serif text-h2 font-medium tracking-tight">{s.title}</h2>
            <TextLink icon={PencilSimple} onClick={() => navigate(s.edit)}>
              {t('onboarding.sum.edit', 'Edit')}
              <span className="sr-only"> {s.title}</span>
            </TextLink>
          </div>
          {table(s.rows)}
        </Card>
      ))}

      <Alert tone="info">{t('onboarding.sum.local', 'For now your answers stay on this device. They are not yet saved to your Smart Health record.')}</Alert>
      <p className="text-center text-sub text-ink3">{t('onboarding.sum.fine', 'Smart Health explains, organises and reminds. It is not a diagnosis and does not replace your doctor.')}</p>

      <Dock onBack={back} onNext={finish} nextLabel={t('onboarding.sum.finish', 'Finish')}>
        <TextLink
          onClick={() => {
            reset()
            navigate(href('A1'), { replace: true })
          }}
          className="self-center"
        >
          {t('onboarding.sum.restart', 'Clear my answers and start again')}
        </TextLink>
      </Dock>
    </Screen>
  )
}
