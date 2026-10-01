# Data

Everything data-related lives here. Documents live in `docs/`.

| Folder | Holds | Committed? |
|---|---|---|
| `data-map.md` | What data we need, what it is for, where it comes from (with links), what is missing, and what the user enters in the app | Yes |
| `plan/` | `smart_health_data_plan.xlsx`: datasets to use now, what is still missing, and data that strengthens the AI | Yes |
| `raw/` | Downloaded datasets, one subfolder per dataset (`cgmacros/`, `big-ideas/`, `nhanes/`, `fitbit/`, `medicines-250k/`, `open-food-facts/`, `glucobench/`, `doctor-specialty/`) | **No.** Large and licensed |
| `processed/` | Output of the importers (cleaned, converted, time-shifted) | **No** |
| `reference/` | Small seed tables (interactions, foods, preventive items), each with its source recorded | Yes |
| `knowledge/` | The approved corpus used for retrieval, with a `sources.csv` (manifest number and licence per source) | Yes |
| `demo/` | Small synthetic demo data (the simulated 60-day history) | Yes |

## Rules

- **Only the datasets in the hackathon download manifest and the GlucoBench Kaggle dataset are allowed.** Anything else needs the owner's approval first and is listed as "Needs your OK" in the plan workbook.
- **Never commit raw datasets.** Several carry licences (for example CGMacros is CC BY-NC-SA 4.0). The repo holds scripts and small samples only.
- **Simulated data must be marked** as simulated (`entry_source = 'demo_dataset'` or a simulated flag) and disclosed.
- **AI estimates** (such as meal macros) are labelled as estimates and are never mixed in with measured values.
- Every seeded reference row records its source in `data_sources`.

## Getting the data

The plan workbook lists each dataset with its link, the columns we use and its licence. The download script (backlog task E1-1) fetches the allowed subsets into `raw/`.
