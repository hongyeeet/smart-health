/**
 * A3 — About you. Nine steps on one route (?step=1 to 9), so the browser's back button moves one step at a time.
 * The steps and questions follow Damien's clinical onboarding design (Stitch export): body measurements, diabetes history,
 * medicines, lows, conditions, lab results, devices and routine, lifestyle, and a safety check.
 *
 * The screen records answers and nothing else: no score, stage, category or target, and no comment on any value
 * (rules.md 1.1, 1.6). The checks below only catch typing slips. The kinds of medicine ticked here are background for the
 * doctor brief; the medicines themselves, with their doses, come only from the scan and add-by-hand screens.
 */
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { appConfig } from '@/config/app'
import { href } from '@/app/routeIds'
import { useBack, useGo } from '@/app/navigation'
import { useMeds } from '@/data/hooks'
import { Screen } from '@/ui/layout'
import { Segmented } from '@/ui/controls'
import { Alert, Button, Card, Field, TextLink, Toggle } from '@/ui/primitives'
import { Camera, Plus, Trash } from '@/ui/icons'
import { Dock, Group, PickMany, PickOne, Question, Scale, StepHead, TopBar, clock, useStepNav, type Option } from './parts'
import { REMINDER_TIMES, useOptions } from './options'
import { SafetyAlerts } from './SafetyAlerts'
import { LIMITS, inRange, num, pastDateOk, useOnboarding, yearOk, type GlucoseUnit, type Hba1cUnit, type OnboardingAnswers } from './useOnboarding'

export const ABOUT_STEPS = 9
/** Welcome and eligibility come first, so "about you" step 1 is step 3 of the whole flow. */
const OFFSET = 2
/** Adults only (prd section 3). */
const MIN_AGE = 18

type Errors = Partial<Record<keyof OnboardingAnswers, string>>

