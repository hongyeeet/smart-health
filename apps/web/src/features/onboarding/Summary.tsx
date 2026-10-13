/**
 * A6 — Your profile summary. An editable read-back of what the person entered, page by page. Edit opens the right page
 * (About you, ?step=3 to 11, with ?review=1 so Continue comes back here).
 *
 * Finish saves every page to the record, records the consent and completion, and goes to Home. If the save fails, the person
 * stays here, the reason is shown, and nothing is said to be saved that was not. Mr Tan (the demo patient) is never written.
 *
 * Damien's Stitch design ends on a clinical target profile with stages, risk tiers and targets. Those are left out:
 * Smart Health does not classify the person or set targets (rules.md 1.1, 1.6, 1.15). What is kept is the read-back, plain
 * arithmetic (age, BMI, unit conversions, no category), and a short list of gaps worth raising with the doctor.
 */
import { dateLocale } from '@/lib/locale'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { href } from '@/app/routeIds'
import { useUi } from '@/state/store'
import { Screen } from '@/ui/layout'
import { Alert, Card, TextLink } from '@/ui/primitives'
import { PencilSimple } from '@/ui/icons'
import { DemoNotice, Dock, Later, LoadNotice, LoadingAnswers, TopBar, clock } from './parts'
import { labelOf, useOptions } from './options'
import { allPagesBody, emailBody, useCompleteOnboarding, useOnboardingSource, useSaveStep } from './api'
import { convert, num, useOnboarding } from './useOnboarding'
import { LAST_PAGE } from './AboutYou'

interface Row {
  label: string
  value: string
}

