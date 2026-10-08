import { useAcknowledgeClash, useAskAboutClash, useClash, useRunClashCheck } from '@/data/hooks'
import { useUi } from '@/state/store'
import { Alert, Button } from '@/ui/primitives'
import { CheckCircle, Stethoscope, Warning } from '@/ui/icons'

/**
 * The medicine clash box on the Meds page (prd F5). It appears only when two of the person's medicines may clash, found by the drug-pair
 * rules or by the AI check that runs after every medicine is added. With nothing found there is no box, which is not the same as "safe":
 * supplements and herbal products still say "Not checked". The wording never tells the person to stop a medicine.
 */
export function ClashBox() {
  const { data } = useClash()
  const ask = useAskAboutClash()
  const ack = useAcknowledgeClash()
  const rerun = useRunClashCheck()
  const toast = useUi((s) => s.showToast)
  if (!data) return null

  return (
    <>
      {data.checking && <p className="px-1 text-sub text-ink3">Checking your medicines for clashes…</p>}
      {/* No box can mean "nothing found" or "could not check": when the check did not finish, say so instead of looking like all clear. */}
      {!data.checking && data.checkIncomplete && data.alerts.length === 0 && (
        <Alert tone="info" title="We could not finish checking for clashes">
          <p>This is not the same as all clear. Please try again, or ask your pharmacist to look at your list.</p>
          <div className="mt-2">
            <Button size="md" variant="secondary" className="!w-auto" disabled={rerun.isPending} onClick={() => rerun.mutate()}>
              Check again
            </Button>
          </div>
        </Alert>
      )}
      {data.alerts.length > 0 && (
        <Alert tone="warn" icon={Warning} title="Medicines may clash. Check with your doctor.">
          <div className="mt-2 flex flex-col gap-4">
            {data.alerts.map((a) => (
              <div key={a.id} className="flex flex-col gap-2">
                <p className="text-body font-bold">{a.text}</p>
                {a.summary && <p className="text-body">{a.summary}</p>}
                {a.sources.length === 0 && <p className="text-micro text-ink3">No web page was found for this. It is an AI suggestion, so please check it with your pharmacist. Not medical advice.</p>}
                {a.sources.length > 0 && (
                  <p className="text-micro text-ink3">
                    From:{' '}
                    {a.sources.map((s, i) => (
                      <span key={s.url}>
                        {i > 0 && ', '}
                        <a href={s.url} target="_blank" rel="noopener noreferrer" className="underline underline-offset-2">
                          {s.title}
                        </a>
                      </span>
                    ))}
                    . Not medical advice.
                  </p>
                )}
                <div className="flex flex-wrap gap-2">
                  {a.questionAdded ? (
                    <p className="flex min-h-12 items-center gap-2 px-1 text-sub font-bold text-ok">
                      <CheckCircle size={22} weight="fill" aria-hidden /> Added to your doctor questions
                    </p>
                  ) : (
                    <Button
                      size="md"
                      variant="secondary"
                      icon={Stethoscope}
                      className="!w-auto"
                      disabled={ask.isPending}
                      onClick={() => ask.mutate(a.id, { onSuccess: () => toast('Added to your doctor questions') })}
                    >
                      {ask.isPending && ask.variables === a.id ? 'Saving…' : 'Add to my doctor questions'}
                    </Button>
                  )}
                  <Button size="md" variant="ghost" className="!w-auto" disabled={ack.isPending} onClick={() => ack.mutate(a.id)}>
                    I have checked with my doctor
                  </Button>
                </div>
              </div>
            ))}
          </div>
          {ask.isError && <p className="mt-3 text-sub text-ink2">We could not save your question just now. Please try again.</p>}
          {data.checkIncomplete && <p className="mt-3 text-sub text-ink2">The full check could not finish just now, so there may be more to see later.</p>}
        </Alert>
      )}
    </>
  )
}
