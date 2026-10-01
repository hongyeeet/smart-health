import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { Locale, LogResult } from '@/data/types'
import type { ThemeName } from '@/theme/palettes'

export type SheetId = 'C7' | 'D2' | 'E7' | 'H5' | 'H7' | 'L2'

export interface SheetState {
  id: SheetId
  props?: Record<string, unknown>
}

interface UiState {
  theme: ThemeName
  textScale: 1 | 2
  locale: Locale
  setTheme: (t: ThemeName) => void
  setTextScale: (s: 1 | 2) => void
  setLocale: (l: Locale) => void

  consentData: boolean
  consentShare: boolean
  setConsent: (k: 'consentData' | 'consentShare', v: boolean) => void

  sheet: SheetState | null
  openSheet: (id: SheetId, props?: Record<string, unknown>) => void
  closeSheet: () => void

  lastLog: LogResult | null
  setLastLog: (l: LogResult | null) => void

  toast: { id: number; text: string } | null
  showToast: (text: string) => void

  /** recheck timer on the urgent screen */
  recheckAt: number | null
  setRecheck: (t: number | null) => void
}

export const useUi = create<UiState>()(
  persist(
    (set) => ({
      theme: 'light',
      textScale: 1,
      locale: 'en',
      setTheme: (theme) => set({ theme }),
      setTextScale: (textScale) => set({ textScale }),
      setLocale: (locale) => set({ locale }),

      consentData: false,
      consentShare: false,
      setConsent: (k, v) => set({ [k]: v } as Partial<UiState>),

      sheet: null,
      openSheet: (id, props) => set({ sheet: { id, props } }),
      closeSheet: () => set({ sheet: null }),

      lastLog: null,
      setLastLog: (lastLog) => set({ lastLog }),

      toast: null,
      showToast: (text) => set({ toast: { id: Date.now(), text } }),

      recheckAt: null,
      setRecheck: (recheckAt) => set({ recheckAt }),
    }),
    {
      name: 'smart-health-ui',
      partialize: (s) => ({ theme: s.theme, textScale: s.textScale, locale: s.locale }),
    },
  ),
)
