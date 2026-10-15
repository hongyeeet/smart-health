# Dataset links

Built from `download_manifest.csv` (48 datasets) and `ckm_datasets_to_download-2.xlsx` (Datasets, NHANES files, Live APIs, How to download). Nothing is downloaded yet. Sizes and licences are as written in the manifest. Which datasets we actually use is in `smart_health_data_plan.xlsx`; this file is only the lookup list. The number in the first column is the **manifest #** used everywhere else in the repo.

Tier 1 = core evidence base, Tier 2 = useful, Tier 3 = prototyping or low value, "Do not use" = excluded by the manifest.


## A. NHANES (CDC), open, no account

| # | Tier | Dataset | Size | Licence | Link |
|---|---|---|---|---|---|
| 1 | Tier 1 | NHANES 2017-2018 CKM panel (27 files) | ~150 MB (core files, excl. dietary/accelerometry) | US public domain (CDC data user agreement) | https://wwwn.cdc.gov/nchs/nhanes/continuousnhanes/default.aspx?BeginYear=2017 |
| 2 | Tier 1 | NHANES 2021-2023 CKM panel (23 files) | ~150 MB (core files, excl. dietary/accelerometry) | US public domain (CDC data user agreement) | https://wwwn.cdc.gov/nchs/nhanes/continuousnhanes/default.aspx?BeginYear=2021 |

## B. PhysioNet, open (click-through licence, no account for wget)

| # | Tier | Dataset | Size | Licence | Link |
|---|---|---|---|---|---|
| 3 | Tier 1 | BIDMC PPG and Respiration Dataset | 207.7 MB | Open Data Commons Attribution License v1.0 | https://physionet.org/content/bidmc/ |
| 4 | Tier 1 | BIG IDEAs Lab Glycemic Variability and Wearable Device Data | 34.1 GB | Open Data Commons Attribution License v1.0 | https://physionet.org/content/big-ideas-glycemic-wearable/ |
| 5 | Tier 1 | CGMacros: a scientific dataset for personalized nutrition and diet monitoring | 627.9 MB | Creative Commons Attribution-NonCommercial-ShareAlike 4.0 In | https://physionet.org/content/cgmacros/ |
| 7 | Tier 1 | MIMIC-IV Clinical Database Demo | 15.5 MB | Open Data Commons Open Database License v1.0 | https://physionet.org/content/mimic-iv-demo/ |
| 10 | Tier 1 | Pulse Transit Time PPG Dataset | 2.9 GB | Open Data Commons Open Database License v1.0 | https://physionet.org/content/pulse-transit-time-ppg/ |
| 11 | Tier 1 | eICU Collaborative Research Database Demo | 130.6 MB | Open Data Commons Open Database License v1.0 | https://physionet.org/content/eicu-crd-demo/ |
| 22 | Tier 2 | Autonomic Aging: A dataset to quantify changes of cardiovascular autonomic function during healthy aging | 5.9 GB | Open Data Commons Open Database License v1.0 | https://physionet.org/content/autonomic-aging-cardiovascular/ |
| 23 | Tier 2 | Brno University of Technology Smartphone PPG Database (BUT PPG) | 203.3 MB | Creative Commons Attribution 4.0 International Public Licens | https://physionet.org/content/butppg/ |
| 24 | Tier 2 | Cerebral Vasoregulation in Diabetes | 3.0 GB | Creative Commons Attribution 4.0 International Public Licens | https://physionet.org/content/cerebral-vasoreg-diabetes/ |
| 25 | Tier 2 | Congestive Heart Failure RR Interval Database | 6.4 MB | Open Data Commons Attribution License v1.0 | https://physionet.org/content/chf2db/ |
| 26 | Tier 2 | Continuous Cuffless Monitoring of Arterial Blood Pressure via Graphene Bioimpedance Tattoos | 2.3 GB | Open Data Commons Attribution License v1.0 | https://physionet.org/content/bp-graphene-bioimpedance/ |
| 28 | Tier 2 | MIMIC-III Waveform Database Matched Subset | 2.4 TB | Open Data Commons Open Database License v1.0 | https://physionet.org/content/mimic3wdb-matched/ |
| 29 | Tier 2 | MIMIC-IV-ECG: Diagnostic Electrocardiogram Matched Subset | 90.4 GB | Open Data Commons Open Database License v1.0 | https://physionet.org/content/mimic-iv-ecg/ |
| 30 | Tier 2 | Smart Health for Assessing the Risk of Events via ECG Database | 4.1 GB | Open Data Commons Attribution License v1.0 | https://physionet.org/content/shareedb/ |
| 31 | Tier 2 | Wearable Device Dataset from Induced Stress and Structured Exercise Sessions | 247.4 MB | Open Data Commons Attribution License v1.0 | https://physionet.org/content/wearable-device-dataset/ |