export function Summary() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const toast = useUi((s) => s.showToast)
  const a = useOnboarding((s) => s.answers)
  const set = useOnboarding((s) => s.set)
  const o = useOptions()
  const src = useOnboardingSource()
  const save = useSaveStep()
  const complete = useCompleteOnboarding()
  /* null when nothing has gone wrong; otherwise the reason, which may be an empty string */
  const [failed, setFailed] = useState<string | null>(null)
  /* the reminder email could not be saved; the person can still finish */
  const [emailNote, setEmailNote] = useState(false)

  if (!src.ready) {
    return (
      <Screen narrow>
        <TopBar />
        <LoadingAnswers />
      </Screen>
    )
  }

  const on = t('onboarding.sum.on', 'On')
  const off = t('onboarding.sum.off', 'Off')
  const unit = (v: string, u: string) => (v.trim() ? `${v.trim()} ${u}` : '')
  const list = (xs: string[]) => xs.filter(Boolean).join(', ')
  const many = <T extends string>(options: { value: T; label: string }[], values: T[]) => list(values.map((v) => labelOf(options, v)))
  const step = (n: number) => `${href('A3')}?step=${n}&review=1`
  const date = (iso: string) => (iso ? new Date(`${iso}T00:00:00`).toLocaleDateString(dateLocale('en-SG'), { day: 'numeric', month: 'short', year: 'numeric' }) : '')
  const working = a.workType !== null && a.workType !== 'not_working'

  /* the reminder email as the server holds it. The box on the device is not what is saved until the server has it. */
  const serverEmail = src.email.data?.email ?? null
  const typedEmail = a.reminderEmail.trim()
  const savedEmailLine = src.email.isError
    ? t('onboarding.sum.emailUnknown', 'Could not check it just now')
    : typedEmail !== (serverEmail ?? '')
      ? serverEmail
        ? `${serverEmail}. ${t('onboarding.sum.notSavedYet', 'Not saved yet')}`
        : t('onboarding.sum.notSavedYet', 'Not saved yet')
      : (serverEmail ?? '')

  const sections: { title: string; edit: string; rows: Row[] }[] = [
    {
      title: t('onboarding.welcome.step', 'Welcome'),
      edit: `${href('A1')}?review=1`,
      rows: [
        { label: t('onboarding.sum.name', 'Name'), value: a.name.trim() },
        { label: t('onboarding.email.label', 'Email for reminders'), value: savedEmailLine },
        { label: t('onboarding.email.on', 'Send me reminder emails'), value: a.reminderOn ? on : off },
        { label: t('onboarding.consent.data', 'Use my health data'), value: a.consentData ? on : off },
        { label: t('onboarding.consent.share', 'Share a doctor brief'), value: a.consentShare ? on : off },
        { label: t('onboarding.consent.research', 'Use my data for research'), value: a.consentResearch ? on : off },
      ],
    },
    {
      title: t('onboarding.s3.name', 'About you'),
      edit: step(3),
      rows: [
        { label: t('onboarding.birthYear', 'Year of birth'), value: a.birthYear.trim() },
        { label: t('onboarding.gender.label', 'Sex'), value: labelOf(o.gender, a.gender) },
        { label: t('onboarding.race.label', 'Ethnic group'), value: a.race.trim() ? labelOf(o.race, a.race.trim()) : '' },
        { label: t('onboarding.height', 'Height'), value: unit(a.heightCm, 'cm') },
        { label: t('onboarding.weight', 'Weight'), value: unit(a.weightKg, 'kg') },
        { label: t('onboarding.sum.waist', 'Waist'), value: unit(a.waistCm, 'cm') },
      ],
    },
    {
      title: t('onboarding.s4.name', 'Diabetes history'),
      edit: step(4),
      rows: [
        { label: t('onboarding.sum.diagYear', 'Year of diagnosis'), value: a.diagnosedYear.trim() },
        { label: t('onboarding.sum.care', 'Usual place of care'), value: labelOf(o.careSetting, a.careSetting) },
        { label: t('onboarding.sum.hsg', 'Healthier SG'), value: labelOf(o.healthierSg, a.healthierSg) },
      ],
    },
    {
      title: t('onboarding.s6.name', 'Low glucose'),
      edit: step(5),
      rows: [
        { label: t('onboarding.sum.hypo3m', 'Hypos in the last 3 months'), value: labelOf(o.hypo3m, a.hypo3m) },
        { label: t('onboarding.sum.severe', 'Needed help with a hypo in the last 12 months'), value: labelOf(o.yesNo, a.severeHypo) },
        { label: t('onboarding.sum.goldV2', 'Knows when a hypo is starting (1 always, 5 never)'), value: a.gold ?? '' },
      ],
    },
    {
      title: t('onboarding.s7.name', 'Other conditions and checks'),
      edit: step(5),
      rows: [
        { label: t('onboarding.sum.conditions', 'Conditions'), value: list([...a.conditions.map((c) => labelOf(o.conditions, c)), a.otherConditions.trim()]) },
        {
          label: t('onboarding.allergy.label', 'Allergies'),
          value: a.noAllergies ? t('onboarding.sum.noAllergies', 'No known allergies') : list(a.allergies.filter((x) => x.substance.trim()).map((x) => (x.reaction.trim() ? `${x.substance.trim()} (${x.reaction.trim()})` : x.substance.trim()))),
        },
        { label: t('onboarding.sum.eye', 'Last eye check'), value: labelOf(o.lastCheck, a.eyeCheck) },
        { label: t('onboarding.sum.foot', 'Last foot check'), value: labelOf(o.lastCheck, a.footCheck) },
      ],
    },
    {
      title: t('onboarding.s8.name', 'Lab results'),
      edit: step(5),
      rows: [
        { label: t('onboarding.sum.labDate', 'Date of the blood test'), value: date(a.labDate) },
        { label: t('onboarding.hba1c', 'HbA1c'), value: unit(a.hba1c, a.hba1cUnit) },
        { label: t('onboarding.fpg', 'Fasting glucose'), value: unit(a.fastingGlucose, a.glucoseUnit) },
        { label: t('onboarding.sum.insulin', 'Fasting insulin'), value: unit(a.fastingInsulin, 'µIU/mL') },
      ],
    },
    {
      title: t('onboarding.s9.name', 'Devices'),
      edit: step(5),
      rows: [
        { label: t('onboarding.sum.watch', 'Smart watch'), value: labelOf(o.wearable, a.wearable) },
        { label: t('onboarding.sum.cgm', 'Glucose sensor'), value: labelOf(o.cgm, a.cgm) },
      ],
    },
    {
      title: t('onboarding.s10.name', 'Your work week'),
      edit: step(5),
      rows: [
        { label: t('onboarding.sum.work', 'Work'), value: labelOf(o.work, a.workType) },
        { label: t('onboarding.sum.workDays', 'Work days'), value: working ? many(o.weekdays, a.workDays.map(String)) : '' },
        { label: t('onboarding.sum.workHours', 'Work hours'), value: working && a.workStart && a.workEnd ? `${clock(a.workStart)} to ${clock(a.workEnd)}` : '' },
      ],
    },
    {
      title: t('onboarding.s11.name', 'Emergency contact'),
      edit: step(LAST_PAGE),
      rows: [
        { label: t('onboarding.contact.name', 'Their name'), value: a.contactName.trim() },
        { label: t('onboarding.contact.relation', 'Who they are to you'), value: a.contactRelation.trim() },
        { label: t('onboarding.contact.phone', 'Their mobile number'), value: a.contactPhone.trim() },
        { label: t('onboarding.contact.email', 'Their email'), value: a.contactEmail.trim() },
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

  /* Finish saves every page, then records the consent and completion. Nothing is shown as saved until the server has said so. */
  const finish = async () => {
    if (src.readOnly) {
      toast(t('onboarding.sum.demoDone', 'Mr Tan is demo data, so nothing was saved to his record.'))
      navigate(href('B1'), { replace: true })
      return
    }
    /* the saved answers must be read first: a save from a device copy alone could blank what the record holds */
    if (src.loadFailed) {
      setFailed(t('onboarding.sum.noRead', 'Your saved answers could not be read, so Finish cannot save right now. Check your connection, then tap Finish again.'))
      return
    }
    setFailed(null)
    setEmailNote(false)
    try {
      /* the reminder email is sent only when its saved value is known (or the box has something), so it is never cleared by mistake */
      const email = src.email.isSuccess || a.reminderEmail.trim() ? emailBody(a) : null
      const res = await save.mutateAsync({ profile: allPagesBody(a, !src.saved.data?.profile), email })
      /* the profile was just saved, so a waiting email should not happen; if it does, the person stays here and is told */
      if (res.email === 'waiting') {
        setFailed(t('onboarding.email.waiting', 'We will save your email when your profile is created. It is kept on this device until then.'))
        return
      }
      if (res.email === 'failed') setEmailNote(true)
      await complete.mutateAsync()
    } catch (err) {
      setFailed(err instanceof Error ? err.message : '')
      return
    }
    set({ completedAt: new Date().toISOString() })
    toast(t('onboarding.sum.done', 'Setup finished'))
    navigate(href('B1'), { replace: true })
  }

  const savedAt = src.saved.data?.profile?.updatedAt
  const savedLine = src.readOnly
    ? t('onboarding.sum.demo', 'Mr Tan is demo data. Nothing you see here is saved to his record.')
    : savedAt
      ? t('onboarding.sum.savedAt', 'Your record was last saved on {{date}}.', { date: new Date(savedAt).toLocaleString(dateLocale('en-SG'), { day: 'numeric', month: 'short', year: 'numeric', hour: 'numeric', minute: '2-digit' }) })
      : t('onboarding.sum.notSaved', 'Not saved to your record yet. Tap Finish to save it.')

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
    <Screen narrow>
      <TopBar />
      <div>
        <p className="text-sub font-bold text-brand">{t('onboarding.sum.step', 'All steps done')}</p>
        <h1 className="mt-1 break-words font-serif text-h1 font-medium tracking-tight text-ink">{title}</h1>
        <p className="mt-1.5 text-sub text-ink2">{t('onboarding.sum.sub', 'This is what you told us. Change anything that is not right.')}</p>
      </div>

      {src.loadFailed && <LoadNotice />}
      {src.readOnly && <DemoNotice />}

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

      <Alert tone="info">
        <p>{savedLine}</p>
        {!src.readOnly && src.saved.data && !src.saved.data.historyReady && (
          <p className="mt-1.5">{t('onboarding.sum.local', 'Some answers, such as the diabetes history and the lab results, are kept on this device for now.')}</p>
        )}
      </Alert>
      {emailNote && <Alert tone="warn">{t('onboarding.email.notSavedV2', 'We could not save your reminder email just now. It is kept on this device. You can add it later in Me, Data and account.')}</Alert>}
      {failed !== null && (
        <Alert tone="danger">
          <p>{t('onboarding.sum.failed', 'Setup is not finished yet. Your answers are still on this device. Fix the point below, or check your connection, then tap Finish again.')}</p>
          {failed && <p className="mt-1.5">{failed}</p>}
        </Alert>
      )}
      <p className="text-center text-sub text-ink3">{t('onboarding.sum.fine', 'Smart Health explains, organises and reminds. It is not a diagnosis and does not replace your doctor.')}</p>

      <Later />
      <Dock onBack={() => navigate(step(LAST_PAGE))} onNext={finish} nextDisabled={save.isPending || complete.isPending} nextLabel={t('onboarding.sum.finish', 'Finish')} />
    </Screen>
  )
}
