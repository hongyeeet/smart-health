/**
 * "Emergency contacts": everyone we email if the person's glucose looks very low and they do not answer. The first contact is the one set
 * up at the start; more can be added. After a save the pop-up closes and the contact shows in the list with a green "Saved to your account"
 * mark (the save button never stays green). Remove asks first. Each contact needs a name and a phone or an email; an email is what reaches them.
 */
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useUi } from '@/state/store'
import { Sheet } from '@/ui/Sheet'
import { CheckCircle, Envelope, Phone, Plus } from '@/ui/icons'
import { Alert, Button, Card, Field, SectionTitle, Skeleton, StatusPill } from '@/ui/primitives'
import { READ_ONLY_USER } from '@/features/onboarding/api'
import { contactProblem, emailError, phoneError } from '../settings/rules'
import { useContacts, useRemoveContactItem, useSaveContactItem, type ContactItem } from '../settings/api'
import { EditLink } from './InfoSection'

const BLANK = { name: '', relation: '', phone: '', email: '' }

export function ContactsSection() {
  const { t } = useTranslation()
  const user = useUi((s) => s.userKey)
  const q = useContacts()
  const remove = useRemoveContactItem()
  const [editing, setEditing] = useState<ContactItem | 'new' | null>(null)
  const [asking, setAsking] = useState<string | null>(null)
  const [justSaved, setJustSaved] = useState<string | null>(null)
  const contacts = q.data?.contacts ?? []

  return (
    <section id="contacts" className="flex scroll-mt-4 flex-col gap-3">
      <SectionTitle>{t('me.account.contactsTitle', 'Emergency contacts')}</SectionTitle>
      <p className="text-sub text-ink2">
        {t('me.account.contactsSub', 'If your glucose looks very low and you do not answer, we email these people and ask them to check on you, or to call 995.')}
      </p>
      {q.isPending && <Skeleton className="h-28" />}
      {q.isError && <Alert tone="warn">{t('me.contact.loadError', 'We could not load your emergency contact just now. Please try again in a moment.')}</Alert>}
      {q.data && (
        <Card className="flex flex-col !py-2">
          {contacts.length === 0 ? (
            <p className="py-3 text-body text-ink2">{t('me.account.noContacts', 'No emergency contact yet.')}</p>
          ) : (
            <ul className="divide-y divide-line">
              {contacts.map((c) => (
                <li key={c.id} className="flex flex-col gap-1 py-3">
                  <div className="flex items-start justify-between gap-3">
                    <p className="min-w-0 break-words text-body font-bold">
                      {c.name}
                      {c.relation ? <span className="font-normal text-ink2">{` · ${c.relation}`}</span> : null}
                    </p>
                    <div className="flex flex-none items-center">
                      <EditLink onClick={() => setEditing(c)} label={t('me.account.editAria', 'Edit {{what}}', { what: c.name ?? '' })} />
                      <EditLink
                        onClick={() => setAsking(asking === c.id ? null : c.id)}
                        label={t('me.account.removeAria', 'Remove {{what}}', { what: c.name ?? '' })}
                      >
                        {t('me.account.remove', 'remove')}
                      </EditLink>
                    </div>
                  </div>
                  {c.phone && (
                    <p className="num flex items-center gap-2 text-sub text-ink2">
                      <Phone size={16} aria-hidden />
                      {c.phone}
                    </p>
                  )}
                  {c.email && (
                    <p className="flex items-center gap-2 break-all text-sub text-ink2">
                      <Envelope size={16} aria-hidden />
                      {c.email}
                    </p>
                  )}
                  {justSaved === c.id && (
                    <div>
                      <StatusPill tone="ok" icon={CheckCircle}>
                        {t('me.account.savedToAccount', 'Saved to your account')}
                      </StatusPill>
                    </div>
                  )}
                  {asking === c.id && (
                    <div className="flex flex-wrap items-center gap-2 pt-1">
                      <span className="text-sub text-ink2">{t('me.account.removeAsk', 'Remove this contact?')}</span>
                      <Button
                        variant="danger"
                        size="md"
                        className="!w-auto"
                        disabled={remove.isPending}
                        onClick={() => remove.mutate(c.id, { onSuccess: () => { setAsking(null); setJustSaved(null) } })}
                      >
                        {t('me.account.yesRemove', 'Yes, remove')}
                      </Button>
                      <Button variant="secondary" size="md" className="!w-auto" onClick={() => setAsking(null)}>
                        {t('me.care.keepIt', 'Keep it')}
                      </Button>
                    </div>
                  )}
                </li>
              ))}
            </ul>
          )}
          {remove.isError && <Alert tone="warn">{t('me.account.removeError', 'That contact was not removed. Please try again.')}</Alert>}
          <div className="border-t border-line pt-2">
            <Button variant="secondary" size="md" icon={Plus} className="!w-auto" onClick={() => setEditing('new')}>
              {contacts.length === 0 ? t('me.account.addContact', 'Add an emergency contact') : t('me.account.addAnother', 'Add another emergency contact')}
            </Button>
          </div>
        </Card>
      )}
      {editing && (
        <ContactSheet
          existing={editing === 'new' ? null : editing}
          emailSupported={q.data?.emailSupported !== false}
          readOnly={user === READ_ONLY_USER}
          onClose={() => setEditing(null)}
          onSaved={(id) => {
            setJustSaved(id)
            setEditing(null)
          }}
        />
      )}
    </section>
  )
}

