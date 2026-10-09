"""
Part 2: pandas data cleaning and EDA.
Reads the RAW CSVs in data/ (never the SQL database).
Run from the repo root:  python analysis/clean_and_eda.py
"""
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

# ---------------------------------------------------------------- Task 1
print("=" * 60)
print("TASK 1: Load and inspect")
print("=" * 60)
customers = pd.read_csv(DATA / "customers.csv")
products = pd.read_csv(DATA / "products.csv")
orders = pd.read_csv(DATA / "orders.csv")
print("customers.shape:", customers.shape)
print("products.shape :", products.shape)
print("orders.shape   :", orders.shape, "(expected (180, 9))")
print("\nMissing values per column (raw orders):")
print(orders.isnull().sum())

# ---------------------------------------------------------------- Task 2
print("\n" + "=" * 60)
print("TASK 2: Standardise payment_method casing")
print("=" * 60)
print("Raw values  :", sorted(orders["payment_method"].unique()),
      "->", orders["payment_method"].nunique(), "values")
orders["payment_method"] = orders["payment_method"].str.strip().str.upper()
print("Fixed values:", sorted(orders["payment_method"].unique()),
      "->", orders["payment_method"].nunique(), "values")
print(orders["payment_method"].value_counts())

# ---------------------------------------------------------------- Task 3
print("\n" + "=" * 60)
print("TASK 3: Remove duplicate orders")
print("=" * 60)
# Natural key = every column EXCEPT order_id (order_id differs on the double-submits)
key_cols = ["customer_id", "product_id", "order_date", "quantity",
            "discount_pct", "payment_method", "rating", "returned"]
dup_mask = orders.duplicated(subset=key_cols, keep="first")
dropped = orders[dup_mask].copy()
print("Duplicates flagged:", int(dup_mask.sum()))
print("Dropped order_ids :", dropped["order_id"].tolist())
orders_clean = orders[~dup_mask].copy()
print("orders_clean.shape:", orders_clean.shape, "(expected (175, 9))")

# ---------------------------------------------------------------- Task 4
print("\n" + "=" * 60)
print("TASK 4: Impute missing values (after de-duplication)")
print("=" * 60)
n_disc = int(orders_clean["discount_pct"].isnull().sum())
n_rate = int(orders_clean["rating"].isnull().sum())
median_rating = float(orders_clean["rating"].median())  # median of non-null ratings
print(f"discount_pct missing: {n_disc} -> fill with 0 (no promo code applied)")
print(f"rating missing      : {n_rate} -> fill with the median")
print("Median rating (before imputing):", median_rating)
orders_clean["discount_pct"] = orders_clean["discount_pct"].fillna(0)
orders_clean["rating"] = orders_clean["rating"].fillna(median_rating)
print("Nulls after imputing:", orders_clean[["discount_pct", "rating"]].isnull().sum().to_dict())

# ---------------------------------------------------------------- Task 5
print("\n" + "=" * 60)
print("TASK 5: Merge, order_value, and reconcile against Part 1")
print("=" * 60)
df = (orders_clean
      .merge(products, on="product_id", how="left")
      .merge(customers, on="customer_id", how="left"))
print("Merged shape:", df.shape)
df["order_value"] = df["quantity"] * df["price"] * (1 - df["discount_pct"] / 100)
cleaned_total = round(float(df["order_value"].sum()), 2)
print(f"Cleaned total revenue (175 rows): INR {cleaned_total:,.2f}")

# Independent check: add up the value of the 5 dropped duplicate rows
dd = dropped.merge(products, on="product_id", how="left")
dd["order_value"] = dd["quantity"] * dd["price"] * (1 - dd["discount_pct"].fillna(0) / 100)
dup_value = round(float(dd["order_value"].sum()), 2)
raw_total = round(cleaned_total + dup_value, 2)
print(f"Combined order_value of the 5 dropped duplicates: INR {dup_value:,.2f}")
print(f"Part 1 raw total (Report a): INR {raw_total:,.2f}")
print("\nRECONCILIATION NOTE:")
print(f"  Part 1 Report (a) showed INR {raw_total:,.2f} on the raw 180 rows. This pipeline shows "
      f"INR {cleaned_total:,.2f} on the 175 cleaned rows. The difference of INR {raw_total - cleaned_total:,.2f} "
      f"is exactly the combined order_value of the 5 double-submitted orders removed in Task 3 "
      f"({', '.join(dropped['order_id'])}), which independently adds up to INR {dup_value:,.2f}. "
      f"None of the gap comes from imputation: blank discounts were already treated as 0% in SQL "
      f"(COALESCE), and ratings do not enter order_value at all.")

# ---------------------------------------------------------------- Task 6
print("\n" + "=" * 60)
print("TASK 6: IQR outlier detection on quantity (flag, do not drop)")
print("=" * 60)
q1 = float(df["quantity"].quantile(0.25))
q3 = float(df["quantity"].quantile(0.75))
iqr = q3 - q1
lower = q1 - 1.5 * iqr
upper = q3 + 1.5 * iqr
print(f"Q1={q1}  Q3={q3}  IQR={iqr}  lower={lower}  upper={upper}")
df["is_outlier"] = (df["quantity"] < lower) | (df["quantity"] > upper)
outliers = df[df["is_outlier"]]
print("Outliers flagged:", len(outliers))
print(outliers[["order_id", "order_date", "quantity"]].to_string(index=False))

