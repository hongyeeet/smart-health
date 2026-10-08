import { useEffect, useRef, useState } from 'react'
import { useParams } from 'react-router-dom'
import { useAskDoctorAbout, useExplainMed, useMed } from '@/data/hooks'
import type { MedicationDetail } from '@/data/types'
import { useUi } from '@/state/store'
import { Header, Screen } from '@/ui/layout'
import { Alert, Button, Card, Field, SectionTitle, Skeleton, SourceTag, StatusPill } from '@/ui/primitives'
import { Clock, Info, Stethoscope } from '@/ui/icons'

const DEFAULT_TELL =
  'Tell your doctor or pharmacist about any side effect that worries you, or if you are unsure whether to take a dose.'

/** The strength is shown under the name unless it was never entered or the name already says it ("Amlodipine 5 mg"). */
const strengthSub = (m: MedicationDetail) =>
  m.strength && m.strength !== 'Strength not entered' && !m.name.toLowerCase().replace(/\s+/g, '').includes(m.strength.toLowerCase().replace(/\s+/g, ''))
    ? m.strength
    : undefined

/** How the person takes it. Always from their own label, never from the explanation (prd F3). */
function howYouTakeIt(m: MedicationDetail): string {
  if (m.asNeeded) return 'Only when you need it. There are no set times.'
  if (!m.times.length) return 'No dose times set. Ask your pharmacist how to take it.'
  const n = m.times.length
  const often = n === 1 ? 'Once a day' : n === 2 ? 'Twice a day' : `${n} times a day`
  return `${often}, at ${m.times.join(' and ')}${m.withFood ? ', with food' : ''}.`
}

/**
 * H6 — Medicine detail (prd F3). What the medicine is for and its common side effects, in plain words, with the web pages they came
 * from, how the person takes it (from their own label), when to tell the doctor, and a box to save a question for the doctor.
 * The explanation is made the first time the page is opened (a web search, up to 30 seconds) and kept, so it is instant after that.
 */
