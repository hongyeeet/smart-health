/**
 * A3 — About you, pages 3 to 10 on one route (?step=3 to 10). The step in the address is the page number, so the counter reads
 * "Step N of 10". Back goes to the page before (by replacing the address, so the browser history never loops) and, from the first page,
 * to the eligibility check. Continue saves this page to the record (usePageSave) before moving on. Medicines are not asked here:
 * they are added from the Medications tab.
 *
 * The screen records answers and nothing else: no score, stage, category or target, and no comment on any value (rules.md 1.1, 1.6).
 * The checks only catch typing slips and missing required answers, and each one says what to fix.
 */
import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { appConfig } from '@/config/app'
import { href } from '@/app/routeIds'
import { Screen } from '@/ui/layout'
import { Alert, Button, Card, Field, TextLink, Toggle } from '@/ui/primitives'
import { Plus, Trash } from '@/ui/icons'
import { DemoNotice, Dock, Group, InfoTip, Later, LoadNotice, LoadingAnswers, PickMany, PickOne, Scale, StepHead, TopBar, UnitToggle, useStepNav } from './parts'
import { RACE_OTHERS, labelOf, useOptions } from './options'
import { emailBody, pageBody, useOnboardingSource, type ProfileBody } from './api'
import { usePageSave } from './usePageSave'
import { LIMITS, emailOk, inRange, pastDateOk, phoneOk, useOnboarding, yearOk, type GlucoseUnit, type Hba1cUnit, type OnboardingAnswers } from './useOnboarding'

/** The first and last page on this route. Welcome (1) and eligibility (2) have their own routes. Page 5 (medicines) was removed and the later pages renumbered. */
export const FIRST_PAGE = 3
export const LAST_PAGE = 10
/** Adults only (prd section 3). */
const MIN_AGE = 18

type Errors = Partial<Record<keyof OnboardingAnswers, string>>

