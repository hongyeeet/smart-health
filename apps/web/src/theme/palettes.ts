/**
 * Colour source of truth. Everything visual reads these through CSS variables
 * (applyPalette), so a new brand or a high-contrast theme is one more object here.
 * Contrast notes: ink on canvas is above 12:1; ink2 above 7:1; ink3 above 4.5:1 (use at 16px or larger).
 */
export interface Palette {
  canvas: string
  card: string
  well: string
  line: string
  ink: string
  ink2: string
  ink3: string
  brand: string
  brandPress: string
  brandSoft: string
  onBrand: string
  brass: string
  brassSoft: string
  ok: string
  okSoft: string
  warn: string
  warnSoft: string
  danger: string
  dangerSoft: string
  info: string
  infoSoft: string
  urgentBg: string
  overlay: string
  /** glucose range fills (AGP convention) */
  gVeryLow: string
  gLow: string
  gIn: string
  gHigh: string
  gVeryHigh: string
  /** data series, in order of use */
  s1: string
  s2: string
  s3: string
  /** activity effort bars: light = yellow, moderate = green, vigorous = orange (each also has a pattern, so colour is never the only cue) */
  actLight: string
  actLightEdge: string
  actModerate: string
  actVigorous: string
  band: string
}

export type ThemeName = 'light' | 'dark'

export const palettes: Record<ThemeName, Palette> = {
  light: {
    canvas: '#F6F4EE',
    card: '#FFFEFB',
    well: '#EFECE3',
    line: '#E1DDD0',
    ink: '#16201B',
    ink2: '#46524B',
    ink3: '#5F6B64',
    brand: '#1D4A3C',
    brandPress: '#143629',
    brandSoft: '#E2ECE6',
    onBrand: '#FBFAF5',
    brass: '#7A5C22',
    brassSoft: '#F0E7D0',
    ok: '#2B6B47',
    okSoft: '#E4EFE7',
    warn: '#935812',
    warnSoft: '#F6EAD3',
    danger: '#A12B2B',
    dangerSoft: '#F6E3E0',
    info: '#2E5A85',
    infoSoft: '#E3ECF5',
    urgentBg: '#F8E4E0',
    overlay: 'rgba(14, 22, 18, 0.42)',
    gVeryLow: '#6B1D1D',
    gLow: '#B8372C',
    gIn: '#4C9168',
    gHigh: '#D3A21F',
    gVeryHigh: '#CC6A1F',
    s1: '#1D4A3C',
    s2: '#9A7428',
    s3: '#2E5A85',
    actLight: '#F2CB4B',
    actLightEdge: '#8A6A06',
    actModerate: '#2F8A57',
    actVigorous: '#D86F1C',
    band: 'rgba(29, 74, 60, 0.10)',
  },
  dark: {
    canvas: '#0D1411',
    card: '#141D19',
    well: '#1B2621',
    line: '#2A3731',
    ink: '#ECEFE8',
    ink2: '#B3BEB7',
    ink3: '#8D9993',
    brand: '#86C9AA',
    brandPress: '#A8DBC3',
    brandSoft: '#1A2E26',
    onBrand: '#0A110E',
    brass: '#D8B46C',
    brassSoft: '#2D2615',
    ok: '#7CCB9A',
    okSoft: '#16291E',
    warn: '#E4B25C',
    warnSoft: '#2E2410',
    danger: '#F08A80',
    dangerSoft: '#34191A',
    info: '#8DB6E6',
    infoSoft: '#162538',
    urgentBg: '#351A1A',
    overlay: 'rgba(0, 0, 0, 0.6)',
    gVeryLow: '#B34B4B',
    gLow: '#E0645A',
    gIn: '#5FB583',
    gHigh: '#E0B53C',
    gVeryHigh: '#E58A45',
    s1: '#86C9AA',
    s2: '#D8B46C',
    s3: '#8DB6E6',
    actLight: '#E8C64F',
    actLightEdge: '#F3DC8A',
    actModerate: '#4DB07A',
    actVigorous: '#F0873A',
    band: 'rgba(134, 201, 170, 0.14)',
  },
}

const kebab = (s: string) => s.replace(/[A-Z]/g, (m) => '-' + m.toLowerCase())

/** Writes the palette as --c-* variables on an element (the phone frame or the document root). */
export function applyPalette(el: HTMLElement, p: Palette) {
  for (const [k, v] of Object.entries(p)) el.style.setProperty(`--c-${kebab(k)}`, v)
}
