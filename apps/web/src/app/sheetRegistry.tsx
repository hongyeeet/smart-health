import type { ComponentType } from 'react'
import type { SheetId } from '@/state/store'

/** Built sheets, by id. Add a component here and `go('H7', { sheet: {...} })` will open it. */
export const sheets: Partial<Record<SheetId, ComponentType<{ onClose: () => void } & Record<string, unknown>>>> = {}
