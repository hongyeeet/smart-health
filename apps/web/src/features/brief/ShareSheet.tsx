/**
 * L2 — Share with my doctor. Make a read-only link to the same report the person sees on L1 and L3, for a chosen period, that stops
 * working after a chosen time or when it is turned off. Opened from L1 with `go('L2', { sheet: { days } })`.
 */
import { useState } from 'react'
import { appConfig } from '@/config/app'
import { Segmented } from '@/ui/controls'
import { Sheet } from '@/ui/Sheet'
import { Alert, Button, Skeleton, StatusPill, type Tone } from '@/ui/primitives'
import { formatWhen, shareAddress, useCreateShare, useRevokeShare, useShares, type ShareCreated, type ShareDays, type ShareHours, type ShareStatus } from './shareApi'

const STATUS: Record<ShareStatus, { tone: Tone; label: string }> = {
  active: { tone: 'ok', label: 'Active' },
  expired: { tone: 'neutral', label: 'Expired' },
  revoked: { tone: 'neutral', label: 'Turned off' },
}

export function ShareSheet({ onClose, days: fromScreen }: { onClose: () => void; days?: ShareDays } & Record<string, unknown>) {
  const [days, setDays] = useState<ShareDays>(fromScreen ?? 14)
  const [hours, setHours] = useState<ShareHours>(appConfig.shareLinkHours as ShareHours)
  const [made, setMade] = useState<ShareCreated | null>(null)
  const [copied, setCopied] = useState<'yes' | 'no' | null>(null)
  const create = useCreateShare()
  const revoke = useRevokeShare()
  const shares = useShares()

  const address = made ? shareAddress(made.path) : ''

  async function copy() {
    try {
      await navigator.clipboard.writeText(address)
      setCopied('yes')
    } catch {
      setCopied('no')
    }
  }

  return (
    <Sheet title="Share with my doctor" onClose={onClose}>
      <div className="flex flex-col gap-5">
        <p className="text-body text-ink2">Make a link your doctor can open on any device. It needs no sign-in. You can turn it off at any time.</p>

        <Segmented
          label="Period to share"
          value={days}
          onChange={setDays}
          options={[
            { value: 7, label: '7 days' },
            { value: 14, label: '14 days' },
            { value: 30, label: '30 days' },
            { value: 90, label: '90 days' },
          ]}
        />
        <Segmented
          label="How long the link works"
          value={hours}
          onChange={setHours}
          options={[
            { value: 24, label: '1 day' },
            { value: 72, label: '3 days' },
            { value: 168, label: '7 days' },
          ]}
        />

        <section className="flex flex-col gap-2">
          <h3 className="text-sub font-bold text-ink">What your doctor will see</h3>
          <p className="text-body text-ink2">
            The same report as your doctor brief for the period above: a summary of your glucose readings, symptoms with the glucose reading nearby, your medicines and how often you took them, activity and wellbeing,
            the alerts, and your open questions.
          </p>
          <p className="text-body text-ink2">Your name, sex and age, and your diagnosis. Nothing else: not your chat, your photos or your emergency contact.</p>
          <p className="text-body text-ink2">Anyone with the link can read the report until it stops working. Send it only to your doctor.</p>
        </section>

        {create.isError && <Alert tone="warn">{create.error instanceof Error ? create.error.message : 'We could not make the link. Please try again.'}</Alert>}
        <Button
          disabled={create.isPending}
          onClick={() =>
            create.mutate(
              { days, hours },
              {
                onSuccess: (res) => {
                  setMade(res)
                  setCopied(null)
                },
              },
            )
          }
        >
          {create.isPending ? 'Making the link…' : 'Create link'}
        </Button>

        {made && (
          <section className="flex flex-col gap-3 rounded-[14px] border border-line bg-card p-4" aria-label="Your new link">
            <h3 className="text-sub font-bold text-ink">Your link</h3>
            <input
              readOnly
              value={address}
              aria-label="Link to copy"
              onFocus={(e) => e.currentTarget.select()}
              className="min-h-12 w-full break-all rounded-[14px] border-2 border-line bg-well px-3 py-2 text-sub text-ink"
            />
            <Button variant="secondary" size="md" onClick={copy}>
              Copy link
            </Button>
            <p role="status" className="text-sub text-ink2">
              {copied === 'yes' && 'Link copied.'}
              {copied === 'no' && 'We could not copy it. Select the link above and copy it.'}
              {copied === null && `This link works until ${formatWhen(made.expiresAt)}. It is shown only now, so copy it before you close this.`}
            </p>
          </section>
        )}

        <section className="flex flex-col gap-3">
          <h3 className="text-sub font-bold text-ink">Links you have made</h3>
          {revoke.isError && <Alert tone="warn">We could not turn that link off. Please try again.</Alert>}
          {shares.isLoading && <Skeleton className="h-24" />}
          {shares.isError && <Alert tone="warn">We could not load your links just now.</Alert>}
          {shares.data && shares.data.length === 0 && <p className="text-body text-ink2">No links yet.</p>}
          {shares.data && shares.data.length > 0 && (
            <ul className="flex flex-col divide-y divide-line">
              {shares.data.map((s) => (
                <li key={s.id} className="flex flex-col gap-1.5 py-3 first:pt-0 last:pb-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <StatusPill tone={STATUS[s.status].tone}>{STATUS[s.status].label}</StatusPill>
                    <span className="text-sub text-ink2">
                      {s.days} days, made {formatWhen(s.createdAt)}
                    </span>
                  </div>
                  <p className="text-sub text-ink2">
                    {s.status === 'active' && `Works until ${formatWhen(s.expiresAt)}.`}
                    {s.status === 'expired' && `Expired on ${formatWhen(s.expiresAt)}.`}
                    {s.status === 'revoked' && 'Turned off by you.'}{' '}
                    {s.viewCount === 0 ? 'Not opened yet.' : `Opened ${s.viewCount} ${s.viewCount === 1 ? 'time' : 'times'}, last on ${formatWhen(s.lastViewedAt ?? s.createdAt)}.`}
                  </p>
                  {s.status === 'active' && (
                    <Button
                      variant="secondary"
                      size="md"
                      disabled={revoke.isPending}
                      aria-label={`Turn off the link made ${formatWhen(s.createdAt)}`}
                      onClick={() =>
                        revoke.mutate(s.id, {
                          onSuccess: () => {
                            if (made?.id === s.id) setMade(null)
                          },
                        })
                      }
                    >
                      Turn off this link
                    </Button>
                  )}
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </Sheet>
  )
}
