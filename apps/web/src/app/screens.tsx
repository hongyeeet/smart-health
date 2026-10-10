import type { ComponentType } from 'react'
import { Navigate } from 'react-router-dom'
import { NotBuilt } from './NotBuilt'
import { WorkoutTracker } from '@/features/workout/WorkoutTracker'
import { ScanFrame } from '@/features/scan/ScanFrame'
import { ScanReview } from '@/features/scan/ScanReview'
import { ScanPlan } from '@/features/scan/ScanPlan'
import { AddByHand } from '@/features/meds/AddByHand'
import { MedDetail } from '@/features/meds/MedDetail'
import { MedList } from '@/features/meds/MedList'
import { LogHub } from '@/features/log/LogHub'
import { LogDone } from '@/features/log/LogDone'
import { LogSymptom } from '@/features/log/LogSymptom'
import { LogCheckin } from '@/features/log/LogCheckin'
import { LogMeal } from '@/features/log/LogMeal'
import { LogWorkout } from '@/features/workout/LogWorkout'
import { Home } from '@/features/home/Home'
import { Me } from '@/features/me/Me'
import { Learned } from '@/features/me/Learned'
import { Progress } from '@/features/me/Progress'
import { LunchIdeas } from '@/features/log/LunchIdeas'
import { Notifications } from '@/features/home/Notifications'
import { InteractionDetail } from '@/features/alerts/InteractionDetail'
import { BriefHome } from '@/features/brief/BriefHome'
import { Overview } from '@/features/insights/Overview'
import { GlucoseTab } from '@/features/insights/Glucose'
import { FoodTab } from '@/features/insights/Food'
import { ActivityTab } from '@/features/insights/Activity'
import { SleepTab } from '@/features/insights/Sleep'
import { MedicationTab } from '@/features/insights/Medication'
import { Sprint } from '@/features/insights/Sprint'
import { Welcome } from '@/features/onboarding/Welcome'
import { Eligibility } from '@/features/onboarding/Eligibility'
import { AboutYou } from '@/features/onboarding/AboutYou'
import { Summary } from '@/features/onboarding/Summary'
import { Day } from '@/features/day/Day'
import { Chat } from '@/features/chat/Chat'
import { Review } from '@/features/review/Review'
import { ChatSetup } from '@/features/onboarding/ChatSetup'
import { Care } from '@/features/me/Care'
import { Sources } from '@/features/me/Sources'
import { Language } from '@/features/me/Language'
import { Privacy } from '@/features/me/Privacy'
import { Appointment } from '@/features/me/Appointment'
import { DataAccount } from '@/features/me/DataAccount'
import { Contact } from '@/features/me/Contact'
import { Urgent } from '@/features/urgent/Urgent'
import { ROUTES, routeIds, type RouteId } from './routeIds'

/**
 * Built screens, by route id. Anything not listed here shows the "not built yet" placeholder, so the whole
 * navigation works from day one and each screen is swapped in as it is built.
 *
 *   import { Home } from '@/features/home/Home'
 *   export const built: Partial<Record<RouteId, ComponentType>> = { B1: Home }
 */
export const built: Partial<Record<RouteId, ComponentType>> = {
  A1: Welcome,
  A2: Eligibility,
  A3: AboutYou,
  A4: ChatSetup,
  /** Folded into A3: devices and routine is step 7 there. */
  A5: () => <Navigate to="/welcome/about?step=7" replace />,
  A6: Summary,
  B1: Home,
  C1: Overview,
  C2: GlucoseTab,
  C3: FoodTab,
  C4: ActivityTab,
  C5: SleepTab,
  C6: MedicationTab,
  C8: Sprint,
  D1: Day,
  I1: Chat,
  K11: Review,
  J1: Urgent,
  K3: Care,
  K4: Sources,
  K5: Language,
  K6: Privacy,
  K7: Appointment,
  K8: DataAccount,
  K9: Contact,
  B2: Notifications,
  K1: Me,
  L1: BriefHome,
  K2: Learned,
  K10: Progress,
  F1: LogWorkout,
  F2: WorkoutTracker,
  H1: MedList,
  H2: ScanFrame,
  H3: ScanReview,
  H4: ScanPlan,
  H5: InteractionDetail,
  H6: MedDetail,
  H8: AddByHand,
  E1: LogHub,
  E2: LogMeal,
  E4: LogSymptom,
  E5: LogCheckin,
  E6: LogDone,
  E8: LunchIdeas,
}

export function screenFor(id: RouteId): ComponentType {
  return built[id] ?? (() => <NotBuilt id={id} />)
}

/** Screens that are routes (not sheets, not pages outside the app frame). */
export const routedIds: RouteId[] = routeIds.filter((id) => ROUTES[id].kind === 'tab' || ROUTES[id].kind === 'screen')