## C. PhysioNet, credentialed (account + CITI training + DUA, takes days to weeks)

| # | Tier | Dataset | Size | Licence | Link |
|---|---|---|---|---|---|
| 6 | Tier 1 | MIMIC-IV | n/a (gated) | PhysioNet Credentialed Health Data License 1.5.0 | https://physionet.org/content/mimiciv/ |
| 8 | Tier 1 | MIMIC-IV-Note: Deidentified free-text clinical notes | n/a (gated) | PhysioNet Credentialed Health Data License 1.5.0 | https://physionet.org/content/mimic-iv-note/ |
| 9 | Tier 1 | Medication Extraction Labels for MIMIC-IV-Note Clinical Database | n/a (gated) | PhysioNet Credentialed Health Data License 1.5.0 | https://physionet.org/content/medication-labels-mimic-note/ |
| 27 | Tier 2 | Curated Data for Describing Blood Glucose Management in the Intensive Care Unit | n/a (gated) | PhysioNet Credentialed Health Data License 1.5.0 | https://physionet.org/content/glucose-management-mimic/ |
| 32 | Tier 2 | eICU Collaborative Research Database | n/a (gated) | PhysioNet Credentialed Health Data License 1.5.0 | https://physionet.org/content/eicu-crd/ |

## D. Kaggle (free account + API token)

| # | Tier | Dataset | Size | Licence | Link |
|---|---|---|---|---|---|
| 12 | Tier 2 | Cardiovascular Disease dataset | 2.9 MB | Unknown | https://www.kaggle.com/datasets/sulianova/cardiovascular-disease-dataset |
| 13 | Tier 2 | ECG Heartbeat Categorization Dataset | 582.8 MB | Unknown | https://www.kaggle.com/datasets/shayanfazeli/heartbeat |
| 14 | Tier 2 | FitBit Fitness Tracker Data | 616.8 MB | CC0: Public Domain | https://www.kaggle.com/datasets/arashnic/fitbit |
| 15 | Tier 2 | Heart Failure Prediction | 12 KB | Attribution 4.0 International (CC BY 4.0) | https://www.kaggle.com/datasets/andrewmvd/heart-failure-clinical-data |
| 16 | Tier 2 | Heart Failure Prediction Dataset | 36 KB | Database: Open Database, Contents: © Original Authors | https://www.kaggle.com/datasets/fedesoriano/heart-failure-prediction |
| 17 | Tier 2 | Open Food Facts | 1.01 GB | Database: Open Database, Contents: Database Contents | https://www.kaggle.com/datasets/openfoodfacts/world-food-facts |
| 18 | Tier 2 | Sleep Health and Lifestyle Dataset | 24 KB | CC0: Public Domain | https://www.kaggle.com/datasets/uom190346a/sleep-health-and-lifestyle-dataset |
| 19 | Tier 2 | Stroke Prediction Dataset | 317 KB | Data files © Original Authors | https://www.kaggle.com/datasets/fedesoriano/stroke-prediction-dataset |
| 20 | Tier 2 | 250k Medicines Usage, Side Effects and Substitutes | 89.4 MB | CC BY-SA 4.0 | https://www.kaggle.com/datasets/shudhanshusingh/250k-medicines-usage-side-effects-and-substitutes |
| 21 | Tier 2 | Diabetes Health Indicators Dataset (BRFSS 2015) | 51.8 MB | CC0: Public Domain | https://www.kaggle.com/datasets/alexteboul/diabetes-health-indicators-dataset |
| 37 | Tier 2 (one column only) | Doctor's Specialty Recommendation | 2.6 MB | CC BY-SA 4.0 | https://www.kaggle.com/datasets/ebrahimelgazar/doctor-specialist-recommendation-system |
| 38 | Tier 3 | Diabetes Risk Prediction Dataset (50K patients) | 12.0 MB | CC BY-SA 4.0 | https://www.kaggle.com/datasets/mobeenfatimah/diabetes-risk-prediction-dataset-50k-patients |
| 39 | Tier 3 | Hypertension Risk Prediction Dataset | 122 KB | Apache 2.0 | https://www.kaggle.com/datasets/miadul/hypertension-risk-prediction-dataset |
| 48 | Do not use (patient-facing) | Healthcare Symptoms–Disease Classification Dataset | 2.1 MB | CC BY 4.0 | https://www.kaggle.com/datasets/kundanbedmutha/healthcare-symptomsdisease-classification-dataset |

