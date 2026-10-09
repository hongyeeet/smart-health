/**
 * A1 — Welcome. Preferred name, language and the consents. Nothing is kept on the device until the data-use consent is on,
 * and the person cannot go further without it (prd F1).
 */
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { appConfig } from '@/config/app'
import { href } from '@/app/routeIds'
import { useSwitchUser } from '@/data/hooks'
import { useUi } from '@/state/store'
import type { Locale } from '@/data/types'
import { Screen } from '@/ui/layout'
import { Field, TextLink, Toggle } from '@/ui/primitives'
import { Dock, Group, PickOne, StepHead, TopBar, useStepNav, type Option } from './parts'
import { useOnboarding } from './useOnboarding'

/** The seeded persona with about 90 days of history (see UserSwitch). */
const DEMO_PATIENT = 'mr-tan'

export function Welcome() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { review, next } = useStepNav()
  const { locale, setLocale } = useUi()
  const switchUser = useSwitchUser()
  const a = useOnboarding((s) => s.answers)
  const set = useOnboarding((s) => s.set)

  const languages: Option<Locale>[] = appConfig.locales.map((l) => ({ value: l.code, label: l.native }))
  const consents = [
    { key: 'consentData' as const, title: t('onboarding.consent.data', 'Use my health data'), sub: t('onboarding.consent.dataSub', 'Required. I agree to Smart Health collecting and using the health information I enter and the readings from my devices.') },
    { key: 'consentShare' as const, title: t('onboarding.consent.share', 'Share a doctor brief'), sub: t('onboarding.consent.shareSub', 'Optional. You decide each time.') },
    { key: 'consentResearch' as const, title: t('onboarding.consent.research', 'Use my data for research'), sub: t('onboarding.consent.researchSub', 'Optional. For diabetes research, without my name or contact details.') },
  ]

  return (
    <Screen>
      <TopBar />
      <StepHead
        step={1}
        name={t('onboarding.welcome.step', 'Welcome')}
        title={t('onboarding.welcome.title', 'Set up Smart Health for you')}
        sub={t('onboarding.welcome.sub', 'It takes about 5 minutes. Your answers help Smart Health follow your days and prepare a clear summary for your doctor. It never gives medical advice and never diagnoses.')}
      />

      <Group>
        <Field label={t('onboarding.name', 'What should we call you?')} value={a.name} onChange={(name) => set({ name })} placeholder={t('onboarding.namePlaceholder', 'For example, Mr Tan')} />
        <PickOne label={t('onboarding.language', 'Language')} hint={t('onboarding.languageHint', 'Most screens are in English for now.')} options={languages} value={locale} onChange={(v) => v && setLocale(v)} />
      </Group>

      <Group title={t('onboarding.consent.title', 'Privacy and consent')}>
        <div className="flex flex-col divide-y divide-line">
          {consents.map((c) => (
            <div key={c.key} className="flex items-start justify-between gap-4 py-3 first:pt-0 last:pb-0">
              <div className="min-w-0">
                <p className="text-body font-bold">{c.title}</p>
                <p className="text-sub text-ink2">{c.sub}</p>
              </div>
              <Toggle on={a[c.key]} onChange={(v) => set({ [c.key]: v })} label={c.title} />
            </div>
          ))}
        </div>
      </Group>

      <Dock onNext={() => next(href('A2'))} nextDisabled={!a.consentData} nextLabel={review ? t('onboarding.backToSummary', 'Back to summary') : t('common.continue', 'Continue')}>
        {!review && (
          <TextLink
            onClick={() => {
              switchUser(DEMO_PATIENT)
              navigate(href('B1'))
            }}
            className="self-center"
          >
            {t('onboarding.demo', 'Start as demo patient')}
          </TextLink>
        )}
      </Dock>
    </Screen>
  )
}
