import { useEffect, type ReactNode } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MotionConfig } from 'motion/react'
import i18n from '@/i18n'
import { palettes, applyPalette } from '@/theme/palettes'
import { useUi } from '@/state/store'

const queryClient = new QueryClient({ defaultOptions: { queries: { staleTime: 30_000, refetchOnWindowFocus: false, retry: 0 } } })

/** Applies the chosen palette and language to the document. A new theme is a new entry in theme/palettes.ts. */
function ThemeSync() {
  const theme = useUi((s) => s.theme)
  const locale = useUi((s) => s.locale)
  useEffect(() => {
    const root = document.documentElement
    applyPalette(root, palettes[theme])
    root.dataset.theme = theme
    document.querySelector('meta[name="theme-color"]')?.setAttribute('content', palettes[theme].canvas)
  }, [theme])
  useEffect(() => {
    void i18n.changeLanguage(locale)
    document.documentElement.lang = locale
  }, [locale])
  return null
}

export function Providers({ children }: { children: ReactNode }) {
  return (
    <QueryClientProvider client={queryClient}>
      <MotionConfig reducedMotion="user">
        <ThemeSync />
        {children}
      </MotionConfig>
    </QueryClientProvider>
  )
}
