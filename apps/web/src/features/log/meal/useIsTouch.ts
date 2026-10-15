import { useEffect, useState } from 'react'

const TOUCH = '(pointer: coarse)'

/** True on phones and tablets (a finger is the main pointer). Used to offer the camera only where it makes sense. */
export function useIsTouch() {
  const [touch, setTouch] = useState(() => typeof window !== 'undefined' && window.matchMedia(TOUCH).matches)
  useEffect(() => {
    const mq = window.matchMedia(TOUCH)
    const update = () => setTouch(mq.matches)
    mq.addEventListener('change', update)
    return () => mq.removeEventListener('change', update)
  }, [])
  return touch
}
