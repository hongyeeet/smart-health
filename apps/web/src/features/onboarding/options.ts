import { useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import type { Gender, LastCheck, WorkType, YesNo, YesNoUnsure } from './useOnboarding'
import type { Option } from './parts'

/**
 * Every answer list in onboarding, in one place, so the form and the summary always show the same words.
 *
 * The lists follow Damien's clinical onboarding design, reworded in plain language for the person filling it in.
 * The second line of an answer is only a name or example that helps the person recognise it (a brand name, what the
 * condition is called). It never says what a medicine or condition does to them: that would be health content with no
 * cited source (rules.md 1.9).
 */
export function useOptions() {
  const { t } = useTranslation()
  return useMemo(() => {
    const yes = t('common.yes', 'Yes')
    const no = t('common.no', 'No')
    const notSure = t('common.notSure', 'Not sure')

    const gender: Option<Gender>[] = [
      { value: 'female', label: t('onboarding.gender.female', 'Female') },
      { value: 'male', label: t('onboarding.gender.male', 'Male') },
      { value: 'other', label: t('onboarding.gender.other', 'Other') },
      { value: 'prefer_not_to_say', label: t('onboarding.gender.undisclosed', 'Prefer not to say') },
    ]
    /** Suggestions only: race is free text in the data model, so the stored value is the word itself. */
    const race: Option<string>[] = [
      { value: 'Chinese', label: t('onboarding.race.chinese', 'Chinese') },
      { value: 'Malay', label: t('onboarding.race.malay', 'Malay') },
      { value: 'Indian', label: t('onboarding.race.indian', 'Indian') },
    ]
    const yesNo: Option<YesNo>[] = [
      { value: 'yes', label: yes },
      { value: 'no', label: no },
    ]
    const yesNoUnsure: Option<YesNoUnsure>[] = [
      { value: 'yes', label: yes },
      { value: 'no', label: no },
      { value: 'unsure', label: notSure },
    ]
    const careSetting: Option<string>[] = [
      { value: 'polyclinic', label: t('onboarding.care.polyclinic', 'Polyclinic') },
      { value: 'gp', label: t('onboarding.care.gp', 'GP or family clinic') },
      { value: 'hospital', label: t('onboarding.care.hospital', 'Hospital specialist clinic') },
      { value: 'none', label: t('onboarding.care.none', 'No regular doctor') },
    ]
    const healthierSg: Option<string>[] = [
      { value: 'yes', label: t('onboarding.hsg.yes', 'Enrolled') },
      { value: 'no', label: t('onboarding.hsg.no', 'Not enrolled') },
      { value: 'unsure', label: notSure },
    ]

    const diabetesMeds: Option<string>[] = [
      { value: 'metformin', label: t('onboarding.med.metformin', 'Metformin'), sub: 'Glucophage' },
      { value: 'sulfonylurea', label: t('onboarding.med.su', 'Sulfonylurea'), sub: t('onboarding.med.suSub', 'Gliclazide, glimepiride, tolbutamide') },
      { value: 'dpp4', label: t('onboarding.med.dpp4', 'DPP-4 inhibitor'), sub: t('onboarding.med.dpp4Sub', 'Sitagliptin, linagliptin (Januvia, Trajenta)') },
      { value: 'sglt2', label: t('onboarding.med.sglt2', 'SGLT2 inhibitor'), sub: t('onboarding.med.sglt2Sub', 'Empagliflozin, dapagliflozin (Jardiance, Forxiga)') },
      { value: 'glp1', label: t('onboarding.med.glp1', 'GLP-1 injection or tablet'), sub: t('onboarding.med.glp1Sub', 'Semaglutide, dulaglutide (Ozempic, Trulicity)') },
      { value: 'tzd', label: t('onboarding.med.tzd', 'Pioglitazone') },
      { value: 'acarbose', label: t('onboarding.med.acarbose', 'Acarbose'), sub: 'Glucobay' },
      { value: 'basal_insulin', label: t('onboarding.med.basal', 'Long-acting insulin'), sub: t('onboarding.med.basalSub', 'Glargine, degludec (Lantus, Tresiba)') },
      { value: 'bolus_insulin', label: t('onboarding.med.bolus', 'Mealtime insulin'), sub: t('onboarding.med.bolusSub', 'Aspart, lispro (NovoRapid, Humalog)') },
      { value: 'premix_insulin', label: t('onboarding.med.premix', 'Premixed insulin'), sub: t('onboarding.med.premixSub', 'Mixtard, Humalog Mix') },
      { value: 'none', label: t('onboarding.med.none', 'No diabetes medicine'), sub: t('onboarding.med.noneSub', 'Food and activity only') },
    ]
    const otherMeds: Option<string>[] = [
      { value: 'bp', label: t('onboarding.omed.bp', 'Blood pressure medicine'), sub: t('onboarding.omed.bpSub', 'For example amlodipine, losartan, enalapril') },
      { value: 'beta_blocker', label: t('onboarding.omed.bb', 'Beta-blocker'), sub: t('onboarding.omed.bbSub', 'Atenolol, bisoprolol') },
      { value: 'statin', label: t('onboarding.omed.statin', 'Cholesterol medicine (statin)'), sub: t('onboarding.omed.statinSub', 'Atorvastatin, rosuvastatin') },
      { value: 'steroid', label: t('onboarding.omed.steroid', 'Steroid tablets'), sub: t('onboarding.omed.steroidSub', 'Prednisolone') },
      { value: 'antiplatelet', label: t('onboarding.omed.antiplatelet', 'Blood thinner (antiplatelet)'), sub: t('onboarding.omed.antiplateletSub', 'Aspirin, clopidogrel') },
      { value: 'none', label: t('onboarding.omed.none', 'None of these') },
    ]

    const hypo3m: Option<string>[] = [
      { value: '0', label: t('onboarding.hypo.none', 'None') },
      { value: '1-2', label: t('onboarding.hypo.few', '1 or 2 times') },
      { value: '3+', label: t('onboarding.hypo.many', '3 times or more') },
      { value: 'unsure', label: notSure },
    ]

    const conditions: Option<string>[] = [
      { value: 'hypertension', label: t('onboarding.cond.hypertension', 'High blood pressure'), sub: t('onboarding.cond.hypertensionSub', 'Hypertension') },
      { value: 'high_cholesterol', label: t('onboarding.cond.cholesterol', 'High cholesterol') },
      { value: 'kidney', label: t('onboarding.cond.kidney', 'Kidney disease'), sub: t('onboarding.cond.kidneySub', 'Or protein in the urine') },
      { value: 'heart', label: t('onboarding.cond.heart', 'Heart disease or a past heart attack') },
      { value: 'stroke', label: t('onboarding.cond.stroke', 'Stroke or mini-stroke') },
      { value: 'heart_failure', label: t('onboarding.cond.heartFailure', 'Heart failure') },
      { value: 'eye', label: t('onboarding.cond.eye', 'Diabetic eye disease'), sub: t('onboarding.cond.eyeSub', 'Retinopathy') },
      { value: 'nerve', label: t('onboarding.cond.nerve', 'Nerve problems in the feet'), sub: t('onboarding.cond.nerveSub', 'Numbness, tingling or pins and needles') },
      { value: 'foot_ulcer', label: t('onboarding.cond.footUlcer', 'A past foot ulcer or amputation') },
      { value: 'sleep_apnoea', label: t('onboarding.cond.sleepApnoea', 'Sleep apnoea') },
      { value: 'fatty_liver', label: t('onboarding.cond.fattyLiver', 'Fatty liver') },
      { value: 'anaemia', label: t('onboarding.cond.anaemia', 'Anaemia or thalassaemia') },
      { value: 'none', label: t('onboarding.cond.none', 'None of these') },
    ]
    const lastCheck: Option<LastCheck>[] = [
      { value: 'within_year', label: t('onboarding.check.withinYear', 'In the last year') },
      { value: 'over_year', label: t('onboarding.check.overYear', 'More than a year ago') },
      { value: 'never_unsure', label: t('onboarding.check.never', 'Never or not sure') },
    ]

    const cgm: Option<string>[] = [
      { value: 'libre', label: 'Abbott FreeStyle Libre' },
      { value: 'dexcom', label: 'Dexcom' },
      { value: 'other', label: t('onboarding.cgm.other', 'Another sensor') },
      { value: 'none', label: t('onboarding.cgm.none', 'No glucose sensor') },
    ]
    const wearable: Option<string>[] = [
      { value: 'apple', label: 'Apple Watch' },
      { value: 'garmin', label: 'Garmin' },
      { value: 'samsung', label: 'Samsung Galaxy Watch' },
      { value: 'fitbit', label: 'Fitbit' },
      { value: 'xiaomi', label: 'Xiaomi' },
      { value: 'other', label: t('onboarding.wear.other', 'Another watch') },
      { value: 'none', label: t('onboarding.wear.none', 'No watch') },
    ]
    const work: Option<WorkType>[] = [
      { value: 'desk', label: t('onboarding.work.desk', 'Mostly sitting') },
      { value: 'standing', label: t('onboarding.work.standing', 'Mostly standing') },
      { value: 'physical', label: t('onboarding.work.physical', 'Physical work') },
      { value: 'mixed', label: t('onboarding.work.mixed', 'A mix') },
      { value: 'shift', label: t('onboarding.work.shift', 'Shifts or nights') },
      { value: 'not_working', label: t('onboarding.work.notWorking', 'Retired or not working') },
    ]
    const weekdays: Option<string>[] = [
      { value: '1', label: t('common.day.mon', 'Mon') },
      { value: '2', label: t('common.day.tue', 'Tue') },
      { value: '3', label: t('common.day.wed', 'Wed') },
      { value: '4', label: t('common.day.thu', 'Thu') },
      { value: '5', label: t('common.day.fri', 'Fri') },
      { value: '6', label: t('common.day.sat', 'Sat') },
      { value: '7', label: t('common.day.sun', 'Sun') },
    ]
    const fasting: Option<string>[] = [
      { value: 'ramadan', label: t('onboarding.fast.ramadan', 'Ramadan') },
      { value: 'religious', label: t('onboarding.fast.religious', 'Other religious fasts') },
      { value: 'intermittent', label: t('onboarding.fast.intermittent', 'Intermittent fasting') },
      { value: 'none', label: t('onboarding.fast.none', 'No regular fasting') },
    ]

    const eatOut: Option<string>[] = [
      { value: '0-3', label: t('onboarding.eat.a', '0 to 3 meals') },
      { value: '4-7', label: t('onboarding.eat.b', '4 to 7 meals') },
      { value: '8-14', label: t('onboarding.eat.c', '8 to 14 meals') },
      { value: '15+', label: t('onboarding.eat.d', '15 or more') },
    ]
    const sweetDrinks: Option<string>[] = [
      { value: '0', label: t('onboarding.sweet.a', 'None') },
      { value: '1', label: t('onboarding.sweet.b', '1 a day') },
      { value: '2', label: t('onboarding.sweet.c', '2 a day') },
      { value: '3+', label: t('onboarding.sweet.d', '3 or more') },
    ]
    const activeDays: Option<string>[] = [
      { value: '0', label: t('onboarding.active.a', 'No days') },
      { value: '1-2', label: t('onboarding.active.b', '1 or 2 days') },
      { value: '3-4', label: t('onboarding.active.c', '3 or 4 days') },
      { value: '5+', label: t('onboarding.active.d', '5 days or more') },
    ]
    const smoking: Option<string>[] = [
      { value: 'never', label: t('onboarding.smoke.never', 'Never') },
      { value: 'former', label: t('onboarding.smoke.former', 'I used to') },
      { value: 'current', label: t('onboarding.smoke.current', 'Yes, including vaping') },
    ]
    const alcohol: Option<string>[] = [
      { value: 'none', label: t('onboarding.alcohol.none', 'None') },
      { value: 'occasional', label: t('onboarding.alcohol.occasional', 'Now and then') },
      { value: 'weekly', label: t('onboarding.alcohol.weekly', 'Most weeks') },
      { value: 'daily', label: t('onboarding.alcohol.daily', 'Most days') },
    ]

    const redFlags: Option<string>[] = [
      { value: 'chest', label: t('onboarding.red.chest', 'Chest pressure, shortness of breath or a pounding heartbeat') },
      { value: 'high_sick', label: t('onboarding.red.highSick', 'Very high glucose with vomiting, fast breathing, drowsiness or confusion') },
      { value: 'wound', label: t('onboarding.red.wound', 'A foot wound or ulcer that is not healing, or skin turning black') },
      { value: 'severe_low', label: t('onboarding.red.severeLow', 'A severe low in the last 7 days that needed emergency help') },
      { value: 'none', label: t('onboarding.red.none', 'None of these right now') },
    ]

    return { gender, race, yesNo, yesNoUnsure, careSetting, healthierSg, diabetesMeds, otherMeds, hypo3m, conditions, lastCheck, cgm, wearable, work, weekdays, fasting, eatOut, sweetDrinks, activeDays, smoking, alcohol, redFlags }
  }, [t])
}

export const REMINDER_TIMES = ['07:00', '08:00', '13:00', '19:30', '20:00', '22:00']

/** The label for a stored value, or the value itself if the list no longer has it. */
export function labelOf<T extends string>(options: Option<T>[], value: T | null): string {
  return options.find((o) => o.value === value)?.label ?? value ?? ''
}
