import { useEffect, useRef, useState } from 'react'
import { useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useAskDoctorAbout, useExplainMed, useMed } from '@/data/hooks'
import type { MedicationDetail, MedicineExplanationParts } from '@/data/types'
import { useUi } from '@/state/store'
import { Header, Screen } from '@/ui/layout'
import { Alert, Button, Card, Field, SectionTitle, Skeleton, SourceTag } from '@/ui/primitives'
import { Clock, Stethoscope } from '@/ui/icons'
import { fullName, refillSentence, refillSourceLine, showStrength } from './medicineText'
import { SourceItem, uniqueSources } from './SourceLinks'

/** The strength is shown under the name unless it was never entered or the name already says it ("Amlodipine 5 mg"). */
const strengthSub = (m: MedicationDetail) => (showStrength(m) ? m.strength : undefined)

/** How the person takes it. Always from their own label, never from the explanation (prd F3). */
function howYouTakeIt(m: MedicationDetail, t: Translate): string {
  if (m.asNeeded) return t('medDetail.needed', 'Only when you need it. There are no set times.')
  if (!m.times.length) return t('medDetail.noTimes', 'No dose times set. Ask your pharmacist how to take it.')
  const n = m.times.length
  const often = n === 1 ? t('medDetail.onceADay', 'Once a day') : n === 2 ? t('medDetail.twiceADay', 'Twice a day') : t('medDetail.timesADay', '{{n}} times a day', { n })
  const food = m.withFood ? t('medDetail.withFood', ', with food') : ''
  return `${often}, ${t('medDetail.at', 'at')} ${m.times.join(' and ')}${food}.`
}

type Translate = ReturnType<typeof useTranslation>['t']

/**
 * H6 — Medicine detail (prd F3). What the medicine is for, how it works, what to notice and why timing matters, plus the common side
 * effects, when to tell the doctor, the web pages used (Additional information), how the person takes it (from their own label) and a
 * box to save a question for the doctor. The explanation is made the first time the page is opened (a web search, up to 30 seconds) and
 * kept, so it is instant after that. An explanation in the older layout can be updated with one tap.
 */
