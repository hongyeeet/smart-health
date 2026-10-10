/**
 * K8. Download my data as a file, and ask for the account and its data to be deleted.
 * A deletion is only recorded here (in the activity log) and processed within 30 days; nothing is deleted by this screen.
 */
import { useState } from 'react'
import { useUi } from '@/state/store'
import { Header, Screen } from '@/ui/layout'
import { Download, Trash } from '@/ui/icons'
import { Alert, Button, Card, Field, SectionTitle } from '@/ui/primitives'
import { downloadMyData, useRequestDeletion, type DeletionRequest } from './settings/api'
import { fmtDate } from './settings/rules'

export function DataAccount() {
  const showToast = useUi((s) => s.showToast)
  const [downloading, setDownloading] = useState(false)
  const [downloadError, setDownloadError] = useState<string | null>(null)
  const [step, setStep] = useState<'start' | 'confirm'>('start')
  const [typed, setTyped] = useState('')
  const [requested, setRequested] = useState<DeletionRequest | null>(null)
  const del = useRequestDeletion()

  const download = async () => {
    setDownloading(true)
    setDownloadError(null)
    try {
      await downloadMyData()
      showToast('Your file is downloading')
    } catch (e) {
      setDownloadError(e instanceof Error ? e.message : 'The download did not start.')
    } finally {
      setDownloading(false)
    }
  }

  const sendRequest = () =>
    del.mutate('DELETE', {
      onSuccess: (r) => {
        setRequested(r)
        setStep('start')
      },
    })

  return (
    <Screen>
      <Header title="Data and account" back backTo="K1" />

      <Card as="section" className="flex flex-col gap-3">
        <SectionTitle>Download my data</SectionTitle>
        <p className="text-body text-ink2">
          Get a file with what you have logged, your profile, your consent history, and your medicines and doses. You can keep it or share it with someone you trust.
        </p>
        {downloadError && <Alert tone="warn">The file could not be downloaded. {downloadError}</Alert>}
        <Button variant="secondary" icon={Download} disabled={downloading} onClick={download}>
          {downloading ? 'Preparing your file' : 'Download my data'}
        </Button>
      </Card>

      <Card as="section" className="flex flex-col gap-3 border-danger/40">
        <SectionTitle>Delete my account and data</SectionTitle>

        {requested ? (
          <Alert tone="ok" title="Request received">
            <p>Your request is recorded. We will process it within 30 days, by {fmtDate(requested.processBy)}. Nothing has been deleted yet.</p>
          </Alert>
        ) : step === 'start' ? (
          <>
            <p className="text-body text-ink2">
              This removes your logs, your medicines and doses, your profile, and what Smart Health has learned about you. It cannot be undone.
            </p>
            <Button variant="secondary" icon={Trash} onClick={() => setStep('confirm')}>
              Delete my account and data
            </Button>
          </>
        ) : (
          <div className="flex flex-col gap-3">
            <p className="text-body text-ink2">To confirm, type DELETE in capital letters. We will then record your request, and process it within 30 days.</p>
            <Field label="Type DELETE to confirm" value={typed} onChange={setTyped} placeholder="DELETE" />
            {del.isError && <Alert tone="warn">The request was not recorded. {del.error?.message}</Alert>}
            <Button variant="danger" disabled={typed !== 'DELETE' || del.isPending} onClick={sendRequest}>
              Request deletion
            </Button>
            <Button
              variant="ghost"
              onClick={() => {
                setStep('start')
                setTyped('')
              }}
            >
              Keep my account
            </Button>
          </div>
        )}
      </Card>

      <p className="text-sub text-ink3">Requests and changes to your settings are kept in an activity log that cannot be changed.</p>
    </Screen>
  )
}
