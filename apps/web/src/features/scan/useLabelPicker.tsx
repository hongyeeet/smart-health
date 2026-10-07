import { useRef, useState, type ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'
import { useUploadScan } from '@/data/hooks'
import { href } from '@/app/routeIds'

/**
 * Take or upload a label photo, send it to POST /scans and go to the review screen (H3).
 * Used by H1 (Meds page) and H2 (Scan a label), so both behave the same. Render `inputs` once on the screen:
 * they are the two hidden file inputs (camera on a phone, file picker on a laptop).
 */
export function useLabelPicker(): {
  busy: boolean
  error: string | null
  takePhoto: () => void
  uploadPhoto: () => void
  inputs: ReactNode
} {
  const navigate = useNavigate()
  const upload = useUploadScan()
  const cameraRef = useRef<HTMLInputElement>(null)
  const galleryRef = useRef<HTMLInputElement>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleFile = async (file: File) => {
    setError(null)
    setBusy(true)
    try {
      const result = await upload.mutateAsync(file)
      navigate(href('H3'), { state: { scanId: result.scanId } })
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not read the label. Please try again.')
    } finally {
      setBusy(false)
    }
  }

  const onPick = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0]
    if (f) void handleFile(f)
    e.target.value = ''
  }

  return {
    busy,
    error,
    takePhoto: () => cameraRef.current?.click(),
    uploadPhoto: () => galleryRef.current?.click(),
    inputs: (
      <>
        <input ref={cameraRef} type="file" accept="image/*" capture="environment" className="hidden" onChange={onPick} aria-hidden tabIndex={-1} />
        <input ref={galleryRef} type="file" accept="image/*" className="hidden" onChange={onPick} aria-hidden tabIndex={-1} />
      </>
    ),
  }
}