function ContactSheet({ existing, emailSupported, readOnly, onClose, onSaved }: { existing: ContactItem | null; emailSupported: boolean; readOnly: boolean; onClose: () => void; onSaved: (id: string) => void }) {
  const { t } = useTranslation()
  const showToast = useUi((s) => s.showToast)
  const save = useSaveContactItem()
  const [form, setForm] = useState(existing ? { name: existing.name ?? '', relation: existing.relation ?? '', phone: existing.phone ?? '', email: existing.email ?? '' } : BLANK)
  const set = (k: keyof typeof BLANK) => (v: string) => setForm((f) => ({ ...f, [k]: v }))
  const problem = contactProblem(form) ?? (!form.name.trim() ? t('me.rules.contactName', 'Add the name of your emergency contact.') : undefined)
  const bad = !!problem || !!phoneError(form.phone) || !!emailError(form.email)
  const emailNotYet = !!form.email.trim() && !emailSupported

  const submit = () =>
    save.mutate(
      { id: existing?.id, contact: form },
      {
        onSuccess: (data) => {
          showToast(t('me.account.contactSaved', 'Emergency contact saved to your account'))
          onSaved(existing ? existing.id : (data.contacts[data.contacts.length - 1]?.id ?? 'primary'))
        },
      },
    )

  return (
    <Sheet title={existing ? t('me.account.editContact', 'Edit emergency contact') : t('me.account.newContact', 'New emergency contact')} onClose={onClose}>
      <div className="flex flex-col gap-4">
        {readOnly && <Alert tone="info">{t('me.account.exampleNoticeV2', 'Mr Tan is an example record. It is not changed from here. Create your own user to keep your own information.')}</Alert>}
        <div className="grid gap-4 sm:grid-cols-2 [[data-ts='2']_&]:sm:grid-cols-1 [&>*]:min-w-0">
          <Field label={t('me.contact.name', 'Name')} value={form.name} onChange={set('name')} placeholder={t('me.contact.namePlaceholder', 'For example, Mdm Lim')} />
          <Field label={t('me.contact.relation', 'Relationship to you')} value={form.relation} onChange={set('relation')} placeholder={t('me.contact.relationPlaceholder', 'For example, spouse')} />
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
        </div>
        {problem && form.name.trim() !== '' && <Alert tone="warn">{problem}</Alert>}
        {emailNotYet && (
          <Alert tone="warn">{t('me.contact.emailNotYet', 'Email for your emergency contact is not set up yet, so it cannot be saved. The name and phone number can still be saved.')}</Alert>
        )}
        {save.isError && (
          <Alert tone="warn">
            {t('me.contact.notSaved', 'Your contact was not saved.')} {save.error?.message}
          </Alert>
        )}
        <div className="flex gap-3">
          <Button variant="secondary" className="!w-auto flex-none px-6" onClick={onClose}>
            {t('common.cancel', 'Cancel')}
          </Button>
          <Button disabled={bad || readOnly || save.isPending} onClick={submit}>
            {save.isPending ? t('me.account.saving', 'Saving') : t('me.contact.save', 'Save contact')}
          </Button>
        </div>
      </div>
    </Sheet>
  )
}
