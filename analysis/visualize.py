"""
Part 2, Task 11: two charts.
Run from the repo root:  python analysis/visualize.py
It runs clean_and_eda.py first (quietly), so the charts always use the same numbers.
"""
import calendar
import contextlib
import io
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # draw to files only (no pop-up window)
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
OUT_DIR = HERE.parent / "visualizations"
OUT_DIR.mkdir(exist_ok=True)

sys.path.insert(0, str(HERE))
with contextlib.redirect_stdout(io.StringIO()):  # hide the long analysis printout
    import clean_and_eda as eda

# ---------------------------------------------------- chart 1: return rate by payment method
rates = dict(sorted(eda.rates.items(), key=lambda kv: kv[1], reverse=True))  # high to low
labels, values = list(rates.keys()), list(rates.values())
lowest = min(v for k, v in rates.items() if k != "COD")
multiple = rates["COD"] / lowest
colors = ["#C0392B" if k == "COD" else "#7F8C8D" for k in labels]

fig, ax = plt.subplots(figsize=(7, 5))
bars = ax.bar(labels, values, color=colors)
for bar, v in zip(bars, values):
    ax.text(bar.get_x() + bar.get_width() / 2, v + 0.8, f"{v:.1f}%", ha="center", fontweight="bold")
ax.set_ylabel("Return rate (%)")
ax.set_xlabel("Payment method")
ax.set_ylim(0, max(values) * 1.18)
ax.set_title(f"COD Returns at {rates['COD']:.1f}%: {multiple:.0f}x the Lowest-Risk Method")
ax.spines[["top", "right"]].set_visible(False)
fig.tight_layout()
fig.savefig(OUT_DIR / "return_rate_by_payment.png", dpi=150)
plt.close(fig)

# ---------------------------------------------------- chart 2: outlier-corrected monthly revenue
monthly = eda.monthly_corrected
peak = eda.findings["true_peak_month"]["month"]
peak_name = calendar.month_name[int(peak.split("-")[1])]

fig, ax = plt.subplots(figsize=(8, 5))
ax.plot(monthly.index, monthly.values, marker="o", linewidth=2, color="#2C3E50")
ax.scatter([peak], [monthly[peak]], s=140, color="#C0392B", zorder=3)
ax.annotate(f"Peak: INR {monthly[peak]:,.0f}", (peak, monthly[peak]),
            textcoords="offset points", xytext=(0, 12), ha="center", fontweight="bold")
ax.set_xlabel("Month (2026)")
ax.set_ylabel("Revenue (INR, outliers excluded)")
ax.set_title(f"{peak_name} Is the True Peak Month (Outlier-Corrected Revenue)")
ax.set_ylim(0, monthly.max() * 1.2)
ax.spines[["top", "right"]].set_visible(False)
fig.tight_layout()
fig.savefig(OUT_DIR / "monthly_revenue_trend.png", dpi=150)
plt.close(fig)

print("Saved:", OUT_DIR / "return_rate_by_payment.png")
print("Saved:", OUT_DIR / "monthly_revenue_trend.png")