## E. UCI (open, fetched with Python)

| # | Tier | Dataset | Size | Licence | Link |
|---|---|---|---|---|---|
| 33 | Tier 2 | Diabetes 130-US Hospitals for Years 1999-2008 | 101766 rows x 47.0 feats | UCI / CC BY 4.0 | https://archive.ics.uci.edu/dataset/296 |
| 34 | Tier 2 | Drug Reviews (Druglib.com) | 4143 rows x 8.0 feats | UCI / CC BY 4.0 | https://archive.ics.uci.edu/dataset/461 |
| 35 | Tier 2 | Estimation of Obesity Levels Based On Eating Habits and Physical Condition | 2111 rows x 16.0 feats | UCI / CC BY 4.0 | https://archive.ics.uci.edu/dataset/544 |
| 36 | Tier 2 | Human Activity Recognition Using Smartphones | 10299 rows x 0.0 feats | UCI / CC BY 4.0 | https://archive.ics.uci.edu/dataset/240 |
| 40 | Tier 3 | Chronic Kidney Disease | 400 rows x 24.0 feats | UCI / CC BY 4.0 | https://archive.ics.uci.edu/dataset/336 |
| 41 | Tier 3 | Heart Disease | 303 rows x 13.0 feats | UCI / CC BY 4.0 | https://archive.ics.uci.edu/dataset/45 |
| 42 | Tier 3 | Heart Failure Clinical Records | 299 rows x 12.0 feats | UCI / CC BY 4.0 | https://archive.ics.uci.edu/dataset/519 |
| 43 | Tier 3 | Hepatitis C Virus (HCV) for Egyptian patients | 1385 rows x 28.0 feats | UCI / CC BY 4.0 | https://archive.ics.uci.edu/dataset/503 |
| 44 | Tier 3 | ILPD (Indian Liver Patient Dataset) | 583 rows x 10.0 feats | UCI / CC BY 4.0 | https://archive.ics.uci.edu/dataset/225 |
| 45 | Tier 3 | Liver Disorders | 345 rows x 5.0 feats | UCI / CC BY 4.0 | https://archive.ics.uci.edu/dataset/60 |
| 46 | Tier 3 | Risk Factor Prediction of Chronic Kidney Disease | 200 rows x 28.0 feats | UCI / CC BY 4.0 | https://archive.ics.uci.edu/dataset/857 |
| 47 | Tier 3 | Smartphone Dataset for Human Activity Recognition (HAR) in Ambient Assisted Living (AAL) | 5744 rows x 0.0 feats | UCI / CC BY 4.0 | https://archive.ics.uci.edu/dataset/364 |

> UCI links use the standard `archive.ics.uci.edu/dataset/<id>` pattern built from the manifest id; the manifest itself only gives DOIs (`https://doi.org/<doi>`) and Python fetch commands. Check each one opens.


## NHANES direct file links (only the two cycles in the manifest)

Manifest #1 is the 2017-2018 cycle (27 files), manifest #2 is 2021-2023 (23 files). Files are SAS XPORT (`.xpt`); join on `SEQN`. The Excel also lists 80 more files for 2011-2016, which are **not** in the manifest (see the guide in chat).


### 2017-2018 (manifest #1)