export function MedDetail() {
  const { id = '' } = useParams()
  const { data: m, isLoading, isError, error } = useMed(id)
  const explain = useExplainMed()
  const ask = useAskDoctorAbout()
  const toast = useUi((s) => s.showToast)
  const [question, setQuestion] = useState('')
  const [asked, setAsked] = useState(false)
  const started = useRef<string | null>(null)

  // Make the explanation once, when the page opens and there is none yet. The ref stops a second search if the page renders twice.
  const { mutate: makeExplanation } = explain
  useEffect(() => {
    if (m && !m.explanation && started.current !== m.id) {
      started.current = m.id
      makeExplanation(m.id)
    }
  }, [m, makeExplanation])

  if (isLoading)
    return (
      <Screen>
        <Header title="Medicine" back backTo="H1" />
        <Skeleton className="h-60" />
      </Screen>
    )
  if (isError || !m)
    return (
      <Screen>
        <Header title="Medicine" back backTo="H1" />
        <Alert tone="warn">{error instanceof Error ? error.message : 'We could not open this medicine.'}</Alert>
      </Screen>
    )

  const ex = explain.data ?? m.explanation
  const looking = !ex && !explain.isError

  const send = () => {
    const text = question.trim()
    if (text.length < 3) return
    ask.mutate({ id: m.id, text: `About ${m.name}${strengthSub(m) ? ' ' + strengthSub(m) : ''}: ${text}` }, {
      onSuccess: () => {
        setQuestion('')
        setAsked(true)
        toast('Added to your doctor questions')
      },
    })
  }

  return (
    <Screen>
      <Header title={m.name} back backTo="H1" sub={strengthSub(m)} />

      {looking && (
        <Card tone="soft" className="flex flex-col gap-3 py-6">
          <Skeleton className="h-16 w-full" />
          <p className="text-body font-bold text-ink2">Looking this up for you…</p>
          <p className="text-sub text-ink3">We read reliable medicine information and write it in plain words. The first time this takes up to half a minute. After that it opens straight away.</p>
        </Card>
      )}

      {explain.isError && !ex && (
        <Alert tone="warn" title="We could not look this up">
          {explain.error instanceof Error ? explain.error.message : 'Please try again in a moment.'}
          <span className="mt-2 block">
            <Button variant="secondary" onClick={() => makeExplanation(m.id)} disabled={explain.isPending}>
              Try again
            </Button>
          </span>
        </Alert>
      )}

      {ex?.status === 'not_identified' && (
        <Card className="flex flex-col gap-1.5">
          <SectionTitle>What it is for</SectionTitle>
          <p className="text-body">We could not tell exactly what this product is, so we are not guessing. Please ask your pharmacist or doctor what it is for. You can add your question below.</p>
        </Card>
      )}

      {ex?.status === 'ready' && (
        <Card className="flex flex-col gap-1.5">
          <SectionTitle>What it is for</SectionTitle>
          <p className="text-body">{ex.purpose}</p>
        </Card>
      )}

      <Card className="flex flex-col gap-1.5">
        <SectionTitle>How you take it (from your own label)</SectionTitle>
        <p className="text-body">{howYouTakeIt(m)}</p>
        {m.directions && <p className="text-sub text-ink2">Your label says: “{m.directions}”</p>}
      </Card>

      {ex?.status === 'ready' && ex.sideEffects.length > 0 && (
        <Card className="flex flex-col gap-1.5">
          <SectionTitle>Common side effects</SectionTitle>
          <ul className="flex flex-col gap-1.5">
            {ex.sideEffects.map((s) => (
              <li key={s} className="flex gap-3 text-body">
                <span className="mt-2.5 h-1.5 w-1.5 flex-none rounded-full bg-brand" aria-hidden />
                {s}
              </li>
            ))}
          </ul>
        </Card>
      )}

      {ex?.status === 'ready' && (
        <Card className="flex flex-col gap-1.5">
          <SectionTitle>When to tell your doctor</SectionTitle>
          <p className="text-body">{ex.tellDoctor || DEFAULT_TELL}</p>
        </Card>
      )}

      {m.refill && (
        <Alert tone="info" icon={Clock} title={`Runs out in about ${m.refill.daysLeft} days`}>
          {m.refill.unitsLeft} tablets or capsules left at your current pace.
        </Alert>
      )}

      {ex && ex.sources.length > 0 && (
        <Card className="flex flex-col gap-2">
          <SectionTitle>Where this comes from</SectionTitle>
          <ul className="flex flex-col gap-1">
            {ex.sources.map((s) => (
              <li key={s.url}>
                <a href={s.url} target="_blank" rel="noopener noreferrer" className="text-sub font-bold text-brand underline underline-offset-4">
                  {s.title}
                </a>
              </li>
            ))}
          </ul>
        </Card>
      )}

      {ex && (
        <div className="flex flex-col gap-2">
          <SourceTag>a web search of medicine information, summarised by AI from your medicine&apos;s name and label. This is not medical advice.</SourceTag>
          <StatusPill tone="info" icon={Info}>
            Not an authoritative drug label
          </StatusPill>
        </div>
      )}

      <Card className="flex flex-col gap-3">
        <SectionTitle>Ask your doctor</SectionTitle>
        <p className="text-sub text-ink2">Write down anything you want to ask. We keep it in your doctor questions for your next visit and for your doctor brief.</p>
        <Field label="Your question" value={question} onChange={(v) => { setQuestion(v); setAsked(false) }} multiline placeholder="For example: Can I take this with my other medicines?" />
        <Button icon={Stethoscope} onClick={send} disabled={question.trim().length < 3 || ask.isPending}>
          {ask.isPending ? 'Saving…' : 'Add to my doctor questions'}
        </Button>
        {ask.isError && <Alert tone="warn">{ask.error instanceof Error ? ask.error.message : 'We could not save your question. Please try again.'}</Alert>}
        {asked && <p className="text-sub font-bold text-brand">Saved. You can add another one.</p>}
      </Card>
    </Screen>
  )
}
