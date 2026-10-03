# Data map

What data Smart Health needs, what it is used for, where it comes from, and what is missing. The source of truth for the datasets is [plan/smart_health_data_plan.xlsx](plan/smart_health_data_plan.xlsx); how and when each one is loaded is in [../docs/backlog/details/e1-data-foundation.md](../docs/backlog/details/e1-data-foundation.md). Data policy: only the datasets in the hackathon download manifest and the GlucoBench Kaggle link are allowed. Anything else needs the owner's OK first ([README.md](README.md)).

**Status words**

| Status | Meaning |
|---|---|
| Dataset | Real data from a cited dataset |
| Simulated | Built from cited data, marked `entry_source = demo_dataset` or simulated, and disclosed |
| User-entered | Typed or photographed in the app by the person. Not from a dataset |
| Missing | No cited source has it |
| Needs your OK | Cannot be used until the owner approves |

## 1. Data from datasets (use now)

| Need | Used for | Source | Link | Status |
|---|---|---|---|---|
| Glucose sensor readings | Food response, time in range, day traces, momentum | CGMacros (#5), BIG IDEAs (#4) | [CGMacros](https://physionet.org/content/cgmacros/), [BIG IDEAs](https://physionet.org/content/big-ideas-glycemic-wearable/) | Dataset. Only CGMacros has T2D (14 people). BIG IDEAs people are not diabetic |
| Meals and macros | Meal log, personal food response | CGMacros, BIG IDEAs | same | Dataset. US foods, no sodium |
| Meal photos | Testing how well photo logging estimates nutrition | CGMacros | [CGMacros](https://physionet.org/content/cgmacros/) | Dataset, evaluation only |
| Watch heart rate and steps | Trends, momentum, day traces | CGMacros (Fitbit columns), BIG IDEAs | same | Dataset |
| Stress signals and HRV | Stress proxy on the timeline | BIG IDEAs (research wristband, not a consumer watch) | [BIG IDEAs](https://physionet.org/content/big-ideas-glycemic-wearable/) | Dataset |
| Second watch format, sleep, activity | Proves the import works on any device | Fitbit (#14) | [Fitbit](https://www.kaggle.com/datasets/arashnic/fitbit) | Dataset. 30 users, 2016, sleep missing for some |
| Patient profile and labs | Realistic demo patient | CGMacros `bio.csv`, NHANES | [NHANES 2017-18](https://wwwn.cdc.gov/nchs/nhanes/continuousnhanes/default.aspx?BeginYear=2017), [NHANES 2021-23](https://wwwn.cdc.gov/nchs/nhanes/continuousnhanes/default.aspx?BeginYear=2021) | Dataset |
| Starting baselines | Normal ranges before 10 days of a person's own data | NHANES | same | Dataset. US adults, never shown as targets |
| Realistic medicine mix | The demo patient's regimen | NHANES | same | Dataset |
| Drug names, classes, uses, side effects | Scan matching (E3-2), the explainer (E4-1) | 250k Medicines (#20) | [250k Medicines](https://www.kaggle.com/datasets/shudhanshusingh/250k-medicines-usage-side-effects-and-substitutes) | Dataset. Not authoritative, source is "various" |
| Nutrient sanity check | Flags AI meal estimates that look off | Open Food Facts (#17), NHANES dietary files | [Open Food Facts](https://www.kaggle.com/datasets/openfoodfacts/world-food-facts) | Dataset. Packaged and US foods only |
| Timeline format | Pipeline test file | GlucoBench | [GlucoBench](https://www.kaggle.com/datasets/omenkj/glucobench-glucose-monitoring-and-lifestyle-data) | Dataset, fixture only. Source unverified, possibly synthetic |
| Disease to specialist | "Who to ask" in the doctor questions | Doctor Specialty (#37) | [Doctor Specialty](https://www.kaggle.com/datasets/ebrahimelgazar/doctor-specialist-recommendation-system) | Dataset. Weak provenance, routing only |

## 2. Missing data, and what we do about it

| Need | Closest cited data | Link | Status |
|---|---|---|---|
| Sodium per meal | AI estimate from the photo or text | [Open Food Facts](https://www.kaggle.com/datasets/openfoodfacts/world-food-facts) | Missing. Estimated, labelled "Estimated" until the user confirms |
| Singapore foods with glucose response | AI macros for any dish name. Measured response only from CGMacros (US foods) | [CGMacros](https://physionet.org/content/cgmacros/) | Missing. Accept the limit |
| Drug-to-drug interactions | The 250k Medicines interactions column, if it exists | [250k Medicines](https://www.kaggle.com/datasets/shudhanshusingh/250k-medicines-usage-side-effects-and-substitutes) | **Needs your OK.** Unverified: if the column is thin, the clash checker (E6-1) cannot work |
| Supplement and TCM interactions | None | none | **Needs your OK.** Shows "not checked" |
| Medicine label photos | None. MIMIC labels are text only | [MIMIC-IV-Note](https://physionet.org/content/mimic-iv-note/), [MIMIC labels](https://physionet.org/content/medication-labels-mimic-note/) | **Needs your OK.** Blocks scanner testing (E3-1, E3-3) |
| Missed-dose patterns and reasons | Drug Reviews (side-effect wording only) | [Drug Reviews](https://archive.ics.uci.edu/dataset/461) | Missing. Simulated |
| 60-day continuous history | CGMacros (about 10 days), Fitbit (about 31 days) | [CGMacros](https://physionet.org/content/cgmacros/), [Fitbit](https://www.kaggle.com/datasets/arashnic/fitbit) | Missing. Simulated |
| Mood and stress ratings | GlucoBench stress (unverified), BIG IDEAs signals | [GlucoBench](https://www.kaggle.com/datasets/omenkj/glucobench-glucose-monitoring-and-lifestyle-data), [BIG IDEAs](https://physionet.org/content/big-ideas-glycemic-wearable/) | Missing. Simulated |
| Blood oxygen (SpO2) | Brief trend beside glucose and heart rate | No cited dataset is known to hold it | none | Missing. Simulated and labelled in the demo; a real watch source needs your OK |
| Blood pressure over time | NHANES (one visit only) | [NHANES 2017-18](https://wwwn.cdc.gov/nchs/nhanes/continuousnhanes/default.aspx?BeginYear=2017) | Missing. Simulated |
| Logged workouts | Derive from step and heart-rate bursts | [CGMacros](https://physionet.org/content/cgmacros/), [Fitbit](https://www.kaggle.com/datasets/arashnic/fitbit) | Missing. Simulated |
| Lab history (HbA1c, lipids, kidney) | Single time points only | [CGMacros](https://physionet.org/content/cgmacros/), [NHANES 2017-18](https://wwwn.cdc.gov/nchs/nhanes/continuousnhanes/default.aspx?BeginYear=2017) | Missing. Simulated |
| Clinical thresholds, screening intervals, red-flag symptoms | None. These are rules, not data | none | **Needs your OK.** Needs clinician review. Blocks urgent alerts (E11-1) |
| Lifestyle guidance text (for example HPB) | None | none | **Needs your OK.** Nudges stay team-written templates |
| Real Mi Watch data | Fitbit, CGMacros and BIG IDEAs | none | **Needs your OK.** A teammate export would be needed |
| Chinese, Malay, Tamil explanations | None | none | Missing. Machine translation with no reviewed reference |

## 3. Data the user enters in the app (not from a dataset)

| Data | How it is entered | Notes |
|---|---|---|
| Daily meals | Photo or text, then the AI estimates the macros | Stored as `inferred`, shown "Estimated" until the user confirms or edits. The glucose rise is always measured, never estimated |
| Glucose readings | Typed from a glucometer | Sensor readings come from a device, not typed |
| Doses taken and miss reasons | Tap Taken, pick a reason | Feeds adherence and the brief |
| Workouts | Typed, or accepted from a watch suggestion | |
| Symptoms, mood and sleep check-ins | Picker and 1 to 5 ratings. A symptom also stores the sensor glucose and trend at that moment, when it happened, and optional detail (duration, side, meal relation) | See prd.md F6 |
| Emergency contact | Typed once, with consent | Name, phone, email and how to alert them. Never sent to an AI model |
| Awareness of lows | One question after a low | "Did you feel it before your sensor alerted you?" |
| Medicine labels | Photo, then reviewed and confirmed | Nothing saves until confirmed |
| Profile, conditions, allergies, medicines | Onboarding form or chat | |
| Appointments and questions for the doctor | Typed | |
| Blood pressure, weight, lab results | Typed, only if the person has them | |

In the demo these are all simulated. In real use they are the daily data the product depends on, so a gap in logging is a gap in the brief. The brief's data completeness bar shows how much each stream has.

## 4. Biggest open risks

- Interaction data (blocks E6-1, the clash checker).
- Medicine label photos (block scanner testing in E3-1 and E3-3).
- Clinical thresholds and red-flag symptoms (block urgent alerts in E11-1).

## 5. Datasets listed as "later" (not needed now)

[Stress and exercise wearable](https://physionet.org/content/wearable-device-dataset/) · [Autonomic Aging](https://physionet.org/content/autonomic-aging-cardiovascular/) · [Cerebral Vasoregulation in Diabetes](https://physionet.org/content/cerebral-vasoreg-diabetes/) · [Diabetes 130 US Hospitals](https://archive.ics.uci.edu/dataset/296) · [BRFSS Diabetes Indicators](https://www.kaggle.com/datasets/alexteboul/diabetes-health-indicators-dataset) · [MIMIC-IV](https://physionet.org/content/mimiciv/)
