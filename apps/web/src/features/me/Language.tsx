/** K5. Language, text size and colour theme. The language is saved to the person's profile; text size and theme stay on this device. */
import { useEffect } from 'react'
import { Trans, useTranslation } from 'react-i18next'
import { appConfig } from '@/config/app'
import type { Locale } from '@/data/types'
import { useUi } from '@/state/store'
import { Header, Screen } from '@/ui/layout'
import { Segmented } from '@/ui/controls'
import { Alert, Card, Chip, SectionTitle, Skeleton } from '@/ui/primitives'
import { useLanguage, useSaveLanguage } from './settings/api'

export function Language() {
  const { t } = useTranslation()
  const locale = useUi((s) => s.locale)
  const setLocale = useUi((s) => s.setLocale)
  const theme = useUi((s) => s.theme)
  const setTheme = useUi((s) => s.setTheme)
  const textScale = useUi((s) => s.textScale)
  const setTextScale = useUi((s) => s.setTextScale)
  const showToast = useUi((s) => s.showToast)

  const saved = useLanguage()
  const save = useSaveLanguage()

  // The profile is the source of truth for the language: when it loads, this device follows it.
  useEffect(() => {
    if (saved.data && saved.data.language !== locale) setLocale(saved.data.language)
  }, [saved.data, locale, setLocale])

  const choose = (code: Locale) => {
    if (code === locale) return
    setLocale(code)
    save.mutate(code, { onSuccess: () => showToast(t('me.language.saved', 'Language saved')) })
  }

  return (
    <Screen>
      <Header title={t('me.language.title', 'Language and display')} back backTo="K1" />

      <section className="flex flex-col gap-3 md:max-w-xl">
        <SectionTitle>{t('me.language.language', 'Language')}</SectionTitle>
        <div role="group" aria-label={t('me.language.language', 'Language')} className="flex flex-wrap gap-2">
          {appConfig.locales.map((l) => (
            <Chip key={l.code} on={locale === l.code} onClick={() => choose(l.code as Locale)}>
              {l.native}
            </Chip>
          ))}
        </div>
        <p className="text-sub text-ink2">
          {t('me.language.note', 'Chinese, Malay and Tamil are machine translated. Native speakers are still checking them.')}
        </p>
        {save.isError && (
          <Alert tone="warn">
            {t('me.language.saveError', 'Your language could not be saved to your profile.')} {save.error?.message}
          </Alert>
        )}
        {saved.isError && <Alert tone="warn">{t('me.language.loadError', 'We could not load your saved language. This device keeps the one you chose.')}</Alert>}
        {!saved.data && saved.isPending && <Skeleton className="h-12" />}
      </section>

      <section className="flex flex-col gap-3 md:max-w-xl">
        <SectionTitle>{t('me.language.textSize', 'Text size')}</SectionTitle>
        <Segmented
          label={t('me.language.textSize', 'Text size')}
          value={textScale}
          onChange={setTextScale}
          options={[
            { value: 1, label: t('me.language.standard', 'Standard') },
            { value: 2, label: t('me.language.larger', 'Larger, 200%') },
          ]}
        />
        <Card tone="soft" className="flex flex-col gap-2" as="section">
          <p className="text-sub font-bold text-ink2">{t('me.language.preview', 'Preview')}</p>
          <p className="text-body">
            <Trans
              i18nKey="me.language.previewText"
              defaults="This is how your text will look. Readings use larger numbers: <n>7.8</n> mmol/L."
              components={{ n: <span className="num text-h2" /> }}
            />
          </p>
        </Card>
      </section>

      <section className="flex flex-col gap-3 md:max-w-xl">
        <SectionTitle>{t('me.language.colour', 'Colour')}</SectionTitle>
        <Segmented
          label={t('me.language.colourTheme', 'Colour theme')}
          value={theme}
          onChange={setTheme}
          options={[
            { value: 'light', label: t('me.language.light', 'Light') },
            { value: 'dark', label: t('me.language.dark', 'Dark') },
          ]}
        />
      </section>
    </Screen>
  )
}
