import { Sheet } from '@/ui/Sheet'
import { Button } from '@/ui/primitives'
import type { WhyTopic } from './shared'

const WHY: Record<WhyTopic, { title: string; shows: string; from: string; limit: string }> = {
  week: {
    title: 'Your week',
    shows: 'One square for each of the last 7 days, for glucose in range, meals logged, active minutes, sleep, stress and doses taken. A darker square means more of it.',
    from: 'Your glucose sensor, your watch, and what you logged in the app.',
    limit: 'A dash means there was no data that day. It does not mean zero. The colour shows how much, not whether it is good or bad.',
  },
  glucose: {
    title: 'Glucose',
    shows: 'How much of the time your glucose was in each band, your average, and your usual morning (fasting) level.',
    from: 'Your glucose sensor. Fasting means your average between 5 and 7 am. Your usual range is worked out from the 60 days before the period shown.',
    limit: 'Estimated A1c (GMI) is worked out from your sensor average. It is not a lab result and can differ from one.',
  },
  food: {
    title: 'Food',
    shows: 'The meals you logged, with salt and sugar flagged, and how much your glucose rose in the 2 hours after each food.',
    from: 'Your logged meals (the amounts are estimates from your photos) and your glucose sensor.',
    limit: 'A food is only ranked once you have logged it at least twice with the sensor on. One meal is not a pattern. Other things, like what else you ate or how active you were, also affect the rise.',
  },
  activity: {
    title: 'Activity',
    shows: 'Your minutes of moderate or vigorous activity and strength sessions against the weekly goals, the last 4 weeks, your workouts and your steps.',
    from: 'Workouts you logged and steps from your watch. The weekly goals are 150 active minutes and 2 strength sessions.',
    limit: 'The glucose change after a workout is shown only when the sensor was worn. Goals here are general. Your doctor can set yours.',
  },
  sleep: {
    title: 'Sleep and stress',
    shows: 'Hours slept each night, and your mood and stress check-ins.',
    from: 'Sleep from your watch. Mood and stress are the ratings you gave in your check-ins.',
    limit: 'Stress is how you rated it, not something measured. Bedtime regularity is not shown yet.',
  },
  medication: {
    title: 'Medication',
    shows: 'Each medicine, day by day: taken, taken late, not confirmed or missed, and the reasons you gave for missed doses.',
    from: 'The doses you confirmed in the app. A dose counts as late when it was taken more than an hour after its time.',
    limit: 'Adherence counts prescription medicines only. A dose nobody answered is counted as not taken. Missing a dose is information for your doctor, not a score.',
  },
  findings: {
    title: 'What your history shows',
    shows: 'Things that tend to go together in your own data, such as how your morning glucose looked after an evening walk.',
    from: 'Your own history, compared by the app each night. A finding is shown only when it is based on at least 5 matching events.',
    limit: 'These are associated with, not proven. They do not show that one thing causes the other. Worth mentioning to your doctor, who can tell you what they mean for you.',
  },
  sprint: {
    title: 'Glucose sensor sprint',
    shows: 'A summary of your latest 14 days of sensor data.',
    from: 'Your glucose sensor and the meals you logged.',
    limit: 'It is not yet a timed sprint with a start and an end. That comes with the sensor connection.',
  },
}

/** C7 — Why am I seeing this? What a chart shows, where the data comes from, and what it cannot tell you. Opened from every chart in C1 to C6. */
export function WhySheet({ onClose, topic = 'week' }: { onClose: () => void; topic?: WhyTopic }) {
  const w = WHY[topic] ?? WHY.week
  return (
    <Sheet title="Why am I seeing this?" onClose={onClose} label={`Why am I seeing ${w.title}?`}>
      <div className="flex flex-col gap-4">
        <p className="font-serif text-h2 font-medium">{w.title}</p>
        <div className="flex flex-col gap-1">
          <p className="text-sub font-bold text-ink3">What it shows</p>
          <p className="text-body">{w.shows}</p>
        </div>
        <div className="flex flex-col gap-1">
          <p className="text-sub font-bold text-ink3">Where it comes from</p>
          <p className="text-body">{w.from}</p>
        </div>
        <div className="flex flex-col gap-1">
          <p className="text-sub font-bold text-ink3">What to keep in mind</p>
          <p className="text-body">{w.limit}</p>
        </div>
        <p className="text-sub text-ink3">Every number is worked out by the app from your own data. Nothing here is advice or a diagnosis.</p>
        <Button onClick={onClose}>Got it</Button>
      </div>
    </Sheet>
  )
}