| Group | What it gives you | File | Data (.xpt) | Codebook |
|---|---|---|---|---|
| ALB_CR | Urine albumin-creatinine ratio (albuminuria / KDIGO staging) | ALB_CR_J | https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2017/DataFiles/ALB_CR_J.xpt | https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2017/DataFiles/ALB_CR_J.htm |
| BIOPRO | Standard biochemistry: creatinine (eGFR), ALT, AST, albumin, glucose, uric acid | BIOPRO_J | https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2017/DataFiles/BIOPRO_J.xpt | https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2017/DataFiles/BIOPRO_J.htm |
| BMX | Body measures: BMI, waist circumference (obesity / CKM adiposity) | BMX_J | https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2017/DataFiles/BMX_J.xpt | https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2017/DataFiles/BMX_J.htm |
| BPX | Blood pressure (manual, 2011-2017) / BPXO oscillometric (2017+) | BPX_J | https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2017/DataFiles/BPX_J.xpt | https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2017/DataFiles/BPX_J.htm |
| BPX | Blood pressure (manual, 2011-2017) / BPXO oscillometric (2017+) | BPXO_J | https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2017/DataFiles/BPXO_J.xpt | https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2017/DataFiles/BPXO_J.htm |
| BPX | Blood pressure (manual, 2011-2017) / BPXO oscillometric (2017+) | BPQ_J | https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2017/DataFiles/BPQ_J.xpt | https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2017/DataFiles/BPQ_J.htm |
| DEMO | Demographics: age, sex, race, income, education, survey weights | DEMO_J | https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2017/DataFiles/DEMO_J.xpt | https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2017/DataFiles/DEMO_J.htm |
| DIQ | Diabetes questionnaire: diagnosis, insulin/pill use, self-monitoring | DIQ_J | https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2017/DataFiles/DIQ_J.xpt | https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2017/DataFiles/DIQ_J.htm |
| DR1TOT | Total nutrient intake day 1 | DR1TOT_J | https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2017/DataFiles/DR1TOT_J.xpt | https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2017/DataFiles/DR1TOT_J.htm |
| GHB | Glycohemoglobin HbA1c | GHB_J | https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2017/DataFiles/GHB_J.xpt | https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2017/DataFiles/GHB_J.htm |
| GLU | Fasting plasma glucose | GLU_J | https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2017/DataFiles/GLU_J.xpt | https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2017/DataFiles/GLU_J.htm |
| HDL | HDL cholesterol | HDL_J | https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2017/DataFiles/HDL_J.xpt | https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2017/DataFiles/HDL_J.htm |
| HIQ | Health insurance access | HIQ_J | https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2017/DataFiles/HIQ_J.xpt | https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2017/DataFiles/HIQ_J.htm |
| INS | Fasting insulin (HOMA-IR) | INS_J | https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2017/DataFiles/INS_J.xpt | https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2017/DataFiles/INS_J.htm |
| KIQ_U | Kidney conditions - urology | KIQ_U_J | https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2017/DataFiles/KIQ_U_J.xpt | https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2017/DataFiles/KIQ_U_J.htm |
| LUX | Liver ultrasound transient elastography: CAP + stiffness (MASLD/fibrosis) | LUX_J | https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2017/DataFiles/LUX_J.xpt | https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2017/DataFiles/LUX_J.htm |
| MCQ | Medical conditions: CVD, HF, liver, cancer history | MCQ_J | https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2017/DataFiles/MCQ_J.xpt | https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2017/DataFiles/MCQ_J.htm |
| PAQ | Physical activity questionnaire | PAQ_J | https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2017/DataFiles/PAQ_J.xpt | https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2017/DataFiles/PAQ_J.htm |
| PAQ | Physical activity questionnaire | PAQY_J | https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2017/DataFiles/PAQY_J.xpt | https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2017/DataFiles/PAQY_J.htm |
| RXQ_RX | Prescription medications taken (drug name, RxCUI-mappable, duration) | RXQ_RX_J | https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2017/DataFiles/RXQ_RX_J.xpt | https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2017/DataFiles/RXQ_RX_J.htm |
| RXQ_RX | Prescription medications taken (drug name, RxCUI-mappable, duration) | RXQ_DRUG | https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/1988/DataFiles/RXQ_DRUG.xpt | https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/1988/DataFiles/RXQ_DRUG.htm |
| SLQ | Sleep disorders questionnaire | SLQ_J | https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2017/DataFiles/SLQ_J.xpt | https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2017/DataFiles/SLQ_J.htm |
| SMQ | Smoking - cigarette use | SMQ_J | https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2017/DataFiles/SMQ_J.xpt | https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2017/DataFiles/SMQ_J.htm |
| TCHOL | Total cholesterol | TCHOL_J | https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2017/DataFiles/TCHOL_J.xpt | https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2017/DataFiles/TCHOL_J.htm |
| TRIGLY | Triglycerides + LDL | TRIGLY_J | https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2017/DataFiles/TRIGLY_J.xpt | https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2017/DataFiles/TRIGLY_J.htm |
| WHQ | Weight history / weight-loss attempts | WHQ_J | https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2017/DataFiles/WHQ_J.xpt | https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2017/DataFiles/WHQ_J.htm |
| WHQ | Weight history / weight-loss attempts | WHQMEC_J | https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2017/DataFiles/WHQMEC_J.xpt | https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2017/DataFiles/WHQMEC_J.htm |

