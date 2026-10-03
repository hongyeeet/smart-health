import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { Providers } from './Providers'
import { Shell } from './Shell'
import { Home } from '@/features/home/Home'
import { Notifications } from '@/features/home/Notifications'
import { ActivityInsights, FoodInsights, GlucoseInsights, MedicationInsights, Overview, SleepInsights, SprintPage } from '@/features/insights/pages'
import { DayView } from '@/features/day/DayView'
import { LogHub } from '@/features/log/LogHub'
import { LogCheckin, LogDone, LogGlucose, LogMeal, LogSymptom } from '@/features/log/LogScreens'
import { LogWorkout } from '@/features/log/LogWorkout'
import { AddByHand, MedList, ScanFrame, ScanPlan, ScanReview } from '@/features/meds/Meds'
import { MedDetail } from '@/features/meds/MedDetail'
import { Chat } from '@/features/chat/Chat'
import { Urgent } from '@/features/urgent/Urgent'
import { Me } from '@/features/me/Me'
import { Learned } from '@/features/me/Learned'
import { CarePlan, DataAccount, EmergencyContactScreen, LanguageDisplay, PlanAppointment, Privacy, Sources } from '@/features/me/MeScreens'
import { BriefPreview } from '@/features/brief/BriefPreview'
import { BriefA4 } from '@/features/brief/BriefA4'
import { AboutYou, ChatSetup, ConnectData, Eligibility, Welcome } from '@/features/onboarding/Onboarding'
import { ScreenIndex } from '@/features/index/ScreenIndex'

/** Paths come from routeIds.ts. If you change one there, change it here too: the index page warns on mismatches. */
export function App() {
  return (
    <Providers>
      <BrowserRouter>
        <Routes>
          <Route path="/screens" element={<ScreenIndex />} />
          <Route path="/brief/a4" element={<BriefA4 />} />
          <Route element={<Shell />}>
            <Route index element={<Home />} />
            <Route path="notifications" element={<Notifications />} />

            <Route path="welcome" element={<Welcome />} />
            <Route path="welcome/eligibility" element={<Eligibility />} />
            <Route path="welcome/about" element={<AboutYou />} />
            <Route path="welcome/chat" element={<ChatSetup />} />
            <Route path="welcome/connect" element={<ConnectData />} />

            <Route path="insights" element={<Overview />} />
            <Route path="insights/glucose" element={<GlucoseInsights />} />
            <Route path="insights/food" element={<FoodInsights />} />
            <Route path="insights/activity" element={<ActivityInsights />} />
            <Route path="insights/sleep" element={<SleepInsights />} />
            <Route path="insights/medication" element={<MedicationInsights />} />
            <Route path="insights/sprint" element={<SprintPage />} />
            <Route path="day/:date" element={<DayView />} />

            <Route path="log" element={<LogHub />} />
            <Route path="log/meal" element={<LogMeal />} />
            <Route path="log/glucose" element={<LogGlucose />} />
            <Route path="log/symptom" element={<LogSymptom />} />
            <Route path="log/checkin" element={<LogCheckin />} />
            <Route path="log/workout" element={<LogWorkout />} />
            <Route path="log/done" element={<LogDone />} />

            <Route path="meds" element={<MedList />} />
            <Route path="meds/scan" element={<ScanFrame />} />
            <Route path="meds/scan/review" element={<ScanReview />} />
            <Route path="meds/scan/plan" element={<ScanPlan />} />
            <Route path="meds/add" element={<AddByHand />} />
            <Route path="meds/:id" element={<MedDetail />} />

            <Route path="chat" element={<Chat />} />
            <Route path="urgent" element={<Urgent />} />

            <Route path="me" element={<Me />} />
            <Route path="me/learned" element={<Learned />} />
            <Route path="me/care" element={<CarePlan />} />
            <Route path="me/sources" element={<Sources />} />
            <Route path="me/language" element={<LanguageDisplay />} />
            <Route path="me/privacy" element={<Privacy />} />
            <Route path="me/appointment" element={<PlanAppointment />} />
            <Route path="me/data" element={<DataAccount />} />
            <Route path="me/contact" element={<EmergencyContactScreen />} />
            <Route path="brief" element={<BriefPreview />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </Providers>
  )
}
