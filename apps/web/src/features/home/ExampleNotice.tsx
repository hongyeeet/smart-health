/**
 * Shown on Home while the app is showing Mr Tan, the example record everyone sees first. It says plainly that he is an example and that his
 * record cannot be changed, and offers the way to start your own: "Create my own user" opens set-up for a new user (newPerson.ts), who is
 * saved only when set-up is finished. Nothing shows once a person's own user is selected.
 */
import { useTranslation } from 'react-i18next'
import { useUi } from '@/state/store'
import { useStartNewPerson } from '@/features/onboarding/newPerson'
import { Button, Card } from '@/ui/primitives'

export function ExampleNotice() {
  const { t } = useTranslation()
  const user = useUi((s) => s.userKey)
  const people = useUi((s) => s.people)
  const startNew = useStartNewPerson()
  if (user !== 'mr-tan') return null
  return (
    <Card className="flex flex-col gap-3 !bg-brand-soft">
      <div>
        <p className="text-body font-bold">{t('home.example.title', 'You are looking at Mr Tan')}</p>
        <p className="mt-1 text-sub text-ink2">
          {t('home.example.body', 'Mr Tan is an example person with about 90 days of history, so you can see what Smart Health does. His record cannot be changed. To use Smart Health for yourself, create your own user.')}
        </p>
      </div>
      <Button onClick={() => startNew(t('switch.newUserN', 'New User {{n}}', { n: people.length + 1 }))}>{t('home.example.create', 'Create my own user')}</Button>
    </Card>
  )
}
