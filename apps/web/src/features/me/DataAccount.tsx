/**
 * K8. Data and account: the one home for the person's own information. From the top: their details (each with an "edit"), their
 * emergency contacts (more than one allowed), their consents (including the reminder emails), then download my data and delete my account.
 * A deletion is only recorded here (in the activity log) and processed within 30 days; nothing is deleted by this screen.
 * The old Privacy and consent (K6) and Emergency contact (K9) screens open here, at their section.
 */
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useLocation } from 'react-router-dom'
import { useUi } from '@/state/store'
import { Header, Screen } from '@/ui/layout'
import { Download, Trash } from '@/ui/icons'
import { Alert, Button, Card, Field, SectionTitle } from '@/ui/primitives'
import { downloadMyData, useRequestDeletion, type DeletionRequest } from './settings/api'
import { fmtDate } from './settings/rules'
import { ConsentsSection } from './account/ConsentsSection'
import { ContactsSection } from './account/ContactsSection'
import { InfoSection } from './account/InfoSection'

/** Download my data, and ask for the account and its data to be deleted. The delete card is last and outlined in red. */
function YourData() {
  const { t } = useTranslation()
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
      showToast(t('me.data.downloading', 'Your file is downloading'))
    } catch (e) {
      setDownloadError(e instanceof Error ? e.message : t('me.data.downloadNotStarted', 'The download did not start.'))
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
    <section id="data" className="flex scroll-mt-4 flex-col gap-3">
      <SectionTitle>{t('me.account.dataTitle', 'Your data')}</SectionTitle>
      {/* the two cards side by side, equal height, from a laptop up */}
      <div className="grid gap-4 lg:grid-cols-2 lg:items-stretch [&>*]:min-w-0">
      <Card as="section" className="flex h-full flex-col gap-3">
        <SectionTitle>{t('me.data.download', 'Download my data')}</SectionTitle>
        <p className="text-body text-ink2">
          {t(
            'me.data.downloadInfo',
            'Get a file with what you have logged, your profile, your consent history, and your medicines and doses. You can keep it or share it with someone you trust.',
          )}
        </p>
        {downloadError && (
          <Alert tone="warn">
            {t('me.data.downloadFailed', 'The file could not be downloaded.')} {downloadError}
          </Alert>
        )}
        <Button variant="secondary" icon={Download} disabled={downloading} onClick={download} className="mt-auto">
          {downloading ? t('me.data.preparing', 'Preparing your file') : t('me.data.downloadButton', 'Download my data')}
        </Button>
      </Card>

      <Card as="section" className="flex h-full flex-col gap-3 border-danger/40">
        <SectionTitle>{t('me.data.deleteTitle', 'Delete my account and data')}</SectionTitle>

        {requested ? (
          <Alert tone="ok" title={t('me.data.received', 'Request received')}>
            <p>{t('me.data.received2', 'Your request is recorded. We will process it within 30 days, by {{date}}. Nothing has been deleted yet.', { date: fmtDate(requested.processBy) })}</p>
          </Alert>
        ) : step === 'start' ? (
          <>
            <p className="text-body text-ink2">
              {t(
                'me.data.deleteWhat',
                'This removes your logs, your medicines and doses, your profile, and what Smart Health has learned about you. It cannot be undone.',
              )}
            </p>
            <Button variant="secondary" icon={Trash} onClick={() => setStep('confirm')}>
              {t('me.data.deleteTitle', 'Delete my account and data')}
            </Button>
          </>
        ) : (
          <div className="flex flex-col gap-3">
            <p className="text-body text-ink2">
              {t('me.data.typeToConfirm', 'To confirm, type DELETE in capital letters. We will then record your request, and process it within 30 days.')}
            </p>
            <Field label={t('me.data.typeLabel', 'Type DELETE to confirm')} value={typed} onChange={setTyped} placeholder="DELETE" />
            {del.isError && (
              <Alert tone="warn">
                {t('me.data.notRecorded', 'The request was not recorded.')} {del.error?.message}
              </Alert>
            )}
            <Button variant="danger" disabled={typed !== 'DELETE' || del.isPending} onClick={sendRequest}>
              {t('me.data.requestDeletion', 'Request deletion')}
            </Button>
            <Button
              variant="ghost"
              onClick={() => {
                setStep('start')
                setTyped('')
              }}
            >
              {t('me.data.keepAccount', 'Keep my account')}
            </Button>
          </div>
        )}
      </Card>
      </div>

    </section>
  )
}

export function DataAccount() {
  const { t } = useTranslation()
  const { hash } = useLocation()

  // K6 and K9 land here with #consents or #contacts: scroll to that section once the page is on screen
  useEffect(() => {
    if (!hash) return
    const id = window.setTimeout(() => document.getElementById(hash.slice(1))?.scrollIntoView({ block: 'start' }), 120)
    return () => window.clearTimeout(id)
  }, [hash])

  return (
    <Screen>
      <Header title={t('me.data.title', 'Data and account')} back backTo="K1" />
      <InfoSection />
      <div className="grid gap-6 lg:grid-cols-2 lg:items-start lg:gap-8 [&>*]:min-w-0">
        <ContactsSection />
        <ConsentsSection />
      </div>
      <YourData />
      <p className="text-sub text-ink3">{t('me.data.log', 'Requests and changes to your settings are kept in an activity log that cannot be changed.')}</p>
    </Screen>
  )
}
