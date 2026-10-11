/**
 * E5 — Mood and sleep check-in.
 *
 * Four Rating components (mood, stress, sleep quality, energy), each 1–5. Nothing is pre-selected: the person answers the
 * questions they want to. At least one answer is needed to save; unanswered questions are not saved (null), never a guessed number.
 * Saves via useFinishLog → E6.
 */
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useFinishLog } from './useFinishLog'
import { Header, Footer, Screen } from '@/ui/layout'
import { Rating } from '@/ui/controls'
import { Alert, Button } from '@/ui/primitives'

export function LogCheckin() {
  const { t } = useTranslation()
  /* null until the person taps a number: no default answer is ever saved */
  const [mood, setMood] = useState<number | null>(null)
  const [stress, setStress] = useState<number | null>(null)
  const [sleep, setSleep] = useState<number | null>(null)
  const [energy, setEnergy] = useState<number | null>(null)
  const { save, pending, error } = useFinishLog()
  const answered = [mood, stress, sleep, energy].some((v) => v != null)
  return (
    <Screen narrow>
      <Header title={t('log.checkin.title', 'Mood and sleep')} back backTo="E1" sub={t('log.checkin.sub', 'Thirty seconds. Tap a number for each.')} />
      <Rating label={t('log.checkin.mood', 'Mood')} value={mood} onChange={setMood} lowLabel={t('log.checkin.moodLow', 'Very low')} highLabel={t('log.checkin.moodHigh', 'Very good')} />
      <Rating label={t('log.checkin.stress', 'Stress')} value={stress} onChange={setStress} lowLabel={t('log.checkin.stressLow', 'Calm')} highLabel={t('log.checkin.stressHigh', 'Very stressed')} />
      <Rating label={t('log.checkin.sleep', 'Sleep quality')} value={sleep} onChange={setSleep} lowLabel={t('log.checkin.sleepLow', 'Very poor')} highLabel={t('log.checkin.sleepHigh', 'Excellent')} />
      <Rating label={t('log.checkin.energy', 'Energy')} value={energy} onChange={setEnergy} lowLabel={t('log.checkin.energyLow', 'Exhausted')} highLabel={t('log.checkin.energyHigh', 'Energised')} />
      {error && <Alert tone="danger">{error}</Alert>}
      <Footer>
        {!answered && <p className="text-sub text-ink2">{t('log.checkin.needOne', 'Tap a number for at least one question to save.')}</p>}
        <Button
          disabled={pending || !answered}
          onClick={() =>
            save({
              kind: 'checkin',
              // only the answers the person gave are sent; the others are left out, so they are stored as not answered
              ...(mood != null ? { mood } : {}),
              ...(stress != null ? { stress } : {}),
              ...(sleep != null ? { sleep } : {}),
              ...(energy != null ? { energy } : {}),
            })
          }
        >
          {t('log.checkin.save', 'Save check-in')}
        </Button>
      </Footer>
    </Screen>
  )
}
