/**
 * A1 — Welcome (page 1 of 10). Your name, the email address for reminders (needed to continue; the reminder on/off switch stays) and the consents. There is no
 * language choice. Nothing is kept on the device until the data-use consent is on, and the person cannot go further without it
 * (prd F1).
 */
import { useTranslation } from 'react-i18next'
import { href } from '@/app/routeIds'
import { Screen } from '@/ui/layout'
import { Alert, Field, Toggle } from '@/ui/primitives'
import { DemoNotice, Dock, Group, Later, LoadNotice, LoadingAnswers, StepHead, TopBar, useStepNav } from './parts'
import { emailBody, pageBody, useOnboardingSource } from './api'
import { usePageSave } from './usePageSave'
import { emailOk, useOnboarding } from './useOnboarding'

export function Welcome() {
  const { t } = useTranslation()
  const { review, next } = useStepNav()
  const a = useOnboarding((s) => s.answers)
  const set = useOnboarding((s) => s.set)
  const src = useOnboardingSource()
  const page = usePageSave(src.loadFailed)

  const consents = [
    { key: 'consentData' as const, title: t('onboarding.consent.data', 'Use my health data'), sub: t('onboarding.consent.dataSub', 'Required. I agree to Smart Health collecting and using the health information I enter and the readings from my devices.') },
    { key: 'consentShare' as const, title: t('onboarding.consent.share', 'Share a doctor brief'), sub: t('onboarding.consent.shareSub', 'Optional. You decide each time.') },
    { key: 'consentResearch' as const, title: t('onboarding.consent.research', 'Use my data for research'), sub: t('onboarding.consent.researchSub', 'Optional. For diabetes research, without my name or contact details.') },
  ]

  if (!src.ready) {
    return (
      <Screen narrow>
        <TopBar />
        <LoadingAnswers />
      </Screen>
    )
  }

  const emailTyped = a.reminderEmail.trim() !== ''
  const emailBad = emailTyped && !emailOk(a.reminderEmail)
  const blocked = !a.consentData || !emailTyped || emailBad       // the address is needed: reminders are sent by email
  const stored = src.email.data
  /* the email and the switch are saved only when they differ from what the server holds */
  const emailChanged = (a.reminderEmail.trim() || null) !== (stored?.email ?? null) || a.reminderOn !== (stored?.optIn ?? true)
  const continueAnyway = page.holding

  const onNext = async () => {
    if (!page.holding) {
      /* the name is saved once the profile exists (page 3 creates it), so a first save never fails for a missing birth year */
      const profile = src.saved.data?.profile ? pageBody(1, a, false) : null
      /* without a profile, an email is sent only when there is an address: a switch alone waits for the first save (page 3) */
      const emailNow = emailChanged && (src.saved.data?.profile || emailTyped) ? emailBody(a) : null
      const ok = await page.commit(profile, emailNow)
      if (!ok) return
    }
    next(href('A2'))
  }

  return (
    <Screen narrow>
      <TopBar />
      <StepHead
        step={1}
        name={t('onboarding.welcome.step', 'Welcome')}
        title={t('onboarding.welcome.title', 'Set up Smart Health for you')}
        sub={t('onboarding.welcome.sub', 'It takes about 5 minutes. Your answers help Smart Health follow your days and prepare a clear summary for your doctor. It never gives medical advice and never diagnoses.')}
      />
      {src.loadFailed && <LoadNotice />}
      {src.readOnly && <DemoNotice />}
      {page.error && <Alert tone="danger">{page.error}</Alert>}
      {page.notice && <Alert tone="info">{page.notice}</Alert>}

      <Group>
        <Field label={t('onboarding.name', 'What should we call you?')} value={a.name} onChange={(name) => set({ name })} placeholder={t('onboarding.namePlaceholder', 'For example, Mr Tan')} />
        <Field
          label={t('onboarding.email.labelV2', 'Email address')}
          value={a.reminderEmail}
          onChange={(reminderEmail) => set({ reminderEmail })}
          placeholder="name@example.com"
          error={emailBad ? t('onboarding.err.emailV2', 'Enter an email address like name@example.com.') : undefined}
          hint={emailBad ? undefined : t('onboarding.email.hintV2', 'We email a gentle reminder when something is due, like logging a meal.')}
        />
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <p className="text-body font-bold">{t('onboarding.email.on', 'Send me reminder emails')}</p>
            <p className="text-sub text-ink2">{t('onboarding.email.onSubV2', 'You can turn this off any time in Me, Data and account.')}</p>
          </div>
          <Toggle on={a.reminderOn} onChange={(reminderOn) => set({ reminderOn })} label={t('onboarding.email.on', 'Send me reminder emails')} />
        </div>
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

      <Later label={t('onboarding.goHome', 'Go to Home')} />
      <Dock onNext={onNext} nextDisabled={blocked || page.saving} nextLabel={continueAnyway ? t('onboarding.continueAnyway', 'Continue anyway') : review ? t('onboarding.backToSummary', 'Back to summary') : t('common.continue', 'Continue')} />
    </Screen>
  )
}
