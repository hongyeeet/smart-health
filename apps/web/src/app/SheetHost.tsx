import { AnimatePresence } from 'motion/react'
import { useUi } from '@/state/store'
import { sheets } from './sheetRegistry'

export function SheetHost() {
  const sheet = useUi((s) => s.sheet)
  const close = useUi((s) => s.closeSheet)
  const Comp = sheet ? sheets[sheet.id] : undefined
  return <AnimatePresence>{sheet && Comp && <Comp key={sheet.id} onClose={close} {...(sheet.props ?? {})} />}</AnimatePresence>
}
