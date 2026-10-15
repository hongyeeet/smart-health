// Entry for the single-file copy. It does what apps/web/src/main.tsx does, after putting the recorded-data shim in place of the network.
// The app itself is imported from apps/web/src and is not changed.
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import '@/index.css'
import '@/i18n'
import { applyPalette, palettes } from '@/theme/palettes'
import { App } from '@/app/App'
import { installShim } from './shim'

installShim()
applyPalette(document.documentElement, palettes.light)

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