export function AboutYou() {
  const { t } = useTranslation()
  const go = useGo()
  const navigate = useNavigate()
  const back = useBack('A2')
  const { review, next } = useStepNav()
  const [params] = useSearchParams()
  const raw = Number(params.get('step'))
  const step = Number.isInteger(raw) && raw >= 1 && raw <= ABOUT_STEPS ? raw : 1

  const a = useOnboarding((s) => s.answers)
  const set = useOnboarding((s) => s.set)
  const opts = useOptions()
  const meds = useMeds()

  const heads: { name: string; title: string; sub: string }[] = [
    { name: t('onboarding.s1.name', 'Body measurements'), title: t('onboarding.s1.title', 'About you'), sub: t('onboarding.s1.sub', 'A few basics about you. Only the year of birth is needed.') },
    { name: t('onboarding.s2.name', 'Diabetes history'), title: t('onboarding.s2.title', 'Your diabetes and your care'), sub: t('onboarding.s2.sub', 'When it started and who looks after it.') },
    { name: t('onboarding.s3.name', 'Medicines'), title: t('onboarding.s3.title', 'Your medicines'), sub: t('onboarding.s3.sub', 'Tick every kind you take now. The names underneath are examples to help you find yours.') },
    {
      name: t('onboarding.s4.name', 'Low glucose'),
      title: t('onboarding.s4.title', 'Low glucose (hypos)'),
      sub: t('onboarding.s4.sub', 'A hypo is a low glucose reading, below {{low}} mmol/L, often with sweating, shaking or dizziness.', { low: appConfig.hypoTiers.low.toFixed(1) }),
    },
    { name: t('onboarding.s5.name', 'Other conditions'), title: t('onboarding.s5.title', 'Other conditions and check-ups'), sub: t('onboarding.s5.sub', 'Things a doctor has told you that you have, your allergies, and your last diabetes checks.') },
    { name: t('onboarding.s6.name', 'Lab results'), title: t('onboarding.s6.title', 'Lab results and blood pressure'), sub: t('onboarding.s6.sub', 'Copy the numbers from your most recent report. Leave blank anything you do not have.') },
    { name: t('onboarding.s7.name', 'Devices and routine'), title: t('onboarding.s7.title', 'Your devices and your day'), sub: t('onboarding.s7.sub', 'Which devices you use, and what a usual day looks like.') },
    { name: t('onboarding.s8.name', 'Lifestyle'), title: t('onboarding.s8.title', 'Eating, activity and habits'), sub: t('onboarding.s8.sub', 'Rough answers are fine. There are no right or wrong ones.') },
    { name: t('onboarding.s9.name', 'Safety check'), title: t('onboarding.s9.title', 'A safety check before you start'), sub: t('onboarding.s9.sub', 'Tell us if any of these is happening, and who to contact in an emergency.') },
  ]
  const head = heads[step - 1]!

  /* ---- checks: they only catch typing slips, and say what to fix ---- */
  const thisYear = new Date().getFullYear()
  const between = (lo: number, hi: number, unit: string) => t('onboarding.err.between', 'Enter a number from {{lo}} to {{hi}} {{unit}}, or leave it blank.', { lo, hi, unit })
  const e: Errors = {}
  if (a.birthYear.trim() && !yearOk(a.birthYear)) e.birthYear = t('onboarding.err.year', 'Enter a 4-digit year, like 1968.')
  else if (a.birthYear.trim() && thisYear - Number(a.birthYear) < MIN_AGE) e.birthYear = t('onboarding.err.adult', 'Smart Health is for adults aged 18 or older.')
  if (!inRange(a.heightCm, LIMITS.heightCm)) e.heightCm = between(...LIMITS.heightCm, 'cm')
  if (!inRange(a.weightKg, LIMITS.weightKg)) e.weightKg = between(...LIMITS.weightKg, 'kg')
  if (!inRange(a.waistCm, LIMITS.waistCm)) e.waistCm = between(...LIMITS.waistCm, 'cm')
  if (!yearOk(a.diagnosedYear, { notBefore: yearOk(a.birthYear, { required: true }) ? Number(a.birthYear) : 1900 })) e.diagnosedYear = t('onboarding.err.diagYear', 'Enter a 4-digit year, not before you were born and not in the future.')
  if (!pastDateOk(a.labDate)) e.labDate = t('onboarding.err.future', 'This date is in the future.')
  const hba1cLimit = a.hba1cUnit === '%' ? LIMITS.hba1cPct : LIMITS.hba1cMmolMol
  if (!inRange(a.hba1c, hba1cLimit)) e.hba1c = between(hba1cLimit[0], hba1cLimit[1], a.hba1cUnit)
  const glucoseLimit = a.glucoseUnit === 'mmol/L' ? LIMITS.glucoseMmol : LIMITS.glucoseMgDl
  if (!inRange(a.fastingGlucose, glucoseLimit)) e.fastingGlucose = between(glucoseLimit[0], glucoseLimit[1], a.glucoseUnit)
  if (!inRange(a.fastingInsulin, LIMITS.fastingInsulin)) e.fastingInsulin = between(...LIMITS.fastingInsulin, 'µIU/mL')
  if (!inRange(a.egfr, LIMITS.egfr)) e.egfr = between(...LIMITS.egfr, '')
  if (!inRange(a.systolic, LIMITS.systolic)) e.systolic = between(...LIMITS.systolic, 'mmHg')
  if (!inRange(a.diastolic, LIMITS.diastolic)) e.diastolic = between(...LIMITS.diastolic, 'mmHg')
  const sys = num(a.systolic)
  const dia = num(a.diastolic)
  if (!e.systolic && !e.diastolic) {
    if ((sys === null) !== (dia === null)) e[sys === null ? 'systolic' : 'diastolic'] = t('onboarding.err.bpBoth', 'Enter both numbers, or leave both blank.')
    else if (sys !== null && dia !== null && dia >= sys) e.diastolic = t('onboarding.err.bpOrder', 'The bottom number should be lower than the top number.')
  }

  const fieldsByStep: (keyof OnboardingAnswers)[][] = [['birthYear', 'heightCm', 'weightKg', 'waistCm'], ['diagnosedYear'], [], [], [], ['labDate', 'hba1c', 'fastingGlucose', 'fastingInsulin', 'egfr', 'systolic', 'diastolic'], [], [], []]
  const stepHasError = fieldsByStep[step - 1]!.some((k) => e[k])
  const working = a.workType !== null && a.workType !== 'not_working'
  const workMissing = working && (a.workDays.length === 0 || !a.workStart || !a.workEnd)
  const contactMissing = !a.contactName.trim() || !a.contactPhone.trim() || !a.contactRelation.trim()
  const blocked = stepHasError || (step === 1 && !a.birthYear.trim()) || (step === 7 && workMissing) || (step === 9 && (a.redFlags.length === 0 || contactMissing))
  const raceIsSuggestion = opts.race.some((o) => o.value === a.race)

  const onNext = () => next(step < ABOUT_STEPS ? `${href('A3')}?step=${step + 1}` : href('A6'))
  const nextLabel = review ? t('onboarding.backToSummary', 'Back to summary') : step === ABOUT_STEPS ? t('onboarding.toSummary', 'Check my answers') : t('common.continue', 'Continue')

  const setAllergy = (i: number, patch: Partial<OnboardingAnswers['allergies'][number]>) => set({ allergies: a.allergies.map((x, k) => (k === i ? { ...x, ...patch } : x)) })
  const reminderOptions: Option<string>[] = REMINDER_TIMES.map((v) => ({ value: v, label: clock(v) }))
  const twoCol = "grid grid-cols-2 gap-3 [[data-ts='2']_&]:grid-cols-1"
  const hba1cUnits: { value: Hba1cUnit; label: string }[] = [{ value: '%', label: '%' }, { value: 'mmol/mol', label: 'mmol/mol' }]
  const glucoseUnits: { value: GlucoseUnit; label: string }[] = [{ value: 'mmol/L', label: 'mmol/L' }, { value: 'mg/dL', label: 'mg/dL' }]

  return (
    <Screen>
      <TopBar />
      <StepHead step={step + OFFSET} name={head.name} title={head.title} sub={head.sub} />

      {step === 1 && (
        <Group>
          <Field label={t('onboarding.birthYear', 'Year of birth')} inputMode="numeric" value={a.birthYear} onChange={(birthYear) => set({ birthYear })} placeholder="1965" error={e.birthYear} />
          <PickOne label={t('onboarding.gender.label', 'Gender')} options={opts.gender} value={a.gender} onChange={(gender) => set({ gender })} />
          <PickOne label={t('onboarding.race.label', 'Ethnic group')} options={opts.race} value={raceIsSuggestion ? a.race : null} onChange={(race) => set({ race: race ?? '' })} />
          <Field label={t('onboarding.race.other', 'Or type it in')} value={raceIsSuggestion ? '' : a.race} onChange={(race) => set({ race })} />
          <div className={twoCol}>
            <Field label={t('onboarding.height', 'Height')} inputMode="decimal" suffix="cm" value={a.heightCm} onChange={(heightCm) => set({ heightCm })} placeholder="168" error={e.heightCm} />
            <Field label={t('onboarding.weight', 'Weight')} inputMode="decimal" suffix="kg" value={a.weightKg} onChange={(weightKg) => set({ weightKg })} placeholder="72" error={e.weightKg} />
          </div>
          <Field label={t('onboarding.waist', 'Waist (optional)')} inputMode="decimal" suffix="cm" value={a.waistCm} onChange={(waistCm) => set({ waistCm })} placeholder="84" hint={t('onboarding.waistHint', 'Measured around your middle, level with your belly button.')} error={e.waistCm} />
        </Group>
      )}

      {step === 2 && (
        <Group>
          <Field label={t('onboarding.diagYear', 'Year you were told you have type 2 diabetes')} inputMode="numeric" value={a.diagnosedYear} onChange={(diagnosedYear) => set({ diagnosedYear })} placeholder="2016" error={e.diagnosedYear} />
          <PickOne label={t('onboarding.family', 'Does a parent, brother or sister have type 2 diabetes?')} options={opts.yesNoUnsure} value={a.familyHistory} onChange={(familyHistory) => set({ familyHistory })} />
          <PickOne label={t('onboarding.care.label', 'Where do you usually go for your diabetes?')} options={opts.careSetting} value={a.careSetting} onChange={(careSetting) => set({ careSetting })} />
          <PickOne label={t('onboarding.hsg.label', 'Are you enrolled in Healthier SG?')} options={opts.healthierSg} value={a.healthierSg} onChange={(healthierSg) => set({ healthierSg })} />
        </Group>
      )}

      {step === 3 && (
        <>
          <Group>
            <PickMany stack none="none" label={t('onboarding.med.label', 'Diabetes medicines')} options={opts.diabetesMeds} value={a.diabetesMeds} onChange={(diabetesMeds) => set({ diabetesMeds })} />
          </Group>
          <Group>
            <PickMany stack none="none" label={t('onboarding.omed.label', 'Other regular medicines')} options={opts.otherMeds} value={a.otherMeds} onChange={(otherMeds) => set({ otherMeds })} />
          </Group>
          <Group title={t('onboarding.meds.addTitle', 'Add each medicine from its label')}>
            <p className="text-sub text-ink2">{t('onboarding.meds.intro', 'The ticks above only tell your doctor which kinds you take. For reminders and explanations, add each medicine: Smart Health copies what is on your label and you confirm it. You can also do this later from Medications.')}</p>
            <div className="flex flex-col gap-2">
              <Button variant="secondary" icon={Camera} onClick={() => go('H2')}>
                {t('onboarding.meds.scan', 'Scan a label')}
              </Button>
              <Button variant="secondary" icon={Plus} onClick={() => go('H8')}>
                {t('onboarding.meds.byHand', 'Add by hand')}
              </Button>
            </div>
            {meds.data && meds.data.length > 0 && (
              <Card tone="soft" className="flex flex-col gap-1.5">
                <p className="text-sub font-bold text-ink2">{t('onboarding.meds.added', 'Already in your list')}</p>
                <ul className="flex flex-col gap-1">
                  {meds.data.map((m) => (
                    <li key={m.id} className="break-words text-body">
                      {m.name} {m.strength}
                    </li>
                  ))}
                </ul>
              </Card>
            )}
          </Group>
          <Alert tone="info">{t('onboarding.meds.note', 'Smart Health explains and reminds. It never tells you to start, stop or change a medicine.')}</Alert>
        </>
      )}

      {step === 4 && (
        <>
          <Group>
            <PickOne label={t('onboarding.hypo.count', 'How many hypos have you had in the last 3 months?')} options={opts.hypo3m} value={a.hypo3m} onChange={(hypo3m) => set({ hypo3m })} />
            <PickOne label={t('onboarding.hypo.severe', 'In the last 12 months, have you had a hypo where you needed someone else to help you?')} options={opts.yesNo} value={a.severeHypo} onChange={(severeHypo) => set({ severeHypo })} />
          </Group>
          <Group>
            <Scale
              max={7}
              label={t('onboarding.gold.q', 'Do you know when your hypos are starting?')}
              value={a.gold}
              onChange={(gold) => set({ gold })}
              lowLabel={t('onboarding.gold.low', '1 = always aware')}
              highLabel={t('onboarding.gold.high', '7 = never aware')}
            />
            <p className="text-sub text-ink3">{t('onboarding.gold.note', 'Your answer is passed to your doctor as you gave it. Skip it if you have never had a hypo.')}</p>
          </Group>
        </>
      )}

      {step === 5 && (
        <>
          <Group>
            <PickMany stack none="none" label={t('onboarding.cond.label', 'Has a doctor told you that you have any of these?')} options={opts.conditions} value={a.conditions} onChange={(conditions) => set({ conditions })} />
            <Field label={t('onboarding.cond.other', 'Any other condition (optional)')} value={a.otherConditions} onChange={(otherConditions) => set({ otherConditions })} />
          </Group>
          <Group title={t('onboarding.allergy.label', 'Allergies')}>
            <div className="flex items-center justify-between gap-4">
              <p className="text-body">{t('onboarding.allergy.none', 'I have no known allergies')}</p>
              <Toggle on={a.noAllergies} onChange={(noAllergies) => set({ noAllergies, allergies: noAllergies ? [] : a.allergies })} label={t('onboarding.allergy.none', 'I have no known allergies')} />
            </div>
            {!a.noAllergies && (
              <>
                {a.allergies.map((x, i) => (
                  <Card key={i} tone="soft" className="flex flex-col gap-3">
                    <Field label={t('onboarding.allergy.substance', 'What are you allergic to?')} value={x.substance} onChange={(substance) => setAllergy(i, { substance })} placeholder={t('onboarding.allergy.substancePh', 'A medicine, food or material')} />
                    <Field label={t('onboarding.allergy.reaction', 'What happens (optional)')} value={x.reaction} onChange={(reaction) => setAllergy(i, { reaction })} />
                    <TextLink icon={Trash} onClick={() => set({ allergies: a.allergies.filter((_, k) => k !== i) })} className="self-start">
                      {t('onboarding.allergy.remove', 'Remove this allergy')}
                    </TextLink>
                  </Card>
                ))}
                <Button variant="secondary" size="md" icon={Plus} onClick={() => set({ allergies: [...a.allergies, { substance: '', reaction: '' }] })}>
                  {t('onboarding.allergy.add', 'Add an allergy')}
                </Button>
              </>
            )}
          </Group>
          <Group title={t('onboarding.check.title', 'Your last diabetes checks')}>
            <PickOne label={t('onboarding.eyeCheck', 'Eye check (retinal photo)')} options={opts.lastCheck} value={a.eyeCheck} onChange={(eyeCheck) => set({ eyeCheck })} />
            <PickOne label={t('onboarding.footCheck', 'Foot check')} options={opts.lastCheck} value={a.footCheck} onChange={(footCheck) => set({ footCheck })} />
          </Group>
        </>
      )}

      {step === 6 && (
        <Group>
          <Field label={t('onboarding.labDate', 'Date of the blood test')} type="date" value={a.labDate} onChange={(labDate) => set({ labDate })} error={e.labDate} />
          <div className="flex flex-col gap-2">
            <Field label={t('onboarding.hba1c', 'HbA1c')} inputMode="decimal" value={a.hba1c} onChange={(hba1c) => set({ hba1c })} placeholder={a.hba1cUnit === '%' ? '7.2' : '55'} error={e.hba1c} />
            <Segmented label={t('onboarding.hba1cUnit', 'HbA1c unit')} options={hba1cUnits} value={a.hba1cUnit} onChange={(hba1cUnit) => set({ hba1cUnit })} />
          </div>
          <div className="flex flex-col gap-2">
            <Field label={t('onboarding.fpg', 'Fasting glucose')} inputMode="decimal" value={a.fastingGlucose} onChange={(fastingGlucose) => set({ fastingGlucose })} placeholder={a.glucoseUnit === 'mmol/L' ? '7.4' : '133'} error={e.fastingGlucose} />
            <Segmented label={t('onboarding.fpgUnit', 'Fasting glucose unit')} options={glucoseUnits} value={a.glucoseUnit} onChange={(glucoseUnit) => set({ glucoseUnit })} />
          </div>
          <Field label={t('onboarding.insulin', 'Fasting insulin (optional)')} inputMode="decimal" suffix="µIU/mL" value={a.fastingInsulin} onChange={(fastingInsulin) => set({ fastingInsulin })} placeholder="11.5" error={e.fastingInsulin} />
          <Field label={t('onboarding.egfr', 'Kidney function (eGFR)')} inputMode="decimal" value={a.egfr} onChange={(egfr) => set({ egfr })} placeholder="82" hint={t('onboarding.egfrHint', 'In mL/min/1.73 m², as printed on your report.')} error={e.egfr} />
          <Question label={t('onboarding.bp.label', 'Blood pressure')} hint={t('onboarding.bp.hint', 'Your last reading, for example 128 over 82.')}>
            <div className={twoCol}>
              <Field label={t('onboarding.bp.sys', 'Top number')} inputMode="numeric" suffix="mmHg" value={a.systolic} onChange={(systolic) => set({ systolic })} placeholder="128" error={e.systolic} />
              <Field label={t('onboarding.bp.dia', 'Bottom number')} inputMode="numeric" suffix="mmHg" value={a.diastolic} onChange={(diastolic) => set({ diastolic })} placeholder="82" error={e.diastolic} />
            </div>
          </Question>
        </Group>
      )}

      {step === 7 && (
        <>
          <Group title={t('onboarding.cgm.title', 'Glucose sensor (CGM)')}>
            <PickOne label={t('onboarding.cgm.label', 'Which sensor do you use?')} options={opts.cgm} value={a.cgm} onChange={(cgm) => set({ cgm })} />
          </Group>
          <Group title={t('onboarding.wear.title', 'Smart watch')}>
            <PickOne label={t('onboarding.wear.label', 'Which watch do you wear?')} options={opts.wearable} value={a.wearable} onChange={(wearable) => set({ wearable })} />
          </Group>
          <Alert tone="info">{t('onboarding.connect.note', 'Nothing is paired in this step. You link a watch or sensor later in Me, under Connected sources. They only send data to Smart Health.')}</Alert>
          <Group title={t('onboarding.routine.title', 'Your usual day')}>
            <div className={twoCol}>
              <Field label={t('onboarding.wake', 'I usually wake at')} type="time" value={a.wakeTime} onChange={(wakeTime) => set({ wakeTime })} />
              <Field label={t('onboarding.sleep', 'I usually sleep at')} type="time" value={a.sleepTime} onChange={(sleepTime) => set({ sleepTime })} />
            </div>
            <PickOne label={t('onboarding.work.label', 'Your work')} options={opts.work} value={a.workType} onChange={(workType) => set(workType === null || workType === 'not_working' ? { workType, workDays: [], workStart: '', workEnd: '' } : { workType })} />
            {working && (
              <>
                <PickMany label={t('onboarding.work.days', 'Days you usually work')} options={opts.weekdays} value={a.workDays.map(String)} onChange={(d) => set({ workDays: d.map(Number).sort((x, y) => x - y) })} />
                <div className={twoCol}>
                  <Field label={t('onboarding.work.start', 'Work starts')} type="time" value={a.workStart} onChange={(workStart) => set({ workStart })} />
                  <Field label={t('onboarding.work.end', 'Work ends')} type="time" value={a.workEnd} onChange={(workEnd) => set({ workEnd })} />
                </div>
                {workMissing && <p className="text-sub text-ink2">{t('onboarding.work.needed', 'Choose your work days and hours to continue. For a night shift, the end time can be earlier than the start.')}</p>}
              </>
            )}
            <PickMany none="none" label={t('onboarding.fast.label', 'Do you fast regularly?')} options={opts.fasting} value={a.fasting} onChange={(fasting) => set({ fasting })} />
            <PickMany label={t('onboarding.reminders', 'Good times for reminders')} hint={t('onboarding.remindersHint', 'Pick any. You can change them later.')} options={reminderOptions} value={a.reminderTimes} onChange={(reminderTimes) => set({ reminderTimes: [...reminderTimes].sort() })} />
          </Group>
        </>
      )}

      {step === 8 && (
        <Group>
          <PickOne label={t('onboarding.eat.label', 'Meals a week from a hawker centre, food court or takeaway')} options={opts.eatOut} value={a.eatOut} onChange={(eatOut) => set({ eatOut })} />
          <PickOne label={t('onboarding.sweet.label', 'Sweet drinks a day (sweet kopi or teh, bubble tea, soft drinks)')} options={opts.sweetDrinks} value={a.sweetDrinks} onChange={(sweetDrinks) => set({ sweetDrinks })} />
          <PickOne label={t('onboarding.active.label', 'Days a week with 30 minutes or more of brisk activity')} options={opts.activeDays} value={a.activeDays} onChange={(activeDays) => set({ activeDays })} />
          <PickOne label={t('onboarding.smoke.label', 'Do you smoke?')} options={opts.smoking} value={a.smoking} onChange={(smoking) => set({ smoking })} />
          <PickOne label={t('onboarding.alcohol.label', 'Alcohol')} options={opts.alcohol} value={a.alcohol} onChange={(alcohol) => set({ alcohol })} />
        </Group>
      )}

      {step === 9 && (
        <>
          <Group>
            <PickMany stack none="none" label={t('onboarding.red.label', 'Is any of these happening? Tick all that apply.')} options={opts.redFlags} value={a.redFlags} onChange={(redFlags) => set({ redFlags })} hint={a.redFlags.length === 0 ? t('onboarding.red.needed', 'Tick at least one answer to continue.') : undefined} />
            <SafetyAlerts flags={a.redFlags} />
          </Group>
          <Group title={t('onboarding.contact.label', 'Emergency contact')}>
            <Field label={t('onboarding.contact.name', 'Their name')} value={a.contactName} onChange={(contactName) => set({ contactName })} placeholder={t('onboarding.contact.namePh', 'Next of kin or caregiver')} />
            <Field label={t('onboarding.contact.relation', 'Who they are to you')} value={a.contactRelation} onChange={(contactRelation) => set({ contactRelation })} placeholder={t('onboarding.contact.relationPh', 'For example, wife, son or friend')} />
            <Field label={t('onboarding.contact.phone', 'Their mobile number')} type="tel" inputMode="tel" value={a.contactPhone} onChange={(contactPhone) => set({ contactPhone })} placeholder="+65 9123 4567" hint={contactMissing ? t('onboarding.contact.needed', 'Their name, number and relationship are needed to continue. Used for safety only.') : t('onboarding.contact.hint', 'Used for safety only. You can change this later.')} />
          </Group>
        </>
      )}

      <Dock onBack={review ? () => navigate(href('A6')) : back} onNext={onNext} nextDisabled={blocked} nextLabel={nextLabel} />
    </Screen>
  )
}
