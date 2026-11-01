import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import ar from './ar.json'
import en from './en.json'

const saved = localStorage.getItem('lang') || 'ar'
i18n.use(initReactI18next).init({
  resources: { ar: { translation: ar }, en: { translation: en } },
  lng: saved, fallbackLng: 'en', interpolation: { escapeValue: false }
})
export function applyLang(lng) {
  document.documentElement.lang = lng
  document.documentElement.dir = lng === 'ar' ? 'rtl' : 'ltr'
  localStorage.setItem('lang', lng)
}
applyLang(saved)
export default i18n
