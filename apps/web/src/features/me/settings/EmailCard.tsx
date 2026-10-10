/** Email reminders: one address and an on/off switch. Shared contract with onboarding: GET/PUT /notify/email. */
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useUi } from '@/state/store'
import { Alert, Button, Card, Field, SectionTitle, Skeleton, Toggle } from '@/ui/primitives'
import { emailError } from './rules'
import { useEmailReminders, useSaveEmailReminders } from './api'

export function EmailCard() {
  const { t } = useTranslation()
  const q = useEmailReminders()
  const save = useSaveEmailReminders()
  const showToast = useUi((s) => s.showToast)
  const [email, setEmail] = useState('')
  const [on, setOn] = useState(true)
  const [loaded, setLoaded] = useState(false)

  // Fill the form once from the server; after that the person's own edits stay as typed.
  useEffect(() => {
    if (q.data && !loaded) {
      setEmail(q.data.email ?? '')
      setOn(q.data.optIn)
      setLoaded(true)
    }
  }, [q.data, loaded])

  const err = emailError(email)

  return (
    <Card as="section" className="flex flex-col gap-3">
      <SectionTitle>{t('me.email.title', 'Email reminders')}</SectionTitle>
      <p className="text-body text-ink2">{t('me.email.intro', 'Reminder emails go to your Gmail address. You can turn them off here at any time.')}</p>

      {q.isPending && <Skeleton className="h-24" />}
      {q.isError && <Alert tone="warn">{t('me.email.loadError', 'Email reminders are not available right now. Your other settings still work. Try again later.')}</Alert>}

      {q.data && (
        <>
          <Field
            label={t('me.email.address', 'Gmail address')}
            value={email}
            onChange={setEmail}
            placeholder="name@gmail.com"
            error={err}
            hint={email.trim() ? undefined : t('me.email.emptyHint', 'Leave this empty if you do not want reminder emails.')}
          />
          <div className="flex items-center justify-between gap-4">
            <span className="text-body">{t('me.email.send', 'Send me reminder emails')}</span>
            <Toggle on={on} onChange={setOn} label={t('me.email.send', 'Send me reminder emails')} />
          </div>
          <p className="text-sub text-ink3">
            {on ? t('me.email.on', 'Reminder emails are on.') : t('me.email.off', 'Reminder emails are off.')}{' '}
            {t('me.email.urgentNote', 'Urgent alerts to your emergency contact are not affected.')}
          </p>
          {save.isError && (
            <Alert tone="warn">
              {t('me.email.notSaved', 'Your email settings could not be saved.')} {save.error?.message}
            </Alert>
          )}
          <Button
            variant="secondary"
            disabled={!!err || save.isPending}
            onClick={() => save.mutate({ email: email.trim() || null, optIn: on }, { onSuccess: () => showToast(t('me.email.saved', 'Email settings saved')) })}
          >
            {t('me.email.save', 'Save email settings')}
          </Button>
        </>
      )}
    </Card>
  )
}
