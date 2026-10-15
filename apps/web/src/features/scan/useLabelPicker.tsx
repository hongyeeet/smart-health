import { useRef, useState, type ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useUploadScan } from '@/data/hooks'
import { href } from '@/app/routeIds'
import { shrinkImage } from '@/lib/image'

/**
 * Take or upload a label photo, send it to POST /scans and go to the review screen (H3).
 * Used by H1 (Meds page) and H2 (Scan a label), so both behave the same. Render `inputs` once on the screen:
 * they are the two hidden file inputs (camera on a phone, file picker on a laptop).
 * A failed or stalled upload never leaves the screen busy: `busy` is cleared in every case, and `error` says what to do next in plain
 * words. `cancel` stops a photo that is being read and goes back to the start without a message.
 */
export function useLabelPicker(): {
  busy: boolean
  error: string | null
  takePhoto: () => void
  uploadPhoto: () => void
  cancel: () => void
  inputs: ReactNode
} {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const upload = useUploadScan()
  const cameraRef = useRef<HTMLInputElement>(null)
  const galleryRef = useRef<HTMLInputElement>(null)
  const current = useRef<AbortController | null>(null)
  const stoppedByPerson = useRef(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleFile = async (file: File) => {
    setError(null)
    setBusy(true)
    const controller = new AbortController()
    current.current = controller
    stoppedByPerson.current = false
    try {
      // a phone camera photo can be over the 10 MB limit; a longer edge than the meal photo keeps small label print readable
      const small = await shrinkImage(file, 2200)
      const result = await upload.mutateAsync({ file: small, cancel: controller.signal })
      navigate(href('H3'), { state: { scanId: result.scanId } })
    } catch (e) {
      if (stoppedByPerson.current) return                  // the person pressed Cancel: nothing to report
      // fetch() rejects with a TypeError when there is no connection at all; a server refusal comes back as an HTTP status, and a stalled
      // upload is given up after the time limit (an AbortError). The last two read the same way: the photo could not be read.
      setError(
        e instanceof TypeError
          ? t('scanFrame.network', 'We could not reach Equinox. Check your connection and try again.')
          : e instanceof DOMException && e.name === 'AbortError'
            ? t('scanFrame.slow', 'Reading the label is taking longer than usual. Please try again, or type it in.')
            : t('scanFrame.general', 'We could not read this. Take another photo or type it in.'),
      )
    } finally {
      current.current = null
      setBusy(false)
    }
  }

  const onPick = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0]
    if (f) void handleFile(f)
    e.target.value = ''
  }

  const cancel = () => {
    stoppedByPerson.current = true
    current.current?.abort()
  }

  return {
    busy,
    error,
    takePhoto: () => cameraRef.current?.click(),
    uploadPhoto: () => galleryRef.current?.click(),
    cancel,
    inputs: (
      <>
        <input ref={cameraRef} type="file" accept="image/*" capture="environment" className="hidden" onChange={onPick} aria-hidden tabIndex={-1} />
        <input ref={galleryRef} type="file" accept="image/*" className="hidden" onChange={onPick} aria-hidden tabIndex={-1} />
      </>
    ),
  }
}
