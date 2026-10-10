/** Email reminders: one address and an on/off switch. Shared contract with onboarding: GET/PUT /notify/email. */
import { useEffect, useState } from 'react'
import { useUi } from '@/state/store'
import { Alert, Button, Card, Field, SectionTitle, Skeleton, Toggle } from '@/ui/primitives'
import { emailError } from './rules'
import { useEmailReminders, useSaveEmailReminders } from './api'

export function EmailCard() {
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
      <SectionTitle>Email reminders</SectionTitle>
      <p className="text-body text-ink2">Reminder emails go to your Gmail address. You can turn them off here at any time.</p>

      {q.isPending && <Skeleton className="h-24" />}
      {q.isError && <Alert tone="warn">Email reminders are not available right now. Your other settings still work. Try again later.</Alert>}

      {q.data && (
        <>
          <Field
            label="Gmail address"
            value={email}
            onChange={setEmail}
            placeholder="name@gmail.com"
            error={err}
            hint={email.trim() ? undefined : 'Leave this empty if you do not want reminder emails.'}
          />
          <div className="flex items-center justify-between gap-4">
            <span className="text-body">Send me reminder emails</span>
            <Toggle on={on} onChange={setOn} label="Send me reminder emails" />
          </div>
          <p className="text-sub text-ink3">{on ? 'Reminder emails are on.' : 'Reminder emails are off.'} Urgent alerts to your emergency contact are not affected.</p>
          {save.isError && <Alert tone="warn">Your email settings could not be saved. {save.error?.message}</Alert>}
          <Button
            variant="secondary"
            disabled={!!err || save.isPending}
            onClick={() => save.mutate({ email: email.trim() || null, optIn: on }, { onSuccess: () => showToast('Email settings saved') })}
          >
            Save email settings
          </Button>
        </>
      )}
    </Card>
  )
}
