import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import en from './locales/en.json'
import zh from './locales/zh.json'

/**
 * Strings are written in components as t('screen.key', 'English text'). The English text is the
 * default, so the app always renders. `npm run i18n:extract` writes every key to
 * locales/en.generated.json for translators. Chinese is filled for the medicine page and navigation first;
 * Malay and Tamil are added the same way later.
 */
void i18n.use(initReactI18next).init({
  resources: { en: { translation: en }, zh: { translation: zh } },
  lng: 'en',
  fallbackLng: 'en',
  interpolation: { escapeValue: false },
  returnNull: false,
})

export default i18n
