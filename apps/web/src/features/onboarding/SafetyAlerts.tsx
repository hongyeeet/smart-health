/**
 * What the person sees when they tick a red-flag symptom in onboarding. Fixed text, no AI, shown the moment the box is
 * ticked (rules.md 1.5). Each message only says where to get help and how soon: it names no condition and says nothing
 * about any medicine (rules.md 1.1 and 1.6).
 *
 * TODO(decision): this wording is Damien's design in plain language and still needs the owner's OK and clinical review
 * (red-flag symptoms are on the "Needs your OK" list; D-054).
 */
import { useTranslation } from 'react-i18next'
import { appConfig } from '@/config/app'
import { Alert } from '@/ui/primitives'
import { Phone } from '@/ui/icons'

export function SafetyAlerts({ flags }: { flags: string[] }) {
  const { t } = useTranslation()
  const urgent = flags.includes('chest') || flags.includes('high_sick')
  if (!urgent && !flags.includes('wound') && !flags.includes('severe_low')) return null
  return (
    <div className="flex flex-col gap-3" role="alert">
      {urgent && (
        <Alert tone="danger" title={t('onboarding.alert.urgentTitle', 'Get help now')}>
          <p>{t('onboarding.alert.urgent', 'Call {{number}} or go to the nearest emergency department. Do not wait to finish this form.', { number: appConfig.emergencyNumber })}</p>
          <a href={`tel:${appConfig.emergencyNumber}`} className="press mt-2 inline-flex min-h-12 items-center gap-2 rounded-field bg-danger px-4 font-bold text-card">
            <Phone size={20} aria-hidden />
            {t('onboarding.alert.call', 'Call {{number}}', { number: appConfig.emergencyNumber })}
          </a>
        </Alert>
      )}
      {flags.includes('wound') && (
        <Alert tone="warn" title={t('onboarding.alert.woundTitle', 'Please have your foot looked at soon')}>
          {t('onboarding.alert.wound', 'See your doctor or a podiatrist in the next 1 to 2 days.')}
        </Alert>
      )}
      {flags.includes('severe_low') && (
        <Alert tone="warn" title={t('onboarding.alert.lowTitle', 'Please tell your doctor about this low')}>
          {t('onboarding.alert.low', 'Contact the doctor who looks after your diabetes soon. Smart Health cannot advise on medicines, but your doctor or pharmacist can.')}
        </Alert>
      )}
    </div>
  )
}
