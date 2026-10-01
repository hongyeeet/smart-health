import { useState } from 'react'
import { appConfig } from '@/config/app'
import { useRevoke, useShare } from '@/data/hooks'
import { useUi } from '@/state/store'
import { Sheet } from '@/ui/Sheet'
import { Alert, Button, StatusPill, Toggle } from '@/ui/primitives'
import { LinkBreak, Link as LinkIcon, ShieldCheck } from '@/ui/icons'

/** Sharing needs consent. The link expires, can be revoked, and the doctor sees exactly what the patient sees. */
export function ShareSheet({ onClose }: { onClose: () => void }) {
  const consent = useUi((s) => s.consentShare)
  const setConsent = useUi((s) => s.setConsent)
  const toast = useUi((s) => s.showToast)
  const share = useShare()
  const revoke = useRevoke()
  const [link, setLink] = useState<{ url: string; expiresIn: string } | null>(null)
  return (
    <Sheet title="Share with my doctor" onClose={onClose}>
      <div className="flex flex-col gap-4">
        <div className="flex items-center justify-between gap-4 rounded-card border border-line p-3.5">
          <div>
            <p className="text-body font-bold">I agree to share my brief</p>
            <p className="text-sub text-ink2">Only people with the link can open it.</p>
          </div>
          <Toggle on={consent} onChange={(v) => setConsent('consentShare', v)} label="Consent to share my doctor brief" />
        </div>
        {!link ? (
          <Button
            icon={LinkIcon}
            disabled={!consent}
            onClick={() => void share.mutateAsync().then((d) => setLink(d))}
          >
            Create link
          </Button>
        ) : (
          <div className="flex flex-col gap-3">
            <div className="rounded-card bg-well p-3.5">
              <p className="break-all font-mono text-sub">{link.url}</p>
              <p className="mt-1 text-sub text-ink2">Expires in {appConfig.shareLinkHours} hours</p>
            </div>
            <Button variant="secondary" onClick={() => toast('Link copied')}>
              Copy link
            </Button>
            <Button
              variant="ghost"
              icon={LinkBreak}
              onClick={() =>
                revoke.mutate(undefined, {
                  onSuccess: () => {
                    setLink(null)
                    toast('Access revoked. The link no longer works.')
                  },
                })
              }
            >
              Revoke access
            </Button>
          </div>
        )}
        <Alert tone="info" icon={ShieldCheck}>
          Your doctor sees exactly what you see. Nothing is hidden.
        </Alert>
        <StatusPill tone="neutral">Each open of the link is logged.</StatusPill>
      </div>
    </Sheet>
  )
}
