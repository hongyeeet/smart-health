# Equinox

**The diabetes companion that remembers, adapts and grows.**

Team Shika: Teo Hong Yi, Joely Lim, Damien Chua. AI CAN DO IT Tencent Cloud Hackathon Singapore 2026. Healthcare track, Challenge 2 "AI Healthier Every Day", Scenario 2: Type 2 diabetes self-care.

---

## 1. Project Overview

Equinox is an AI health companion for adults with Type 2 diabetes. It learns each person from their own meals, medicines, glucose, activity and symptoms, helps them every day, and turns the weeks between clinic visits into a clear brief for their doctor. It explains, organises and reminds. It never advises on medication and never diagnoses.

**Target scenarios.** Equinox supports the moments where people struggle most: understanding a new prescription, taking medicines on time, checking whether a supplement clashes with a medicine, eating local food, making sense of a glucose spike, and getting the most out of a ten-minute consultation.

**Target users.** Adults of about 45 to 65 with Type 2 diabetes, who use a smartphone but are not technical, and the doctors who see them.

**Value proposition.** Patients understand their treatment and keep to it. Doctors get a trustworthy one-page brief with no new system to learn.

**What we built.** A working mobile-first web app in four languages (English, Mandarin, Malay and Tamil). A person can scan a medicine label and get a plain-words explanation, receive reminders, log meals by photo, browse suggestions for lighter dishes, ask a safe assistant questions about their own records, see what the app has learned about them, and share a doctor brief by a private link.

---

## 2. Real-World Scenario Insights

**Source of the pain points.** Diabetes is common in Singapore. The International Diabetes Federation estimates about 699,100 adults are affected, and about 37 percent of cases are undiagnosed ([IDF Diabetes Atlas](https://diabetesatlas.org/data-by-location/country/singapore/)). The World Health Organization has long reported that people often do not take long-term treatment as prescribed ([WHO](https://www.who.int/news/item/01-07-2003-failure-to-take-prescribed-medicine-for-chronic-diseases-is-a-massive-world-wide-problem)). A patient sees a doctor for about ten minutes every few months and manages alone the rest of the time. We have not yet interviewed patients, and we say so openly.

**Target audience.** People with Type 2 diabetes, their families, the clinicians who see them, and pharmacists.

**Core problem solved.** A person's diabetes data exists on a watch, in a pill box, on a phone and in their memory, but nobody joins it up, explains it safely, or hands it to the doctor in a usable form. Equinox does all three.

---

## 3. Comprehensive Solution Design

**Business architecture.** Equinox follows one simple chain: capture the person's data, understand it, help them act every day, then report to the doctor. The patient owns the data and decides what the doctor can see, through a link they can switch off. The app is built to be trusted by a clinical partner: it is bounded, logged and never gives medication advice.

**Technical architecture.** The web app is built with React and hosted on Firebase. The backend is Python with FastAPI on Google Cloud Run, with a PostgreSQL database on Supabase. Gemini 3.8 Flash on Google Vertex AI reads photos, answers questions and words summaries. A decision model called JEV acts as a safety gate: it can stop a request or reply but never writes text. Workato sends reminder e-mails and calendar events.

**How prompts drive the AI.** The code decides what the model is allowed to see. The prompt then sets strict rules and a fixed output format. The code checks the result before the person ever reads it. Our prompts tell the model to treat text from photos and messages as data and never as instructions, to leave a field empty rather than guess, never to give dosing advice, and to answer only from the information it is given. Prompts are versioned so each result can be audited.

---

## 4. Business Value

**Defined impact.** Fewer missed doses, better-informed consultations, and earlier notice when a person's health starts to drift.

**Measurable targets.** These are goals for a pilot, not results. We aim for medicine adherence to rise by 10 to 15 percentage points, for people to log on at least 70 percent of days by week eight, for doctors to rate the brief at least 3.5 out of 5, and for zero medication-advice leaks in safety testing.

**Cost control.** Every AI call goes through one gateway with daily limits, and each suggested dish picture is created once and reused for everyone.

**Where we are.** Equinox is built and working. It has not yet been trialled with patients. The next steps are real sign-in, clinical review of the thresholds, and a supervised pilot with a clinic.
