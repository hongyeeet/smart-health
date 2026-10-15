# Test fixtures

`glucobench_sample.csv`: the first 1,000 rows of GlucoBench (Kaggle `omenkj/glucobench-glucose-monitoring-and-lifestyle-data`, Apache 2.0 as stated on Kaggle).
Insulin columns (and the insulin-related `carb_ratio`) are removed (insulin is out of scope, prd.md A9). The source is not cited and every column is filled in every row,
so it may be synthetic: **a fixture for pipeline tests only, never evidence, never loaded into the database** (decision in the E1-4 plan, 2026-10-02).
The full file stays in the git-ignored `data/raw/`.