export function MedDetail() {
  const { t } = useTranslation()
  const { id = '' } = useParams()
  const { data: m, isLoading, isError, error } = useMed(id)
  const explain = useExplainMed()
  const ask = useAskDoctorAbout()
  const toast = useUi((s) => s.showToast)
  const [question, setQuestion] = useState('')
  const [asked, setAsked] = useState(false)
  const started = useRef<string | null>(null)

  // Make the explanation once, when the page opens and there is none yet. The ref stops a second search if the page renders twice.
  // An explanation in the older layout is not made again here: the person updates it with the button, so nothing costs a search unasked.
  const { mutate: makeExplanation } = explain
  useEffect(() => {
    if (m && !m.explanation && started.current !== m.id) {
      started.current = m.id
      makeExplanation(m.id)
    }
  }, [m, makeExplanation])

  if (isLoading)
    return (
      <Screen narrow>
        <Header title={t('medDetail.title', 'Medicine')} back backTo="H1" />
        <Skeleton className="h-60" />
      </Screen>
    )
  if (isError || !m)
    return (
      <Screen narrow>
        <Header title={t('medDetail.title', 'Medicine')} back backTo="H1" />
        <Alert tone="warn">
          {error instanceof TypeError
            ? t('medDetail.offline', 'We could not reach Equinox. Check your connection and try again.')
            : t('medDetail.couldNotOpen', 'We could not open this medicine.')}
        </Alert>
      </Screen>
    )

  const ex = explain.data ?? m.explanation
  const looking = !ex && !explain.isError
  const parts = ex?.status === 'ready' ? ex.parts ?? null : null
  const olderLayout = ex?.status === 'ready' && !parts

  const PARTS: { key: keyof MedicineExplanationParts; label: string }[] = [
    { key: 'forDiabetes', label: t('medDetail.part.forDiabetes', 'What it is for in your diabetes') },
    { key: 'howItWorks', label: t('medDetail.part.howItWorks', 'How it works') },
    { key: 'whatYouMayNotice', label: t('medDetail.part.whatYouMayNotice', 'What you may notice') },
    { key: 'whyTimingMatters', label: t('medDetail.part.whyTimingMatters', 'Why timing matters') },
  ]

  const send = () => {
    const text = question.trim()
    if (text.length < 3) return
    ask.mutate({ id: m.id, text: `About ${m.name}${strengthSub(m) ? ' ' + strengthSub(m) : ''}: ${text}` }, {
      onSuccess: () => {
        setQuestion('')
        setAsked(true)
        toast(t('medDetail.added', 'Added to your doctor questions'))
      },
    })
  }

  return (
    <Screen narrow>
      <Header title={m.name} back backTo="H1" sub={strengthSub(m)} />

      {looking && (
        <Card tone="soft" className="flex flex-col gap-3 py-6">
          <Skeleton className="h-16 w-full" />
          <p className="text-body font-bold text-ink2">{t('medDetail.looking', 'Looking this up for you…')}</p>
          <p className="text-sub text-ink3">
            {t('medDetail.lookingBody', 'We read reliable medicine information and write it in plain words. The first time this takes up to half a minute. After that it opens straight away.')}
          </p>
        </Card>
      )}

      {explain.isError && (
        <Alert tone="warn" title={ex ? t('medDetail.couldNotUpdate', 'We could not update this information') : t('medDetail.couldNotLook', 'We could not look this up')}>
          {explain.error instanceof TypeError
            ? t('medDetail.offline', 'We could not reach Equinox. Check your connection and try again.')
            : explain.error instanceof Error && explain.error.message && !/^\d{3}/.test(explain.error.message)
              ? explain.error.message
              : t('medDetail.tryLater', 'Please try again in a moment.')}
          {ex && <span className="mt-2 block">{t('medDetail.stillShown', 'The information shown below is the last one we saved.')}</span>}
          <span className="mt-2 block">
            <Button variant="secondary" onClick={() => makeExplanation(m.id)} disabled={explain.isPending}>
              {t('medDetail.tryAgain', 'Try again')}
            </Button>
          </span>
        </Alert>
      )}

      {ex?.status === 'not_identified' && (
        <Card className="flex flex-col gap-1.5">
          <SectionTitle>{t('medDetail.whatFor', 'What it is for')}</SectionTitle>
          <p className="text-body">
            {t('medDetail.notIdentified', 'We could not tell exactly what this product is, so we are not guessing. Please ask your pharmacist or doctor what it is for. You can add your question below.')}
          </p>
        </Card>
      )}

      {parts && (
        <Card className="flex flex-col gap-4">
          {PARTS.map((p) => (
            <div key={p.key} className="flex flex-col gap-1">
              <h2 className="text-sub font-bold text-ink2">{p.label}</h2>
              <p className="text-body">{parts[p.key] || t('medDetail.notFound', 'Not found in the pages we read.')}</p>
            </div>
          ))}
        </Card>
      )}

      {olderLayout && ex && (
        <Card className="flex flex-col gap-3">
          <SectionTitle>{t('medDetail.whatFor', 'What it is for')}</SectionTitle>
          <p className="text-body">{ex.purpose}</p>
          <p className="text-sub text-ink3">{t('medDetail.olderLayout', 'This was written in an older layout. Update it to see the four short parts.')}</p>
          <Button variant="secondary" size="md" onClick={() => makeExplanation(m.id)} disabled={explain.isPending}>
            {explain.isPending ? t('medDetail.updating', 'Updating…') : t('medDetail.update', 'Update this information')}
          </Button>
        </Card>
      )}

      <Card className="flex flex-col gap-1.5">
        <SectionTitle>{t('medDetail.howTake', 'How you take it (from your own label)')}</SectionTitle>
        <p className="text-body">{howYouTakeIt(m, t)}</p>
        {m.directions && (
          <p className="text-sub text-ink2">
            {t('medDetail.labelSays', 'Your label says:')} “{m.directions}”
          </p>
        )}
      </Card>

      {ex?.status === 'ready' && ex.sideEffects.length > 0 && (
        <Card className="flex flex-col gap-1.5">
          <SectionTitle>{t('medDetail.sideEffects', 'Common side effects')}</SectionTitle>
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
          <SectionTitle>{t('medDetail.tellDoctor', 'When to tell your doctor')}</SectionTitle>
          <p className="text-body">{ex.tellDoctor || t('medDetail.defaultTell', 'Tell your doctor or pharmacist about any side effect that worries you, or if you are unsure whether to take a dose.')}</p>
        </Card>
      )}

      {m.refill && (
        <Alert tone="info" icon={Clock}>
          <span className="block font-bold">{refillSentence(fullName(m), m.refill.daysLeft, t)}</span>
          <span className="mt-1 block">
            {m.refillSource === 'estimate'
              ? t('medDetail.unitsMay', '{{n}} tablets or capsules may be left at your current pace.', { n: m.refill.unitsLeft })
              : t('medDetail.unitsLeft', '{{n}} tablets or capsules left at your current pace.', { n: m.refill.unitsLeft })}
          </span>
          {refillSourceLine(m.refillSource, t) && <span className="mt-1 block text-micro text-ink2">{refillSourceLine(m.refillSource, t)}</span>}
        </Alert>
      )}

      {ex && ex.sources.length > 0 && (
        <Card className="flex flex-col gap-2">
          <SectionTitle>{t('medDetail.additional', 'Additional information')}</SectionTitle>
          <ul className="flex flex-col gap-1">
            {uniqueSources(ex.sources).map((s) => (
              <li key={s.title} className="text-sub">
                <SourceItem s={s} linkClass="font-bold text-brand underline underline-offset-4" />
              </li>
            ))}
          </ul>
        </Card>
      )}

      {ex && (
        <div className="flex flex-col gap-1">
          <SourceTag>{t('medDetail.sourceTag', "a web search of medicine information, summarised by AI from your medicine's name and label. This is not medical advice.")}</SourceTag>
          <p className="text-micro text-ink3">{t('medDetail.notAuthoritative', 'Not an authoritative drug label')}</p>
        </div>
      )}

      <Card className="flex flex-col gap-3">
        <SectionTitle>{t('medDetail.askDoctor', 'Ask your doctor')}</SectionTitle>
        <p className="text-sub text-ink2">
          {t('medDetail.askBody', 'Write down anything you want to ask. We keep it in your doctor questions for your next visit and for your doctor brief.')}
        </p>
        <Field
          label={t('medDetail.yourQuestion', 'Your question')}
          value={question}
          onChange={(v) => {
            setQuestion(v)
            setAsked(false)
          }}
          multiline
          placeholder={t('medDetail.questionPlaceholder', 'For example: Can I take this with my other medicines?')}
        />
        <Button icon={Stethoscope} onClick={send} disabled={question.trim().length < 3 || ask.isPending}>
          {ask.isPending ? t('medDetail.saving', 'Saving…') : t('medDetail.addQuestion', 'Add to my doctor questions')}
        </Button>
        {ask.isError && (
          <Alert tone="warn">{ask.error instanceof Error ? ask.error.message : t('medDetail.couldNotSaveQ', 'We could not save your question. Please try again.')}</Alert>
        )}
        {asked && <p className="text-sub font-bold text-brand">{t('medDetail.saved', 'Saved. You can add another one.')}</p>}
      </Card>
    </Screen>
  )
}