### 2021-2023 (manifest #2)

| Group | What it gives you | File | Data (.xpt) | Codebook |
|---|---|---|---|---|
| ALB_CR | Urine albumin-creatinine ratio (albuminuria / KDIGO staging) | ALB_CR_L | https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2021/DataFiles/ALB_CR_L.xpt | https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2021/DataFiles/ALB_CR_L.htm |
| BIOPRO | Standard biochemistry: creatinine (eGFR), ALT, AST, albumin, glucose, uric acid | BIOPRO_L | https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2021/DataFiles/BIOPRO_L.xpt | https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2021/DataFiles/BIOPRO_L.htm |
| BMX | Body measures: BMI, waist circumference (obesity / CKM adiposity) | BMX_L | https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2021/DataFiles/BMX_L.xpt | https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2021/DataFiles/BMX_L.htm |
| BPX | Blood pressure (manual, 2011-2017) / BPXO oscillometric (2017+) | BPXO_L | https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2021/DataFiles/BPXO_L.xpt | https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2021/DataFiles/BPXO_L.htm |
| BPX | Blood pressure (manual, 2011-2017) / BPXO oscillometric (2017+) | BPQ_L | https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2021/DataFiles/BPQ_L.xpt | https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2021/DataFiles/BPQ_L.htm |
| DEMO | Demographics: age, sex, race, income, education, survey weights | DEMO_L | https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2021/DataFiles/DEMO_L.xpt | https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2021/DataFiles/DEMO_L.htm |
| DIQ | Diabetes questionnaire: diagnosis, insulin/pill use, self-monitoring | DIQ_L | https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2021/DataFiles/DIQ_L.xpt | https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2021/DataFiles/DIQ_L.htm |
| DR1TOT | Total nutrient intake day 1 | DR1TOT_L | https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2021/DataFiles/DR1TOT_L.xpt | https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2021/DataFiles/DR1TOT_L.htm |
| GHB | Glycohemoglobin HbA1c | GHB_L | https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2021/DataFiles/GHB_L.xpt | https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2021/DataFiles/GHB_L.htm |
| GLU | Fasting plasma glucose | GLU_L | https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2021/DataFiles/GLU_L.xpt | https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2021/DataFiles/GLU_L.htm |
| HIQ | Health insurance access | HIQ_L | https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2021/DataFiles/HIQ_L.xpt | https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2021/DataFiles/HIQ_L.htm |
| INS | Fasting insulin (HOMA-IR) | INS_L | https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2021/DataFiles/INS_L.xpt | https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2021/DataFiles/INS_L.htm |
| KIQ_U | Kidney conditions - urology | KIQ_U_L | https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2021/DataFiles/KIQ_U_L.xpt | https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2021/DataFiles/KIQ_U_L.htm |
| LUX | Liver ultrasound transient elastography: CAP + stiffness (MASLD/fibrosis) | LUX_L | https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2021/DataFiles/LUX_L.xpt | https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2021/DataFiles/LUX_L.htm |
| MCQ | Medical conditions: CVD, HF, liver, cancer history | MCQ_L | https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2021/DataFiles/MCQ_L.xpt | https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2021/DataFiles/MCQ_L.htm |
| PAQ | Physical activity questionnaire | PAQ_L | https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2021/DataFiles/PAQ_L.xpt | https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2021/DataFiles/PAQ_L.htm |
| PAQ | Physical activity questionnaire | PAQY_L | https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2021/DataFiles/PAQY_L.xpt | https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2021/DataFiles/PAQY_L.htm |
| RXQ_RX | Prescription medications taken (drug name, RxCUI-mappable, duration) | RXQ_RX_L | https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2021/DataFiles/RXQ_RX_L.xpt | https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2021/DataFiles/RXQ_RX_L.htm |
| SLQ | Sleep disorders questionnaire | SLQ_L | https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2021/DataFiles/SLQ_L.xpt | https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2021/DataFiles/SLQ_L.htm |
| SMQ | Smoking - cigarette use | SMQ_L | https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2021/DataFiles/SMQ_L.xpt | https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2021/DataFiles/SMQ_L.htm |
| TCHOL | Total cholesterol | TCHOL_L | https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2021/DataFiles/TCHOL_L.xpt | https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2021/DataFiles/TCHOL_L.htm |
| TRIGLY | Triglycerides + LDL | TRIGLY_L | https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2021/DataFiles/TRIGLY_L.xpt | https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2021/DataFiles/TRIGLY_L.htm |
| WHQ | Weight history / weight-loss attempts | WHQ_L | https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2021/DataFiles/WHQ_L.xpt | https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2021/DataFiles/WHQ_L.htm |