export function AboutYou() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { review, next } = useStepNav()
  const [params] = useSearchParams()
  const raw = Number(params.get('step'))
  const step = Number.isInteger(raw) && raw >= FIRST_PAGE && raw <= LAST_PAGE ? raw : FIRST_PAGE

  const a = useOnboarding((s) => s.answers)
  const set = useOnboarding((s) => s.set)
  const opts = useOptions()
  const src = useOnboardingSource()
  const page = usePageSave(src.loadFailed)
  /* the same route serves every page, so a message from one page is cleared when the person moves to another */
  useEffect(() => page.reset(), [step])

  /* ---- headings: the page title and what the page is for ---- */
  const heads: Record<number, { name: string; title: string; sub: string }> = {
    3: { name: t('onboarding.s3.name', 'About you'), title: t('onboarding.s3.title', 'About you'), sub: t('onboarding.s3.sub', 'A few basics. Only the year of birth is needed to continue.') },
    4: { name: t('onboarding.s4.name', 'Diabetes history'), title: t('onboarding.s4.title', 'Your diabetes and your care'), sub: t('onboarding.s4.sub', 'When it was found, and who looks after it.') },
    5: { name: t('onboarding.s6.name', 'Low glucose'), title: t('onboarding.s6.title', 'Low glucose (hypos)'), sub: t('onboarding.s6.sub', 'Answer what you can. Tap the i to see what a hypo is.') },
    6: { name: t('onboarding.s7.name', 'Other conditions and checks'), title: t('onboarding.s7.title', 'Other conditions and check-ups'), sub: t('onboarding.s7.sub', 'Things a doctor has told you about, your allergies, and your last diabetes checks.') },
    7: { name: t('onboarding.s8.name', 'Lab results'), title: t('onboarding.s8.title', 'Lab results'), sub: t('onboarding.s8.sub', 'Copy the numbers from your most recent report. Leave blank anything you do not have.') },
    8: { name: t('onboarding.s9.name', 'Devices'), title: t('onboarding.s9.title', 'Your watch and sensor'), sub: t('onboarding.s9.sub', 'Choose what you use. Nothing is paired on this page.') },
    9: { name: t('onboarding.s10.name', 'Your work week'), title: t('onboarding.s10.title', 'Your work week'), sub: t('onboarding.s10.sub', 'When you usually work, so reminders can fit your day.') },
    10: { name: t('onboarding.s11.name', 'Emergency contact'), title: t('onboarding.s11.title', 'Who should we contact in an emergency?'), sub: t('onboarding.s11.sub', 'All four details are needed. They are used for safety only.') },
  }
  const head = heads[step]!

  /* ---- checks: they only catch typing slips and missing answers, and say what to fix ---- */
  const thisYear = new Date().getFullYear()
  const between = (lo: number, hi: number, unit: string) => t('onboarding.err.between', 'Enter a number from {{lo}} to {{hi}} {{unit}}, or leave it blank.', { lo, hi, unit })
  const e: Errors = {}
  if (a.birthYear.trim() && !yearOk(a.birthYear)) e.birthYear = t('onboarding.err.year', 'Enter a 4-digit year, like 1968.')
  else if (a.birthYear.trim() && thisYear - Number(a.birthYear) < MIN_AGE) e.birthYear = t('onboarding.err.adult', 'Smart Health is for adults aged 18 or older.')
  if (!inRange(a.heightCm, LIMITS.heightCm)) e.heightCm = between(...LIMITS.heightCm, 'cm')
  if (!inRange(a.weightKg, LIMITS.weightKg)) e.weightKg = between(...LIMITS.weightKg, 'kg')
  if (!inRange(a.waistCm, LIMITS.waistCm)) e.waistCm = between(...LIMITS.waistCm, 'cm')
  if (!yearOk(a.diagnosedYear, { notBefore: yearOk(a.birthYear, { required: true }) ? Number(a.birthYear) : 1900 })) e.diagnosedYear = t('onboarding.err.diagYear', 'Enter a 4-digit year, not before you were born and not in the future.')
  const hba1cLimit = a.hba1cUnit === '%' ? LIMITS.hba1cPct : LIMITS.hba1cMmolMol
  if (!inRange(a.hba1c, hba1cLimit)) e.hba1c = between(hba1cLimit[0], hba1cLimit[1], a.hba1cUnit)
  const glucoseLimit = a.glucoseUnit === 'mmol/L' ? LIMITS.glucoseMmol : LIMITS.glucoseMgDl
  if (!inRange(a.fastingGlucose, glucoseLimit)) e.fastingGlucose = between(glucoseLimit[0], glucoseLimit[1], a.glucoseUnit)
  if (!inRange(a.fastingInsulin, LIMITS.fastingInsulin)) e.fastingInsulin = between(...LIMITS.fastingInsulin, 'µIU/mL')
  if (!pastDateOk(a.labDate)) e.labDate = t('onboarding.err.future', 'This date is in the future.')
  const hasLab = [a.hba1c, a.fastingGlucose, a.fastingInsulin].some((v) => v.trim() !== '')
  if (hasLab && !a.labDate && !e.labDate) e.labDate = t('onboarding.err.labDate', 'Enter the date of your blood test. It is needed with the numbers.')
  const contactProblems: Errors = {}
  if (a.contactPhone.trim() && !phoneOk(a.contactPhone)) contactProblems.contactPhone = t('onboarding.err.phone', 'Enter a mobile number with digits, like +65 9123 4567.')
  if (a.contactEmail.trim() && !emailOk(a.contactEmail)) contactProblems.contactEmail = t('onboarding.err.emailV2', 'Enter an email address like name@example.com.')
  const working = a.workType !== null && a.workType !== 'not_working'
  const workMissing = working && (a.workDays.length === 0 || !a.workStart || !a.workEnd)
  const contactMissing = !a.contactName.trim() || !a.contactRelation.trim() || !a.contactPhone.trim() || !a.contactEmail.trim()
  const pageErrors: Errors = { ...e, ...contactProblems }
  /* a page is only held up by its own fields, so a problem on one page never blocks another */
  const fieldsOnPage: Partial<Record<number, (keyof OnboardingAnswers)[]>> = {
    3: ['birthYear', 'heightCm', 'weightKg', 'waistCm'],
    4: ['diagnosedYear'],
    7: ['labDate', 'hba1c', 'fastingGlucose', 'fastingInsulin'],
    10: ['contactPhone', 'contactEmail'],
  }
  const blocked =
    (fieldsOnPage[step] ?? []).some((k) => pageErrors[k]) ||
    (step === 3 && !a.birthYear.trim()) ||
    (step === 9 && workMissing) ||
    (step === 10 && contactMissing)

  /* ---- what this page saves, and moving on ---- */
  const firstSave = !src.saved.data?.profile
  /* The server creates the profile from page 3 (it needs the birth year). Until then, pages 4 to 11 are kept on this device and
     the Finish step saves them all. */
  const profileBody = (): ProfileBody | null => {
    if (step === 3) return pageBody(3, a, firstSave)
    if (firstSave) return null
    return pageBody(step, a, false)
  }
  /* the reminder email is sent here too when it was not stored yet (typed on Welcome before the profile existed) */
  const storedEmail = src.email.data
  const emailPending = (a.reminderEmail.trim() || null) !== (storedEmail?.email ?? null) || a.reminderOn !== (storedEmail?.optIn ?? true)
  /* the email follows the profile: it is sent once the profile exists (page 3 creates it), or when an address was typed */
  const emailNow = emailPending && (step === FIRST_PAGE || !firstSave || a.reminderEmail.trim() !== '') ? emailBody(a) : null
  const onNext = async () => {
    if (!page.holding) {
      const ok = await page.commit(profileBody(), emailNow)
      if (!ok) return
    }
    if (step < LAST_PAGE) return next(`${href('A3')}?step=${step + 1}`)
    next(href('A6'))
  }
  /* Back names the page before and replaces the address, so Back never pops the history (that made pages 3 and 4 bounce between each other) */
  const onBack = review ? () => navigate(href('A6')) : () => navigate(step === FIRST_PAGE ? href('A2') : `${href('A3')}?step=${step - 1}`, { replace: true })

  const setAllergy = (i: number, patch: Partial<OnboardingAnswers['allergies'][number]>) => set({ allergies: a.allergies.map((x, k) => (k === i ? { ...x, ...patch } : x)) })
  const twoCol = "grid grid-cols-2 gap-3 [[data-ts='2']_&]:grid-cols-1"
  const hba1cUnits: { value: Hba1cUnit; label: string }[] = [{ value: '%', label: '%' }, { value: 'mmol/mol', label: 'mmol/mol' }]
  const glucoseUnits: { value: GlucoseUnit; label: string }[] = [{ value: 'mmol/L', label: 'mmol/L' }, { value: 'mg/dL', label: 'mg/dL' }]
  /* Ethnic group: Chinese, Malay or Indian are picked; "Others" shows a box to say which. An older answer that is none of the three opens as Others. */
  const raceIsSuggestion = opts.race.some((o) => o.value !== RACE_OTHERS && o.value === a.race)
  const [othersTapped, setOthersTapped] = useState(false)
  const raceOthers = othersTapped || (a.race.trim() !== '' && !raceIsSuggestion)
  const pickRace = (v: string | null) => {
    if (v === RACE_OTHERS) {
      setOthersTapped(true)
      if (raceIsSuggestion) set({ race: '' })
    } else {
      setOthersTapped(false)
      set({ race: v ?? '' })
    }
  }
  const nextLabel = review ? t('onboarding.backToSummary', 'Back to summary') : step === LAST_PAGE ? t('onboarding.toSummary', 'Check my answers') : t('common.continue', 'Continue')
  const continueAnyway = page.holding

  if (!src.ready) {
    return (
      <Screen narrow>
        <TopBar />
        <LoadingAnswers />
      </Screen>
    )
  }

  return (
    <Screen narrow>
      <TopBar />
      <StepHead step={step} name={head.name} title={head.title} sub={head.sub} />
      {src.loadFailed && <LoadNotice />}
      {src.readOnly && <DemoNotice />}
      {page.error && <Alert tone="danger">{page.error}</Alert>}
      {page.notice && <Alert tone="info">{page.notice}</Alert>}

      {step === 3 && (
        <Group>
          <Field label={t('onboarding.birthYear', 'Year of birth')} inputMode="numeric" value={a.birthYear} onChange={(birthYear) => set({ birthYear })} placeholder="1965" error={e.birthYear} hint={t('onboarding.birthYearHint', 'Needed to continue.')} />
          <PickOne label={t('onboarding.gender.label', 'Sex')} options={opts.gender} value={a.gender} onChange={(gender) => set({ gender })} />
          <PickOne label={t('onboarding.race.label', 'Ethnic group')} options={opts.race} value={raceOthers ? RACE_OTHERS : raceIsSuggestion ? a.race : null} onChange={pickRace} />
          {raceOthers && <Field label={t('onboarding.race.otherV2', 'Please say which')} value={raceIsSuggestion ? '' : a.race} onChange={(race) => set({ race })} />}
          <div className={twoCol}>
            <Field label={t('onboarding.height', 'Height')} inputMode="decimal" suffix="cm" value={a.heightCm} onChange={(heightCm) => set({ heightCm })} placeholder="168" error={e.heightCm} />
            <Field label={t('onboarding.weight', 'Weight')} inputMode="decimal" suffix="kg" value={a.weightKg} onChange={(weightKg) => set({ weightKg })} placeholder="72" error={e.weightKg} />
          </div>
          <Field label={t('onboarding.waist', 'Waist (optional)')} inputMode="decimal" suffix="cm" value={a.waistCm} onChange={(waistCm) => set({ waistCm })} placeholder="84" hint={t('onboarding.waistHint', 'Measured around your middle, level with your belly button.')} error={e.waistCm} />
        </Group>
      )}

      {step === 4 && (
        <Group>
          <Field label={t('onboarding.diagYear', 'Year you were told you have type 2 diabetes')} inputMode="numeric" value={a.diagnosedYear} onChange={(diagnosedYear) => set({ diagnosedYear })} placeholder="2016" error={e.diagnosedYear} />
          <PickOne label={t('onboarding.care.label', 'Where do you usually go for your diabetes?')} options={opts.careSetting} value={a.careSetting} onChange={(careSetting) => set({ careSetting })} />
          <PickOne label={t('onboarding.hsg.label', 'Are you enrolled in Healthier SG?')} options={opts.healthierSg} value={a.healthierSg} onChange={(healthierSg) => set({ healthierSg })} />
        </Group>
      )}

      {step === 5 && (
        <>
          <Group>
            <div className="flex items-center gap-2 text-sub text-ink2">
              <span>{t('onboarding.hypo.what', 'What is a hypo?')}</span>
              <InfoTip label={t('onboarding.hypo.whatLabel', 'What is a hypo?')}>
                <p>{t('onboarding.hypo.tip', 'A hypo is a low glucose reading, below {{low}} mmol/L, often with sweating, shaking or dizziness.', { low: appConfig.hypoTiers.low.toFixed(1) })}</p>
              </InfoTip>
            </div>
            <PickOne label={t('onboarding.hypo.count', 'How many hypos have you had in the last 3 months?')} options={opts.hypo3m} value={a.hypo3m} onChange={(hypo3m) => set({ hypo3m })} />
            <PickOne label={t('onboarding.hypo.severe', 'In the last 12 months, have you had a hypo where you needed someone else to help you?')} options={opts.yesNo} value={a.severeHypo} onChange={(severeHypo) => set({ severeHypo })} />
          </Group>
          <Group>
            <Scale
              max={5}
              label={t('onboarding.gold.q', 'Do you know when your hypos are starting?')}
              value={a.gold}
              onChange={(gold) => set({ gold })}
              lowLabel={t('onboarding.gold.low', '1 = always aware')}
              highLabel={t('onboarding.gold.highV2', '5 = never aware')}
            />
            <p className="text-sub text-ink3">{t('onboarding.gold.note', 'Leave it blank if you have never had a hypo.')}</p>
          </Group>
        </>
      )}

      {step === 6 && (
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

      {step === 7 && (
        <Group>
          <Field label={t('onboarding.labDate', 'Date of the blood test')} type="date" value={a.labDate} onChange={(labDate) => set({ labDate })} error={e.labDate} hint={hasLab ? undefined : t('onboarding.labDateHint', 'Needed if you enter any number below.')} />
          <div className="flex flex-col gap-2">
            <Field label={t('onboarding.hba1c', 'HbA1c')} inputMode="decimal" value={a.hba1c} onChange={(hba1c) => set({ hba1c })} placeholder={a.hba1cUnit === '%' ? '7.2' : '55'} error={e.hba1c} />
            <UnitToggle label={t('onboarding.hba1cUnit', 'HbA1c unit')} options={hba1cUnits} value={a.hba1cUnit} onChange={(hba1cUnit) => set({ hba1cUnit })} />
          </div>
          <div className="flex flex-col gap-2">
            <Field label={t('onboarding.fpg', 'Fasting glucose')} inputMode="decimal" value={a.fastingGlucose} onChange={(fastingGlucose) => set({ fastingGlucose })} placeholder={a.glucoseUnit === 'mmol/L' ? '7.4' : '133'} error={e.fastingGlucose} />
            <UnitToggle label={t('onboarding.fpgUnit', 'Fasting glucose unit')} options={glucoseUnits} value={a.glucoseUnit} onChange={(glucoseUnit) => set({ glucoseUnit })} />
          </div>
          <Field label={t('onboarding.insulin', 'Fasting insulin (optional)')} inputMode="decimal" suffix="µIU/mL" value={a.fastingInsulin} onChange={(fastingInsulin) => set({ fastingInsulin })} placeholder="11.5" error={e.fastingInsulin} />
        </Group>
      )}

      {step === 8 && <DevicesChoice a={a} set={set} commit={(body) => page.commit(body, null)} readOnly={src.readOnly} error={page.error} />}

      {step === 9 && (
        <Group>
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
        </Group>
      )}

      {step === 10 && (
        <Group>
          <Field label={t('onboarding.contact.name', 'Their name')} value={a.contactName} onChange={(contactName) => set({ contactName })} placeholder={t('onboarding.contact.namePh', 'Next of kin or caregiver')} hint={a.contactName.trim() ? undefined : t('onboarding.contact.needed', 'Needed to continue.')} />
          <Field label={t('onboarding.contact.relation', 'Who they are to you')} value={a.contactRelation} onChange={(contactRelation) => set({ contactRelation })} placeholder={t('onboarding.contact.relationPh', 'For example, wife, son or friend')} hint={a.contactRelation.trim() ? undefined : t('onboarding.contact.needed', 'Needed to continue.')} />
          <Field label={t('onboarding.contact.phone', 'Their mobile number')} type="tel" inputMode="tel" value={a.contactPhone} onChange={(contactPhone) => set({ contactPhone })} placeholder="+65 9123 4567" error={contactProblems.contactPhone} hint={a.contactPhone.trim() ? t('onboarding.contact.phoneHint', 'Digits, with an optional + at the front.') : t('onboarding.contact.needed', 'Needed to continue.')} />
          <Field label={t('onboarding.contact.email', 'Their email')} value={a.contactEmail} onChange={(contactEmail) => set({ contactEmail })} placeholder="name@example.com" error={contactProblems.contactEmail} hint={a.contactEmail.trim() ? undefined : t('onboarding.contact.needed', 'Needed to continue.')} />
          <p className="text-sub text-ink3">{t('onboarding.contact.hintV2', 'Used for safety only. You can change this later in Me, Data and account.')}</p>
        </Group>
      )}

      <Later />
      <Dock onBack={onBack} onNext={onNext} nextDisabled={!continueAnyway && (blocked || page.saving)} nextLabel={continueAnyway ? t('onboarding.continueAnyway', 'Continue anyway') : nextLabel} />
    </Screen>
  )
}

/**
 * Page 9. Choosing a watch or sensor is saved to the record; nothing is paired here. "Connecting…" is shown while the choice is
 * saved. The result says what really happened: the choice is saved and not paired yet, or it was not saved. It never says a
 * device is connected.
 */
function DevicesChoice({ a, set, commit, readOnly, error }: { a: OnboardingAnswers; set: (p: Partial<OnboardingAnswers>) => void; commit: (body: ProfileBody) => Promise<boolean>; readOnly: boolean; error: string | null }) {
  const { t } = useTranslation()
  const opts = useOptions()
  const [state, setState] = useState<'idle' | 'connecting' | 'chosen' | 'later' | 'failed'>(a.wearable || a.cgm ? 'chosen' : 'idle')
  const names = [a.wearable, a.cgm].filter((v): v is string => !!v && v !== 'none').map((v) => labelOf([...opts.wearable, ...opts.cgm], v))
  const hasChoice = names.length > 0
  const connect = async () => {
    setState('connecting')
    const ok = await commit({ watchModel: a.wearable, cgmModel: a.cgm })
    setState(ok ? 'chosen' : 'failed')
  }
  return (
    <>
      <Group title={t('onboarding.cgm.title', 'Glucose sensor (CGM)')}>
        <PickOne label={t('onboarding.cgm.label', 'Which sensor do you use?')} options={opts.cgm} value={a.cgm} onChange={(cgm) => { set({ cgm }); setState('idle') }} />
      </Group>
      <Group title={t('onboarding.wear.title', 'Smart watch')}>
        <PickOne label={t('onboarding.wear.label', 'Which watch do you wear?')} options={opts.wearable} value={a.wearable} onChange={(wearable) => { set({ wearable }); setState('idle') }} />
      </Group>
      <Group title={t('onboarding.connect.title', 'Connect')}>
        {state === 'connecting' && (
          <p className="flex items-center gap-2 text-body font-bold" role="status">
            <span className="h-2 w-2 animate-pulse rounded-full bg-brand" aria-hidden />
            {t('onboarding.connect.connecting', 'Connecting…')}
          </p>
        )}
        {state === 'chosen' && hasChoice && (
          <Alert tone="info">
            {t('onboarding.connect.chosen', 'Chosen: {{names}}. It is not paired yet. You can pair it later in Me, Connected sources.', { names: names.join(', ') })}
          </Alert>
        )}
        {state === 'later' && <Alert tone="info">{t('onboarding.connect.later', 'Not now. You can do this later in Me, Connected sources.')}</Alert>}
        {state === 'failed' && <Alert tone="warn">{error ?? t('onboarding.connect.failed', 'We could not save your choice just now. It is kept on this device.')}</Alert>}
        <div className="flex flex-wrap gap-2">
          <Button disabled={!hasChoice || readOnly || state === 'connecting'} onClick={connect}>
            {t('onboarding.connect.button', 'Connect')}
          </Button>
          <TextLink onClick={() => setState('later')}>{t('onboarding.connect.notNow', 'Not now')}</TextLink>
        </div>
        {readOnly && <p className="text-sub text-ink3">{t('onboarding.connect.demo', 'Mr Tan is demo data, so no choice is saved here.')}</p>}
      </Group>
    </>
  )
}
