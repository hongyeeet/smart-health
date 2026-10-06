import { useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useUploadScan } from '@/data/hooks'
import { href } from '@/app/routeIds'
import { Footer, Header, Screen, Split } from '@/ui/layout'
import { Alert, Button, Card, SectionTitle, Skeleton } from '@/ui/primitives'
import { Camera, Image as ImageIcon, Info } from '@/ui/icons'

/**
 * H2 — Scan a label: camera/upload screen with framing tips.
 * On "Take photo", the file input captures from the camera on mobile (capture="environment")
 * or opens the file picker on desktop. The upload mutation calls POST /scans which runs the
 * vision extractor and returns the ScanResult; we stash the scanId in router state for H3.
 */
export function ScanFrame() {
  const navigate = useNavigate()
  const upload = useUploadScan()
  const inputRef = useRef<HTMLInputElement>(null)
  const sampleRef = useRef<HTMLInputElement>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleFile = async (file: File) => {
    setError(null)
    setLoading(true)
    try {
      const result = await upload.mutateAsync(file)
      // navigate to the review screen with the scanId
      navigate(href('H3'), { state: { scanId: result.scanId } })
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not read the label. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Screen>
      <Header title="Scan a label" back backTo="H1" sub="Step 1 of 3 — take a photo of the label" />
      {loading ? (
        <>
          <Card tone="soft" className="flex flex-col items-center gap-3 py-10">
            <Skeleton className="h-48 w-full" />
            <p className="text-body font-bold text-ink2">Reading your label…</p>
            <p className="text-sub text-ink3">The AI is extracting the medicine details. This takes a few seconds.</p>
          </Card>
        </>
      ) : (
        <>
          <Split>
          <div className="relative flex h-72 items-center justify-center overflow-hidden rounded-card bg-[#101815]" role="img" aria-label="Camera view with a frame to line the label up in">
            {['left-4 top-4 border-l-4 border-t-4', 'right-4 top-4 border-r-4 border-t-4', 'bottom-4 left-4 border-b-4 border-l-4', 'bottom-4 right-4 border-b-4 border-r-4'].map((c) => (
              <span key={c} className={`absolute h-10 w-10 rounded-sm border-[#E9EFEA] ${c}`} />
            ))}
            <p className="px-10 text-center text-body text-[#C9D3CD]">Line up the label inside the corners</p>
          </div>
          <Card tone="soft" className="flex flex-col gap-2">
            <SectionTitle>Tips</SectionTitle>
            <ul className="flex flex-col gap-1.5 text-body">
              <li>Use good light and keep the label flat.</li>
              <li>Hold still until the text looks sharp.</li>
              <li>Medicines, supplements and herbal products all work.</li>
            </ul>
          </Card>
          </Split>
          {error && (
            <Alert tone="danger" title="Could not read the label">
              {error}
            </Alert>
          )}
          <Footer>
            <Button icon={Camera} onClick={() => inputRef.current?.click()}>
              Take photo
            </Button>
            <Button variant="secondary" icon={imageIcon} onClick={() => sampleRef.current?.click()}>
              Upload a photo
            </Button>
          </Footer>
          <Card tone="soft" className="flex items-start gap-3">
            <Info size={20} className="mt-0.5 flex-none text-ink3" aria-hidden />
            <p className="text-sub text-ink2">
              Patient name, NRIC and phone numbers are removed before anything is stored. The app never guesses — if a field
              can't be read, you type it yourself.
            </p>
          </Card>
        </>
      )}
      {/* Hidden file inputs: capture from camera vs. upload from gallery */}
      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        capture="environment"
        className="hidden"
        onChange={(e) => {
          const f = e.target.files?.[0]
          if (f) handleFile(f)
          e.target.value = ''
        }}
      />
      <input
        ref={sampleRef}
        type="file"
        accept="image/*"
        className="hidden"
        onChange={(e) => {
          const f = e.target.files?.[0]
          if (f) handleFile(f)
          e.target.value = ''
        }}
      />
    </Screen>
  )
}

/** Phosphor's Image icon is re-exported as `Image`, which clashes with the component name; use the alias. */
const imageIcon = ImageIcon
