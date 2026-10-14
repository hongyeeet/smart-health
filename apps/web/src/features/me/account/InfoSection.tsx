/**
 * "Your information": what the person told Equinox when they set up, grouped, each with a grey underlined "edit". Edit opens a small
 * pop-up with that one question and Save; only that answer is written (PUT /onboarding/profile). Nothing is shown that the server does
 * not have: an empty answer reads "Not set". Mr Tan's record is shown but never changed from here.
 */
import { useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useGo } from '@/app/navigation'
import { cn } from '@/lib/cn'
import { useUi } from '@/state/store'
import { Sheet } from '@/ui/Sheet'
import { Alert, Button, Card, SectionTitle, Skeleton } from '@/ui/primitives'
import { fromSaved, READ_ONLY_USER, useSaveStep, useSavedOnboarding, type SavedOnboarding } from '@/features/onboarding/api'
import { emptyAnswers, type OnboardingAnswers } from '@/features/onboarding/useOnboarding'
import { useOptions } from '@/features/onboarding/options'
import { buildFields, groupTitle, type FieldDef, type Group } from './fields'

const GROUPS: Group[] = ['about', 'care', 'health', 'results', 'devices', 'work']

/** A grey underlined word that looks like a link and is a button with a 48 px tap target. */
export function EditLink({ onClick, label, children }: { onClick: () => void; label: string; children?: string }) {
  const { t } = useTranslation()
  return (
    <button type="button" onClick={onClick} aria-label={label} className="press -my-1 inline-flex min-h-12 min-w-12 flex-none items-center justify-center px-1 text-sub text-ink3 underline decoration-1 underline-offset-4">
      {children ?? t('me.account.edit', 'edit')}
    </button>
  )
}

export function InfoSection() {
  const { t } = useTranslation()
  const go = useGo()
  const user = useUi((s) => s.userKey)
  const saved = useSavedOnboarding()
  const opts = useOptions()
  const fields = useMemo(() => buildFields(opts), [opts])
  const [editing, setEditing] = useState<FieldDef | null>(null)

  const answers: OnboardingAnswers | null = saved.data ? fromSaved(saved.data, emptyAnswers) : null
  const noProfile = !!saved.data && saved.data.profile === null

  return (
    <section id="information" className="flex scroll-mt-4 flex-col gap-3">
      <SectionTitle>{t('me.account.infoTitle', 'Your information')}</SectionTitle>
      <p className="text-sub text-ink2">{t('me.account.infoSub', 'What you told Equinox when you set up. Change any answer here and it is saved to your account.')}</p>
      {user === READ_ONLY_USER && <Alert tone="info">{t('me.account.exampleNoticeV2', 'Mr Tan is an example record. It is not changed from here. Create your own user to keep your own information.')}</Alert>}
      {saved.isPending && <Skeleton className="h-64" />}
      {saved.isError && <Alert tone="warn">{t('me.account.infoError', 'We could not load your information just now. Please try again in a moment.')}</Alert>}
      {noProfile && (
        <Alert tone="info">
          {t('me.account.noProfile', 'There is no profile yet. Answer the set-up questions first, then you can change any answer here.')}
          <div className="mt-2">
            <Button variant="secondary" size="md" className="!w-auto" onClick={() => go('A1')}>
              {t('me.account.startSetup', 'Start set-up')}
            </Button>
          </div>
        </Alert>
      )}
      {answers && saved.data && !noProfile && (
        <div className="grid gap-4 lg:grid-cols-2 lg:items-start [&>*]:min-w-0">
          {GROUPS.map((g) => (
            <Card key={g} as="section" className="flex flex-col !py-3">
              <h3 className="text-sub font-bold text-ink2">{groupTitle(g)}</h3>
              <dl className="divide-y divide-line">
                {fields
                  .filter((f) => f.group === g)
                  .map((f) => {
                    const value = f.show(answers, saved.data!)
                    return (
                      <div key={f.id} className="flex items-center justify-between gap-3 py-1.5">
                        <div className="min-w-0 flex-1 py-1">
                          <dt className="text-sub text-ink2">{f.label}</dt>
                          <dd className={cn('break-words text-body', value ? 'font-bold text-ink' : 'text-ink3')}>{value ?? t('me.account.notSet', 'Not set')}</dd>
                        </div>
                        <EditLink onClick={() => setEditing(f)} label={t('me.account.editAria', 'Edit {{what}}', { what: f.label })}>
                          {value ? undefined : t('me.account.add', 'add')}
                        </EditLink>
                      </div>
                    )
                  })}
              </dl>
            </Card>
          ))}
        </div>
      )}
      {editing && saved.data && answers && <EditSheet def={editing} saved={saved.data} answers={answers} onClose={() => setEditing(null)} />}
    </section>
  )
}

/** One question in a pop-up. The draft starts from the saved answer; Save writes only this answer. */
function EditSheet({ def, saved, answers, onClose }: { def: FieldDef; saved: SavedOnboarding; answers: OnboardingAnswers; onClose: () => void }) {
  const { t } = useTranslation()
  const user = useUi((s) => s.userKey)
  const showToast = useUi((s) => s.showToast)
  const save = useSaveStep()
  const d = def as unknown as FieldDef<unknown>
  const [draft, setDraft] = useState<unknown>(() => d.init(answers, saved))
  const problem = d.problem?.(draft)
  const readOnly = user === READ_ONLY_USER

  const submit = () => {
    if (problem || readOnly) return
    save.mutate(
      { profile: d.body(draft), email: null },
      {
        onSuccess: () => {
          showToast(t('me.account.saved', 'Saved to your account'))
          onClose()
        },
      },
    )
  }
  const failure = save.error instanceof Error && !/^\d{3}\s/.test(save.error.message) ? save.error.message : t('me.account.saveError', 'We could not save that. Please try again.')

  return (
    <Sheet title={d.label} onClose={onClose} label={t('me.account.editAria', 'Edit {{what}}', { what: d.label })}>
      <div className="flex flex-col gap-4">
        {readOnly && <Alert tone="info">{t('me.account.exampleNoticeV2', 'Mr Tan is an example record. It is not changed from here. Create your own user to keep your own information.')}</Alert>}
        {d.editor(draft, setDraft)}
        {problem && <Alert tone="warn">{problem}</Alert>}
        {save.isError && <Alert tone="warn">{failure}</Alert>}
        <div className="flex gap-3">
          <Button variant="secondary" className="!w-auto flex-none px-6" onClick={onClose}>
            {t('common.cancel', 'Cancel')}
          </Button>
          <Button disabled={!!problem || readOnly || save.isPending} onClick={submit}>
            {save.isPending ? t('me.account.saving', 'Saving') : t('common.save', 'Save')}
          </Button>
        </div>
      </div>
    </Sheet>
  )
}
