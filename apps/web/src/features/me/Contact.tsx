/** K9. One emergency contact. The urgent alert reads this; the alert is sent by email, so an email address is what reaches them. */
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useUi } from '@/state/store'
import { Footer, Header, Screen } from '@/ui/layout'
import { Alert, Button, Card, Field, SectionTitle, Skeleton } from '@/ui/primitives'
import { contactProblem, emailError, phoneError } from './settings/rules'
import { useContact, useSaveContact } from './settings/api'

export function Contact() {
  const { t } = useTranslation()
  const q = useContact()
  const save = useSaveContact()
  const showToast = useUi((s) => s.showToast)
  const [form, setForm] = useState({ name: '', relation: '', phone: '', email: '' })
  const [loaded, setLoaded] = useState(false)

  // Fill the form once from the saved contact; after that the person's own edits stay as typed.
  useEffect(() => {
    if (q.data && !loaded) {
      setForm({ name: q.data.name ?? '', relation: q.data.relation ?? '', phone: q.data.phone ?? '', email: q.data.email ?? '' })
      setLoaded(true)
    }
  }, [q.data, loaded])

  const set = (k: keyof typeof form) => (v: string) => setForm((f) => ({ ...f, [k]: v }))
  const problem = contactProblem(form)
  const bad = !!problem || !!phoneError(form.phone) || !!emailError(form.email)
  const emailNotYet = !!form.email.trim() && q.data?.emailSupported === false

  return (
    <Screen>
      <Header title={t('me.contact.title', 'Emergency contact')} back backTo="K1" sub={t('me.contact.sub', 'Someone who can check on you if your glucose is very low.')} />

      <Card as="section" tone="soft" className="flex flex-col gap-2">
        <p className="text-body font-bold">{t('me.contact.explain', 'If your glucose looks very low and you do not answer, we email this person.')}</p>
        <p className="text-sub text-ink2">
          {t('me.contact.explainTwo', 'The email asks them to check on you, or to call 995. Add their email address so the alert can reach them.')}
        </p>
      </Card>

      {q.isPending && <Skeleton className="h-72" />}
      {q.isError && <Alert tone="warn">{t('me.contact.loadError', 'We could not load your emergency contact just now. Please try again in a moment.')}</Alert>}

      {q.data && (
        <>
          <section className="flex flex-col gap-4">
            <SectionTitle>{t('me.contact.details', 'Their details')}</SectionTitle>
            <Field label={t('me.contact.name', 'Name')} value={form.name} onChange={set('name')} placeholder={t('me.contact.namePlaceholder', 'For example, Mdm Lim')} />
            <Field
              label={t('me.contact.relation', 'Relationship to you')}
              value={form.relation}
              onChange={set('relation')}
              placeholder={t('me.contact.relationPlaceholder', 'For example, spouse')}
            />
            <Field
              label={t('me.contact.phone', 'Mobile number')}
              type="tel"
              value={form.phone}
              onChange={set('phone')}
              placeholder="+65 9123 4567"
              error={phoneError(form.phone)}
              hint={t('me.contact.phoneHint', 'Digits only, with an optional + at the start.')}
            />
            <Field
              label={t('me.contact.email', 'Email address')}
              value={form.email}
              onChange={set('email')}
              placeholder="name@example.com"
              error={emailError(form.email)}
              hint={t('me.contact.emailHint', 'The alert is sent to this address.')}
            />
          </section>

          {problem && <Alert tone="warn">{problem}</Alert>}
          {emailNotYet && (
            <Alert tone="warn">
              {t('me.contact.emailNotYet', 'Email for your emergency contact is not set up yet, so it cannot be saved. The name and phone number can still be saved.')}
            </Alert>
          )}
          {save.isError && (
            <Alert tone="warn">
              {t('me.contact.notSaved', 'Your contact was not saved.')} {save.error?.message}
            </Alert>
          )}

          <Footer>
            <Button
              disabled={bad || save.isPending}
              onClick={() =>
                save.mutate(form, {
                  onSuccess: () => {
                    showToast(t('me.contact.saved', 'Emergency contact saved'))
                  },
                })
              }
            >
              {t('me.contact.save', 'Save contact')}
            </Button>
          </Footer>
        </>
      )}
    </Screen>
  )
}
