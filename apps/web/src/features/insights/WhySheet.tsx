import { useTranslation } from 'react-i18next'
import { Sheet } from '@/ui/Sheet'
import { Button } from '@/ui/primitives'
import type { WhyTopic } from './shared'

/** C7 — Why am I seeing this? What a chart shows, where the data comes from, and what it cannot tell you. Opened from every chart in C1 to C6. */
export function WhySheet({ onClose, topic = 'week' }: { onClose: () => void; topic?: WhyTopic }) {
  const { t } = useTranslation()
  const WHY: Record<WhyTopic, { title: string; shows: string; from: string; limit: string }> = {
    week: {
      title: t('insights.why.week.title', 'Your days'),
      shows: t('insights.why.week.shows', 'A calendar with one square for each day of the month you pick. Choose one measure at a time: glucose in range, meals logged, active minutes, sleep, stress or doses taken. A darker square means more of it. Tap a day to open it.'),
      from: t('insights.why.week.from', 'Your glucose sensor, your watch, and what you logged in the app.'),
      limit: t('insights.why.week.limit', 'A dash means there was no data that day. It does not mean zero. The colour shows how much, not whether it is good or bad.'),
    },
    glucose: {
      title: t('insights.why.glucose.title', 'Glucose'),
      shows: t('insights.why.glucose.shows', 'How much of the time your glucose was in each band, your average, and your usual morning (fasting) level.'),
      from: t(
        'insights.why.glucose.from',
        'Your glucose sensor. Fasting means your average between 5 and 7 am. Your usual range is worked out from the 60 days before the period shown.',
      ),
      limit: t('insights.why.glucose.limit', 'Estimated A1c (GMI) is worked out from your sensor average. It is not a lab result and can differ from one.'),
    },
    food: {
      title: t('insights.why.food.title', 'Food'),
      shows: t('insights.why.food.shows', 'The meals you logged, with salt and sugar flagged, and how much your glucose rose in the 2 hours after each food.'),
      from: t('insights.why.food.from', 'Your logged meals (the amounts are estimates from your photos) and your glucose sensor.'),
      limit: t(
        'insights.why.food.limit',
        'A food is only ranked once you have logged it at least twice with the sensor on. One meal is not a pattern. Other things, like what else you ate or how active you were, also affect the rise.',
      ),
    },
    activity: {
      title: t('insights.why.activity.title', 'Activity'),
      shows: t(
        'insights.why.activity.showsV2',
        'Your steps, what you did, your heart rate and blood oxygen from your watch, your minutes of light, moderate and vigorous activity by day, week or month, and your recent workouts.',
      ),
      from: t(
        'insights.why.activity.fromV2',
        'Workouts you logged, with the effort as you rated it, and steps, heart rate and blood oxygen from your watch.',
      ),
      limit: t('insights.why.activity.limitV2', 'The glucose change after a workout is shown only when the sensor was worn. A workout you did not rate is not counted in the minutes. A watch on the wrist is less accurate than a fingertip meter.'),
    },
    sleep: {
      title: t('insights.why.sleep.title', 'Sleep and stress'),
      shows: t('insights.why.sleep.showsV2', 'Hours slept each night, your heart rate and blood oxygen, your mood and stress check-ins and the blood pressure you logged.'),
      from: t('insights.why.sleep.fromV2', 'Sleep, heart rate and blood oxygen from your watch. Mood and stress are the ratings you gave in your check-ins. Blood pressure is what you typed in.'),
      limit: t('insights.why.sleep.limitV2', 'Stress is how you rated it, not something measured. Blood pressure is shown as logged and is not judged here. A watch on the wrist is less accurate than a fingertip meter.'),
    },
    medication: {
      title: t('insights.why.medication.title', 'Medication'),
      shows: t(
        'insights.why.medication.showsV2',
        'A calendar of your doses, month by month: for each medicine and each day, taken, taken late, not confirmed or missed, and the reasons you gave for missed doses in the month shown.',
      ),
      from: t('insights.why.medication.from', 'The doses you confirmed in the app. A dose counts as late when it was taken more than an hour after its time.'),
      limit: t(
        'insights.why.medication.limit',
        'Adherence counts prescription medicines only. A dose nobody answered is counted as not taken. Missing a dose is information for your doctor, not a score.',
      ),
    },
    findings: {
      title: t('insights.why.findings.title', 'What your history shows'),
      shows: t(
        'insights.why.findings.shows',
        'Things that tend to go together in your own data, such as how your morning glucose looked after an evening walk.',
      ),
      from: t(
        'insights.why.findings.from',
        'Your own history, compared by the app each night. A finding is shown only when it is based on at least 5 matching events.',
      ),
      limit: t(
        'insights.why.findings.limit',
        'These are associated with, not proven. They do not show that one thing causes the other. Worth mentioning to your doctor, who can tell you what they mean for you.',
      ),
    },
    sprint: {
      title: t('insights.why.sprint.title', 'Glucose sensor sprint'),
      shows: t('insights.why.sprint.shows', 'A summary of your latest 14 days of sensor data.'),
      from: t('insights.why.sprint.from', 'Your glucose sensor and the meals you logged.'),
      limit: t('insights.why.sprint.limit', 'It is not yet a timed sprint with a start and an end. That comes with the sensor connection.'),
    },
  }
  const w = WHY[topic] ?? WHY.week
  return (
    <Sheet title={t('insights.why.title', 'Why am I seeing this?')} onClose={onClose} label={t('insights.why.label', 'Why am I seeing {{title}}?', { title: w.title })}>
      <div className="flex flex-col gap-4">
        <p className="font-serif text-h2 font-medium">{w.title}</p>
        <div className="flex flex-col gap-1">
          <p className="text-sub font-bold text-ink3">{t('insights.why.whatShows', 'What it shows')}</p>
          <p className="text-body">{w.shows}</p>
        </div>
        <div className="flex flex-col gap-1">
          <p className="text-sub font-bold text-ink3">{t('insights.why.whereFrom', 'Where it comes from')}</p>
          <p className="text-body">{w.from}</p>
        </div>
        <div className="flex flex-col gap-1">
          <p className="text-sub font-bold text-ink3">{t('insights.why.keepInMind', 'What to keep in mind')}</p>
          <p className="text-body">{w.limit}</p>
        </div>
        <p className="text-sub text-ink3">
          {t('insights.why.footer', 'Every number is worked out by the app from your own data. Nothing here is advice or a diagnosis.')}
        </p>
        <Button onClick={onClose}>{t('insights.why.gotIt', 'Got it')}</Button>
      </div>
    </Sheet>
  )
}
