import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import en from './locales/en.json'
import zh from './locales/zh.json'

/**
 * Strings are written in components as t('screen.key', 'English text'). The English text is the default, so the app always renders.
 * Translations live in one file per area and language: locales/<lang>/<area>.json (lang is zh, ms or ta). Every such file is picked up
 * here by name, so adding a file is all it takes. `npm run i18n:extract` writes every key to locales/en.generated.json for translators.
 * Chinese, Malay and Tamil are machine translated and wait for a native speaker's review (docs/review/translations.md); where a key is
 * missing the English text is shown, so a half-translated screen still works.
 */
type Tree = { [k: string]: string | string[] | Tree }
const merge = (into: Tree, from: Tree): Tree => {
  for (const [k, v] of Object.entries(from)) {
    const cur = into[k]
    into[k] = typeof v === 'object' && v !== null && typeof cur === 'object' && cur !== null ? merge(cur as Tree, v as Tree) : v
  }
  return into
}

const files = import.meta.glob('./locales/*/*.json', { eager: true, import: 'default' }) as Record<string, Tree>
const bundles: Record<'zh' | 'ms' | 'ta', Tree> = { zh: { ...(zh as unknown as Tree) }, ms: {}, ta: {} }
for (const [path, tree] of Object.entries(files)) {
  const lang = path.split('/')[2] as 'zh' | 'ms' | 'ta'
  if (bundles[lang]) bundles[lang] = merge(bundles[lang], tree)
}

void i18n.use(initReactI18next).init({
  resources: { en: { translation: en }, zh: { translation: bundles.zh }, ms: { translation: bundles.ms }, ta: { translation: bundles.ta } },
  lng: 'en',
  fallbackLng: 'en',
  interpolation: { escapeValue: false },
  returnNull: false,
})

export default i18n