## Live APIs (query at runtime, do not bulk download)

| Service | Provider | Endpoint | Status per the Excel |
|---|---|---|---|
| openFDA Drug Label (SPL) | FDA | https://api.fda.gov/drug/label.json | VERIFIED 200 — patient-facing 'information_for_patients' present for 35/39 CKM drugs tested (median 1,783 char |
| openFDA Drug Event (FAERS) | FDA | https://api.fda.gov/drug/event.json | VERIFIED 200 — reaction profiles retrieved for 38/39 CKM drugs |
| openFDA NDC Directory | FDA | https://api.fda.gov/drug/ndc.json | VERIFIED 200 |
| RxNorm (RxNav) REST | NLM | https://rxnav.nlm.nih.gov/REST/rxcui.json | VERIFIED 200 — RxCUI resolved for 39/39 CKM drugs tested |
| RxClass (RxNav) | NLM | https://rxnav.nlm.nih.gov/REST/rxclass/class/byDrugName.json | VERIFIED 200 |
| RxNav Drug Interaction API | NLM | https://rxnav.nlm.nih.gov/REST/interaction/* | RETIRED — returns HTTP 404 on interaction.json, list.json and sources.json as of this run. DO NOT design aroun |
| ClinicalTrials.gov API v2 | NIH | https://clinicaltrials.gov/api/v2/studies | VERIFIED 200 — 1,794 unique digital/wearable-intervention studies retrieved across 7 CKM conditions |
| MedlinePlus Connect | NLM | https://connect.medlineplus.gov/service | NOT TESTED in this run — domain not on sandbox allowlist; verify locally |
| DailyMed SPL | NLM | https://dailymed.nlm.nih.gov/dailymed/services/v2 | NOT TESTED — verify locally; note openFDA had spl_patient_package_insert for only 10/39 drugs, DailyMed is the |
| Open Targets Platform GraphQL | EMBL-EBI/OT | https://api.platform.opentargets.org/api/v4/graphql | REACHABLE 200 but disease lookups by legacy EFO id returned null/empty this run; DEPRIORITISED — drug-discover |
| ChEMBL REST | EMBL-EBI | https://www.ebi.ac.uk/chembl/api/data | VERIFIED 200 — retained only as chemistry reference, low value for this app |
| Apple HealthKit | Apple | developer.apple.com/healthkit | SDK — no public REST; requires iOS app |
| Health Connect (Android) | Google | developer.android.com/health-and-fitness/guides/health-connect | SDK — requires Android app |
| Fitbit Web API | Google/Fitbit | https://api.fitbit.com/1/user/-/ | OAuth — personal-use intraday requires application |
| Dexcom API | Dexcom | https://api.dexcom.com/v3/users/self/egvs | OAuth — sandbox available for hackathon demo |
| Abbott LibreView / LibreLinkUp | Abbott | (partner API) | Partner-gated — not obtainable in a hackathon window |
| Withings / Omron / Garmin APIs | vendors | developer.withings.com; omron; developer.garmin.com | OAuth/partner — BP cuff data is the main gap for HTN |
| Terra / Rook / Vital (aggregators) | 3rd party | tryterra.co; tryrook.io; tryvital.io | Commercial with free dev tiers — verify current terms |
| HL7 FHIR R4 / SMART on FHIR | HL7 | hl7.org/fhir/R4 | Standard — use SMART launch + US Core / IPS profiles |
| Synthea synthetic FHIR | MITRE | github.com/synthetichealth/synthea | Open source — best way to demo the clinician channel without real PHI |

## F. GlucoBench (not in the manifest, allowed by the data source policy)

Link taken from the hyperlinks in `smart_health_data_plan.xlsx`: https://www.kaggle.com/datasets/omenkj/glucobench-glucose-monitoring-and-lifestyle-data

Kaggle access as in group D. The plan treats it as a fixture and template only, never as evidence (no source is cited and it is only 2.76 MB, so it may be synthetic).
