# Equinox

**The diabetes companion that remembers, adapts and grows.**

*Team Shika: Teo Hong Yi, Joely Lim, Damien Chua. AI CAN DO IT Tencent Cloud Hackathon Singapore 2026. Healthcare, Challenge 2 "AI Healthier Every Day", Scenario 2: Type 2 diabetes self-care.*

---

## 1. Project Overview

Equinox is an AI health companion for adults with Type 2 diabetes. It learns each person from their own meals, medicines, glucose, activity and symptoms, helps them every day, and turns the weeks between clinic visits into a clear brief for their doctor. It explains, organises and reminds. It never advises on medication and never diagnoses.

- **Target scenarios:** a new prescription, daily medicines, supplement clashes, eating local food, glucose spikes and symptoms, and the ten-minute consultation.
- **Target users:** adults of about 45 to 65 with Type 2 diabetes, and the doctors who see them.
- **Value proposition:** patients understand and keep to their treatment; doctors get a trustworthy one-page brief with no new system to learn.
- **What we built:** a working mobile-first web app in four languages (English, Mandarin, Malay, Tamil), with medicine scanning, reminders, meal suggestions, a visible learning memory, a safe assistant, and a doctor brief with a private share link.

## 2. Real-World Scenario Insights

- **Source of pain points:** published data show diabetes is common in Singapore, with about 699,100 adults affected and about 37 % undiagnosed ([IDF](https://diabetesatlas.org/data-by-location/country/singapore/)). Long-term treatment is often not followed as prescribed ([WHO](https://www.who.int/news/item/01-07-2003-failure-to-take-prescribed-medicine-for-chronic-diseases-is-a-massive-world-wide-problem)). We have not yet interviewed patients.
- **Target audience:** Type 2 diabetes patients, their families, clinicians and pharmacists.
- **Core problem solved:** a person's diabetes data exists, but nobody joins it up, explains it safely, or hands it to the doctor in a usable form.

## 3. Comprehensive Solution Design

- **Business architecture:** capture the person's data, understand it, help them act every day, then report to the doctor. The patient owns the data and decides what the doctor sees.
- **Technical architecture:**
  - React web app on Firebase Hosting.
  - Python (FastAPI) backend on Cloud Run, with a PostgreSQL database on Supabase.
  - Gemini 3.8 Flash on Vertex AI for chat, photos and wording.
  - JEV as the safety gate that decides but never writes.
  - Workato for reminder e-mails and calendar events.
- **How prompts drive the AI:** code chooses what the model may see, the prompt sets strict rules and an output format, and code checks the result before the person sees it. Prompts never allow dosing advice or guessing, and are versioned for auditing.

## 4. Business Value

- **Defined impact:** fewer missed doses, better-informed consultations, and earlier notice when health drifts.
- **Measurable targets (pilot goals, not results):**
  - Medicine adherence up 10 to 15 points.
  - Logging on at least 70 % of days by week 8.
  - Doctors rating the brief at least 3.5 out of 5.
  - Zero medication-advice leaks in safety testing.
- **Cost control:** every AI call goes through one gateway with daily caps, and each dish picture is made once and reused.
- **Status:** built and working; not yet trialled with patients. The next steps are real sign-in, clinical review and a supervised pilot.