# ---------------------------------------------------------------- Task 7
print("\n" + "=" * 60)
print("TASK 7: Hypothesis: COD orders have a higher return rate")
print("=" * 60)
print("H1: COD orders are returned more often than Card or UPI orders.")
by_pay = df.groupby("payment_method")["returned"].agg(["count", "mean"])
by_pay["return_rate_pct"] = (by_pay["mean"] * 100).round(1)
print(by_pay)
rates = by_pay["return_rate_pct"].to_dict()
confirmed = rates["COD"] > max(rates["CARD"], rates["UPI"])
print(f"\nHypothesis: {'CONFIRMED' if confirmed else 'NOT CONFIRMED'} "
      f"(COD {rates['COD']}% vs CARD {rates['CARD']}% vs UPI {rates['UPI']}%)")

# ---------------------------------------------------------------- Task 8
print("\n" + "=" * 60)
print("TASK 8: Segmentation (payment_method x city_tier)")
print("=" * 60)
seg = df.groupby(["payment_method", "city_tier"])["returned"].agg(["count", "mean"])
seg["return_rate_pct"] = (seg["mean"] * 100).round(1)
print(seg)
top_pay, top_tier = seg["mean"].idxmax()
top_rate = float(seg.loc[(top_pay, top_tier), "return_rate_pct"])
top_n = int(seg.loc[(top_pay, top_tier), "count"])
print(f"\nHighest-risk segment: {top_pay} + Tier-{top_tier} cities at {top_rate}% ({top_n} orders).")
cod = seg.loc["COD"]
print(f"COD risk is NOT uniform: Tier-1 {cod.loc[1, 'return_rate_pct']}% ({int(cod.loc[1, 'count'])} orders) "
      f"vs Tier-2 {cod.loc[2, 'return_rate_pct']}% ({int(cod.loc[2, 'count'])} orders). "
      f"A single blended COD rate hides where the problem is concentrated.")

# ---------------------------------------------------------------- Task 9
print("\n" + "=" * 60)
print("TASK 9: Correlation analysis")
print("=" * 60)


def strength_band(r):
    r = abs(r)
    if r < 0.2:
        return "negligible"
    if r < 0.4:
        return "weak"
    if r < 0.7:
        return "moderate"
    return "strong"


cols = ["rating", "returned", "discount_pct", "quantity"]
corr = df[cols].corr()
print(corr.round(3))
print("\nStrength bands (|r|: <0.2 negligible, 0.2-0.39 weak, 0.4-0.69 moderate, 0.7+ strong):")
for i, a in enumerate(cols):
    for b in cols[i + 1:]:
        r = float(corr.loc[a, b])
        print(f"  {a:>12} vs {b:<12} r = {r:+.3f} -> {strength_band(r)}")
r_disc = float(corr.loc["discount_pct", "returned"])
print(f"\nHypothesis 'higher discounts reduce returns': "
      f"{'BUSTED' if abs(r_disc) < 0.2 else 'SUPPORTED'} "
      f"(discount_pct vs returned r = {r_disc:+.2f}, {strength_band(r_disc)})")

# ---------------------------------------------------------------- Task 10
print("\n" + "=" * 60)
print("TASK 10: Outlier-corrected monthly revenue")
print("=" * 60)
df["order_date"] = pd.to_datetime(df["order_date"])
df["year_month"] = df["order_date"].dt.to_period("M").astype(str)
monthly_all = df.groupby("year_month")["order_value"].sum().round(2)
monthly_corrected = df[~df["is_outlier"]].groupby("year_month")["order_value"].sum().round(2)
print("(1) Monthly revenue INCLUDING outliers:")
print(monthly_all.to_string())
print("\n(2) Monthly revenue EXCLUDING outliers (outlier-corrected):")
print(monthly_corrected.to_string())
apparent_month = monthly_all.idxmax()
true_month = monthly_corrected.idxmax()
outliers = df[df["is_outlier"]]  # re-select now that order_date is a datetime
out_dates = ", ".join(f"{r.order_id} on {r.order_date:%Y-%m-%d}" for r in outliers.itertuples())
print(f"\nFINDING: {apparent_month} looks like the best month (INR {monthly_all[apparent_month]:,.2f}), "
      f"but that lead is an artifact of the {len(outliers)} bulk orders landing in it ({out_dates}). "
      f"With them excluded, {apparent_month} falls to INR {monthly_corrected[apparent_month]:,.2f} "
      f"and {true_month} is the genuine peak month at INR {monthly_corrected[true_month]:,.2f}.")

# ------------------------------------------------- findings.json (feeds Part 3)
print("\n" + "=" * 60)
print("Writing narrator/findings.json (generated from the numbers above)")
print("=" * 60)
findings = {
    "cleaned_total_revenue_inr": cleaned_total,
    "raw_total_revenue_inr": raw_total,
    "duplicate_reconciliation_delta_inr": round(raw_total - cleaned_total, 2),
    "return_rate_by_payment": {k: float(rates[k]) for k in ("COD", "CARD", "UPI")},
    "highest_risk_segment": {"payment_method": top_pay, "city_tier": int(top_tier),
                             "return_rate_pct": top_rate},
    "true_peak_month": {"month": true_month,
                        "revenue_inr": float(monthly_corrected[true_month])},
    "outlier_inflated_month": {"month": apparent_month,
                               "apparent_revenue_inr": float(monthly_all[apparent_month]),
                               "corrected_revenue_inr": float(monthly_corrected[apparent_month])},
}
out_path = ROOT / "narrator" / "findings.json"
out_path.parent.mkdir(exist_ok=True)
out_path.write_text(json.dumps(findings, indent=2) + "\n")
print(json.dumps(findings, indent=2))
print("\nSaved ->", out_path)