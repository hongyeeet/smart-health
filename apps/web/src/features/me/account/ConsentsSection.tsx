/**
 * "Consents": a switch for each thing the person lets Smart Health do. Turning off "Use my health data" asks first (it stops the app
 * working). "Allow reminder notifications" is the reminder email switch (GET/PUT /notify/email): reminders for medicines and for logs such
 * as food and exercise are sent by email; "Change email address" sits under it. Turning one off does not delete any data.
 */
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useUi } from '@/state/store'
import { Sheet } from '@/ui/Sheet'
import { Alert, Button, Card, Field, SectionTitle, Skeleton, Toggle } from '@/ui/primitives'
import { emailError } from '../settings/rules'
import { useConsents, useEmailReminders, useSaveEmailReminders, useSetConsent, type ConsentKind } from '../settings/api'

export function ConsentsSection() {
  const { t } = useTranslation()
  const consents = useConsents()
  const setConsent = useSetConsent()
  const email = useEmailReminders()
  const saveEmail = useSaveEmailReminders()
  const showToast = useUi((s) => s.showToast)
  const [askOff, setAskOff] = useState<ConsentKind | null>(null)
  const [changing, setChanging] = useState(false)

  const ROWS: { kind: ConsentKind; title: string; sub: string; required?: boolean }[] = [
    {
      kind: 'data_processing',
      title: t('me.privacy.dataTitle', 'Use my health data'),
      sub: t('me.privacy.dataSub', 'Lets Smart Health read what you log and what your devices send, so it can show your insights, reminders and doctor brief.'),
      required: true,
    },
    {
      kind: 'brief_sharing',
      title: t('me.privacy.briefTitle', 'Share my doctor brief'),
      sub: t('me.privacy.briefSub', 'Lets you make a link to your doctor brief. You choose each time, and you can turn a link off.'),
    },
    {
      kind: 'caregiver_view',
      title: t('me.privacy.caregiverTitle', 'Let a caregiver see my data'),
      sub: t('me.privacy.caregiverSub', 'Lets someone you choose view your readings and summaries.'),
    },
    {
      kind: 'research_use',
      title: t('me.privacy.researchTitle', 'Use my data for research'),
      sub: t('me.privacy.researchSub', 'Optional. Never includes your name.'),
    },
  ]

  const apply = (kind: ConsentKind, granted: boolean) =>
    setConsent.mutate(
      { kind, granted },
      {
        onSuccess: () => {
          setAskOff(null)
          showToast(granted ? t('me.privacy.turnedOn', 'Turned on') : t('me.privacy.turnedOff', 'Turned off'))
        },
      },
    )

  const change = (kind: ConsentKind, granted: boolean) => {
    // Turning off the data-use consent stops the app working, so it is confirmed first.
    if (!granted && kind === 'data_processing') setAskOff(kind)
    else apply(kind, granted)
  }

  const reminderTitle = t('me.account.remindersTitle', 'Allow reminder notifications')
  const address = email.data?.email ?? null
  const remindersOn = !!email.data?.optIn && !!address
  const toggleReminders = (v: boolean) => {
    if (v && !address) {
      setChanging(true)                                   // there is nowhere to send them yet: ask for the address first
      return
    }
    saveEmail.mutate({ email: address, optIn: v }, { onSuccess: () => showToast(v ? t('me.privacy.turnedOn', 'Turned on') : t('me.privacy.turnedOff', 'Turned off')) })
  }

  return (
    <section id="consents" className="flex scroll-mt-4 flex-col gap-3">
      <SectionTitle>{t('me.account.consentsTitle', 'Consents')}</SectionTitle>
      <p className="text-sub text-ink2">{t('me.privacy.intro', 'You can change any of these at any time. Turning one off does not delete your data.')}</p>
      {consents.isPending && <Skeleton className="h-64" />}
      {consents.isError && (
        <Alert tone="warn">
          {t('me.privacy.loadError', 'We could not load your choices just now.')} {consents.error?.message}
        </Alert>
      )}
      {consents.data && (
        <Card className="!py-1">
          <ul className="divide-y divide-line">
            {ROWS.map((c) => {
              const granted = !!consents.data.consents.find((x) => x.kind === c.kind)?.granted
              return (
                <li key={c.kind} className="flex flex-col gap-3 py-3.5">
                  <div className="flex items-start justify-between gap-4">
                    <div className="min-w-0 flex-1">
                      <p className="text-body font-bold">{c.title}</p>
                      <p className="text-sub text-ink2">{c.sub}</p>
                      {c.required && <p className="text-sub text-ink3">{t('me.privacy.required', 'Required to use the app. ')}</p>}
                    </div>
                    <Toggle on={granted} onChange={(v) => change(c.kind, v)} label={c.title} />
                  </div>
                  {askOff === c.kind && (
                    <Alert tone="warn" title={t('me.privacy.askOffTitle', 'Turn off using your health data?')}>
                      <p>
                        {t(
                          'me.privacy.askOffText',
                          'Smart Health will stop reading what you log and what your devices send. Insights, reminders and the doctor brief will stop until you turn this on again. Nothing is deleted.',
                        )}
                      </p>
                      <div className="mt-3 flex flex-col gap-2">
                        <Button variant="danger" disabled={setConsent.isPending} onClick={() => apply(c.kind, false)}>
                          {t('me.privacy.turnOff', 'Turn off')}
                        </Button>
                        <Button variant="ghost" onClick={() => setAskOff(null)}>
                          {t('me.privacy.keepOn', 'Keep it on')}
                        </Button>
                      </div>
                    </Alert>
                  )}
                </li>
              )
            })}

            <li className="flex flex-col gap-1 py-3.5">
              <div className="flex items-start justify-between gap-4">
                <div className="min-w-0 flex-1">
                  <p className="text-body font-bold">{reminderTitle}</p>
                  <p className="text-sub text-ink2">
                    {t('me.account.remindersSub', 'Reminders for your medicines, and for logs such as food and exercise, are sent to you by email.')}
                  </p>
                  {address && <p className="break-all text-sub text-ink3">{t('me.account.sentTo', 'Sent to {{email}}', { email: address })}</p>}
                </div>
                {email.data ? <Toggle on={remindersOn} onChange={toggleReminders} label={reminderTitle} /> : null}
              </div>
              {email.isError && <Alert tone="warn">{t('me.email.loadError', 'Email reminders are not available right now. Your other settings still work. Try again later.')}</Alert>}
              {email.data && (
                <div>
                  <button type="button" onClick={() => setChanging(true)} className="press inline-flex min-h-12 items-center text-sub text-ink2 underline decoration-1 underline-offset-4">
                    {address ? t('me.account.changeEmail', 'Change email address') : t('me.account.addEmail', 'Add an email address')}
                  </button>
                </div>
              )}
            </li>
          </ul>
        </Card>
      )}
      {setConsent.isError && (
        <Alert tone="warn">
          {t('me.privacy.notSaved', 'That change was not saved.')} {setConsent.error?.message}
        </Alert>
      )}
      {saveEmail.isError && !changing && (
        <Alert tone="warn">
          {t('me.email.notSaved', 'Your email settings could not be saved.')} {saveEmail.error?.message}
        </Alert>
      )}
      {changing && email.data && <EmailSheet current={address} optIn={email.data.optIn} onClose={() => setChanging(false)} />}
    </section>
  )
}

