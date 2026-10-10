 # Mamaearth Returns & Growth Intelligence Pipeline

An end-to-end pipeline that shows how returns eat into Mamaearth's margins. A **SQL** layer stores and reports on the orders, a **pandas** layer cleans the data and finds the real patterns, and a **GenAI** layer (Gemini, with an offline fallback) turns the verified numbers into a business narrative for ops and finance heads.

## Repository structure

```
README.md
requirements.txt
sql/             schema.sql, seed_data.sql, reports.sql
                 (helpers: generate_seed.py, run_reports.py, add_output_comments.py)
data/            customers.csv, products.csv, orders.csv   (raw, never edited)
analysis/        clean_and_eda.py, visualize.py
visualizations/  return_rate_by_payment.png, monthly_revenue_trend.png
narrator/        findings.json, generate_narrative.py, sample_output.txt
```

## How the three layers connect

```
data/*.csv --> sql/  (schema -> seed -> 9 reports)         Layer 1: raw-data totals in SQL
     |
     +-----> analysis/clean_and_eda.py --> narrator/findings.json
                    |                              |
                    +--> analysis/visualize.py     +--> narrator/generate_narrative.py --> sample_output.txt
                         (2 PNG charts)                  (Gemini, or offline template)
```

* **Layers 1 and 2 are independent.** Both read the same raw CSVs, so they can be run in either order. They agree on every figure except one deliberate gap: the SQL raw total is INR 99,860.20 and the pandas cleaned total is INR 97,358.30. The INR 2,501.90 difference is exactly the 5 duplicate orders (O0176 to O0180) that pandas removes. The reconciliation is printed by `clean_and_eda.py`.
* **Layer 2 feeds layer 3.** `clean_and_eda.py` writes `narrator/findings.json`, and the narrator reads only that file. No number is typed by hand anywhere.

## Setup (Windows PowerShell)

```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

Run every command below from the repository root.

## 1. SQL layer

SQLite ships with Python, so nothing extra is needed. Build the database and load the data:

```
python -c "import sqlite3; c=sqlite3.connect('mamaearth.db'); c.executescript(open('sql/schema.sql').read()); c.executescript(open('sql/seed_data.sql').read()); print([c.execute(f'select count(*) from {t}').fetchone()[0] for t in ('customers','products','orders')])"
```

This prints `[45, 16, 180]`. To run `sql/reports.sql` and see the result of every report:

```
python sql/run_reports.py
```

`schema.sql` drops and recreates the tables, so the steps can be repeated safely. The exact output of each report is also pasted as a comment (lines starting with `--|`) above its query in `reports.sql`. Helper scripts: `generate_seed.py` rebuilds `seed_data.sql` from the CSVs, and `add_output_comments.py` refreshes those output comments. `mamaearth.db` is git-ignored.

## 2. Analysis layer

```
python analysis/clean_and_eda.py
python analysis/visualize.py
```

* `clean_and_eda.py` prints every intermediate result and writes `narrator/findings.json` at the end.
* `visualize.py` saves the two PNG charts into `visualizations/`.

Cleaning order: load, standardise payment casing (7 values become 3), remove 5 duplicates, impute (blank discount becomes 0, blank rating becomes the median 3.0), merge and compute `order_value`, flag IQR outliers on quantity (flagged, not dropped), hypothesis tests, correlation, outlier-corrected monthly revenue, write `findings.json`.

## 3. GenAI narrator

```
python narrator/generate_narrative.py
```

* **With Gemini:** get a free key from Google AI Studio and set it as an environment variable. Never put the key in a file in the repo.
```
  $env:GEMINI_API_KEY="your-key"
  python narrator/generate_narrative.py
```
  Settings: temperature 0.0, `max_output_tokens` 4096, 30,000 ms timeout, every call wrapped in try/except. The script tries a short list of Gemini models in order; set `$env:GEMINI_MODEL="model-name"` to force one.
* **Without any key (offline):** run the same command with no variable set. A deterministic template built from `findings.json` writes the narrative with no network and no API call. The script also falls back to it automatically if the Gemini call fails.

Either way the script checks that the five required figures appear (INR 97,358.30; COD 44.4%; COD in Tier-2 cities 54.5%; INR 2,501.90; March with INR 20,318.90), prints PASS or FAIL for each, and saves the narrative to `narrator/sample_output.txt`. The first line of that file shows which source produced it. The committed sample was produced by Gemini.

## Key results (reproduced by the code above)

| Finding | Value |
|---|---|
| Raw revenue (SQL, 180 orders) | INR 99,860.20 |
| Cleaned revenue (pandas, 175 orders) | INR 97,358.30 |
| Gap = 5 duplicate orders | INR 2,501.90 |
| Return rate: COD / UPI / Card | 44.4% / 18.9% / 14.7% |
| Highest-risk segment | COD in Tier-2 cities, 54.5% |
| True peak month (outliers removed) | March 2026, INR 20,318.90 |
| January's apparent lead | An artifact of 2 bulk orders (INR 29,582.10 becomes 11,637.10) |
| "Discounts reduce returns" | Busted (r about -0.09, negligible) |
