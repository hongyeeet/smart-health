import { useNavigate } from 'react-router-dom'
import { href } from '@/app/routeIds'
import { Footer, Header, Screen, Split } from '@/ui/layout'
import { Alert, Button, Card, SectionTitle, Skeleton } from '@/ui/primitives'
import { Camera, Image as ImageIcon, Info, PencilSimple } from '@/ui/icons'
import { useLabelPicker } from './useLabelPicker'

/**
 * H2 — Scan a label: camera/upload screen with framing tips, and the way out to typing it in by hand (H8).
 * "Take photo" captures from the camera on a phone and opens the file picker on a laptop. The photo goes to
 * POST /scans (see useLabelPicker) and the scan id is passed to the review screen (H3) in router state.
 */
export function ScanFrame() {
  const navigate = useNavigate()
  const picker = useLabelPicker()

  return (
    <Screen>
      <Header title="Scan a label" back backTo="H1" sub="Step 1 of 3. Take or upload a photo of the label." />
      {picker.busy ? (
        <Card tone="soft" className="flex flex-col items-center gap-3 py-10">
          <Skeleton className="h-48 w-full" />
          <p className="text-body font-bold text-ink2">Reading your label…</p>
          <p className="text-sub text-ink3">This takes a few seconds.</p>
        </Card>
      ) : (
        <>
          <Split>
            <div
              className="relative flex h-72 items-center justify-center overflow-hidden rounded-card bg-[#101815]"
              role="img"
              aria-label="Camera view with a frame to line the label up in"
            >
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
          {picker.error && (
            <Alert tone="danger" title="Could not read the label">
              {picker.error}
            </Alert>
          )}
          <Footer>
            <Button icon={Camera} onClick={picker.takePhoto}>
              Take photo
            </Button>
            <Button variant="secondary" icon={ImageIcon} onClick={picker.uploadPhoto}>
              Upload a photo
            </Button>
            <Button variant="ghost" icon={PencilSimple} onClick={() => navigate(href('H8'))}>
              Type it in by hand
            </Button>
          </Footer>
          <Card tone="soft" className="flex items-start gap-3">
            <Info size={20} className="mt-0.5 flex-none text-ink3" aria-hidden />
            <p className="text-sub text-ink2">
              If your name or ID number is printed on the label, cover it before you take the photo. Nothing is saved until you
              check it and confirm, and if a field can't be read you type it yourself.
            </p>
          </Card>
        </>
      )}
      {picker.inputs}
    </Screen>
  )
}
