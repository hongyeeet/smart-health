import { AnimatePresence } from 'motion/react'
import { useUi } from '@/state/store'
import { WhySheet } from './WhySheet'
import { MarkerSheet } from './MarkerSheet'
import { EntrySheet } from './EntrySheet'
import { InteractionSheet } from './InteractionSheet'
import { MissSheet } from './MissSheet'
import { ShareSheet } from './ShareSheet'

/** Renders whichever sheet is open. Sheets are opened with go('H7', { sheet: {...} }). */
export function SheetHost() {
  const sheet = useUi((s) => s.sheet)
  const close = useUi((s) => s.closeSheet)
  const props = (sheet?.props ?? {}) as Record<string, never>
  return (
    <AnimatePresence>
      {sheet?.id === 'C7' && <WhySheet key="C7" onClose={close} {...props} />}
      {sheet?.id === 'D2' && <MarkerSheet key="D2" onClose={close} {...props} />}
      {sheet?.id === 'E7' && <EntrySheet key="E7" onClose={close} {...props} />}
      {sheet?.id === 'H5' && <InteractionSheet key="H5" onClose={close} {...props} />}
      {sheet?.id === 'H7' && <MissSheet key="H7" onClose={close} {...props} />}
      {sheet?.id === 'L2' && <ShareSheet key="L2" onClose={close} />}
    </AnimatePresence>
  )
}
