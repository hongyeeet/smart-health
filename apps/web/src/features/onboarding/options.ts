import { useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import type { Gender, LastCheck, WorkType, YesNo, YesNoUnsure } from './useOnboarding'
import type { Option } from './parts'

/** The "Others" choice for the ethnic group. It is never saved: the word the person types in its box is what is saved. */
export const RACE_OTHERS = 'Others'

/**
 * Every answer list in onboarding, in one place, so the form and the summary always show the same words. The lists are in
 * plain language. The second line of an answer only helps the person recognise it (a brand name, what a condition is called).
 * It never says what a medicine or a condition does to them (rules.md 1.9).
 */
export function useOptions() {
  const { t } = useTranslation()
  return useMemo(() => {
    const yes = t('common.yes', 'Yes')
    const no = t('common.no', 'No')
    const notSure = t('common.notSure', 'Not sure')

    /** Sex: male or female only. Older answers with another value are treated as not answered (see useOnboarding). */
    const gender: Option<Gender>[] = [
      { value: 'female', label: t('onboarding.gender.female', 'Female') },
      { value: 'male', label: t('onboarding.gender.male', 'Male') },
    ]
    /** Suggestions only: ethnic group is free text in the data model, so the stored value is the word itself. */
    const race: Option<string>[] = [
      { value: 'Chinese', label: t('onboarding.race.chinese', 'Chinese') },
      { value: 'Malay', label: t('onboarding.race.malay', 'Malay') },
      { value: 'Indian', label: t('onboarding.race.indian', 'Indian') },
      { value: RACE_OTHERS, label: t('onboarding.race.others', 'Others') },
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
    const healthierSg: Option<YesNoUnsure>[] = [
      { value: 'yes', label: t('onboarding.hsg.yes', 'Enrolled') },
      { value: 'no', label: t('onboarding.hsg.no', 'Not enrolled') },
      { value: 'unsure', label: notSure },
    ]
    const hypo3m: Option<string>[] = [
      { value: '0', label: t('onboarding.hypo.none', 'None') },
      { value: '1-2', label: t('onboarding.hypo.few', '1 or 2 times') },
      { value: '3+', label: t('onboarding.hypo.many', '3 times or more') },
      { value: 'unsure', label: notSure },
    ]
    const conditions: Option<string>[] = [
      { value: 'hypertension', label: t('onboarding.cond.hypertension', 'High blood pressure') },
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

    return { gender, race, yesNo, yesNoUnsure, careSetting, healthierSg, hypo3m, conditions, lastCheck, cgm, wearable, work, weekdays }
  }, [t])
}

/** The label for a stored value, or the value itself if the list no longer has it. */
export function labelOf<T extends string>(options: Option<T>[], value: T | null): string {
  return options.find((o) => o.value === value)?.label ?? value ?? ''
}