/** Change (or add) the address reminders are sent to. Saving an address turns reminders on when there was none. */
function EmailSheet({ current, optIn, onClose }: { current: string | null; optIn: boolean; onClose: () => void }) {
  const { t } = useTranslation()
  const showToast = useUi((s) => s.showToast)
  const save = useSaveEmailReminders()
  const [value, setValue] = useState(current ?? '')
  const err = emailError(value)
  const trimmed = value.trim()
  const submit = () =>
    save.mutate(
      { email: trimmed || null, optIn: trimmed ? (current ? optIn : true) : false },
      {
        onSuccess: () => {
          showToast(t('me.email.saved', 'Email settings saved'))
          onClose()
        },
      },
    )
  return (
    <Sheet title={current ? t('me.account.changeEmail', 'Change email address') : t('me.account.addEmail', 'Add an email address')} onClose={onClose}>
      <div className="flex flex-col gap-4">
        <Field
          label={t('me.email.addressV2', 'Email address')}
          value={value}
          onChange={setValue}
          placeholder="name@example.com"
          error={err}
          hint={trimmed ? undefined : t('me.email.emptyHint', 'Leave this empty if you do not want reminder emails.')}
        />
        {save.isError && (
          <Alert tone="warn">
            {t('me.email.notSaved', 'Your email settings could not be saved.')} {save.error?.message}
          </Alert>
        )}
        <div className="flex gap-3">
          <Button variant="secondary" className="!w-auto flex-none px-6" onClick={onClose}>
            {t('common.cancel', 'Cancel')}
          </Button>
          <Button disabled={!!err || save.isPending} onClick={submit}>
            {save.isPending ? t('me.account.saving', 'Saving') : t('common.save', 'Save')}
          </Button>
        </div>
      </div>
    </Sheet>
  )
}
