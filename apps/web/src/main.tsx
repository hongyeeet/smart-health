import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import './i18n'
import { applyPalette, palettes } from './theme/palettes'
import { App } from './app/App'

// first paint in light colours; the theme provider takes over straight after
applyPalette(document.documentElement, palettes.light)

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
