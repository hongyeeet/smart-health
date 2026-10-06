import type { ComponentType } from 'react'
import type { SheetId } from '@/state/store'
import { EntrySheet } from '@/features/sheets/EntrySheet'

/** Built sheets, by id. Add a component here and `go('E7', { sheet: {...} })` will open it. */
export const sheets: Partial<Record<SheetId, ComponentType<{ onClose: () => void } & Record<string, unknown>>>> = {
  E7: EntrySheet as ComponentType<{ onClose: () => void } & Record<string, unknown>>,
}
