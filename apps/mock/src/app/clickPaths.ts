import type { RouteId } from './routeIds'

/** The click paths the prototype must support end to end. Steps are route ids, so they are checked against the registry. */
export const clickPaths: { title: string; steps: { id: RouteId; action: string }[] }[] = [
  { title: '1. Morning', steps: [{ id: 'B1', action: 'Tap Taken' }, { id: 'B1', action: 'Tell us why' }, { id: 'H7', action: 'Pick a reason, Save' }, { id: 'B1', action: 'Back on Home' }] },
  { title: '2. Meal', steps: [{ id: 'E1', action: 'Meal' }, { id: 'E2', action: 'Chicken rice, High salt flag, Save' }, { id: 'E6', action: 'See your day' }, { id: 'D1', action: 'New meal marker' }] },
  { title: '3. Workout', steps: [{ id: 'B1', action: 'Log a walk' }, { id: 'F1', action: 'Confirm the watch card, Save' }, { id: 'E6', action: 'See your activity' }, { id: 'C4', action: 'Then See your day' }, { id: 'D1', action: 'Workout marker' }] },
  { title: '4. Explore a day', steps: [{ id: 'C1', action: 'Tap a day in Your week' }, { id: 'D1', action: 'Tap a marker' }, { id: 'D2', action: 'Detail sheet' }] },
  { title: '5. New medicine', steps: [{ id: 'H1', action: 'Scan a label' }, { id: 'H2', action: 'Take photo' }, { id: 'H3', action: 'Confirm' }, { id: 'H4', action: 'Add to my medicines' }, { id: 'H5', action: 'Add to my doctor questions' }, { id: 'K3', action: 'Care plan' }] },
  { title: '6. Safety moment', steps: [{ id: 'I1', action: 'Try the skip-my-metformin question' }, { id: 'I1', action: 'Safety reply, Add to my doctor questions' }, { id: 'K3', action: 'Care plan' }] },
  { title: '7. Learning', steps: [{ id: 'K1', action: 'What Smart Health has learned' }, { id: 'K2', action: 'Week 1 and week 8, tap a fact\'s evidence' }, { id: 'C4', action: 'The related insight' }] },
  { title: '8. Doctor visit', steps: [{ id: 'B1', action: 'Prepare for the visit' }, { id: 'K3', action: 'Generate my doctor brief' }, { id: 'L1', action: 'Share with my doctor' }, { id: 'L2', action: 'Create link' }] },
  { title: '9. Urgent', steps: [{ id: 'E3', action: 'Log 2.8 mmol/L (or the demo panel)' }, { id: 'J1', action: "I'm okay now" }, { id: 'B1', action: 'Back on Home' }] },
]
