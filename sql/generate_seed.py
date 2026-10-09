import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NUMERIC = {"city_tier", "price", "quantity", "discount_pct", "rating", "returned"}


def literal(col, value):
    if value == "":
        return "NULL"  # blank CSV cell -> real SQL NULL
    return value if col in NUMERIC else "'" + value.replace("'", "''") + "'"


lines = [
    "-- Part 1, Task 2: seed data, generated from data/*.csv by generate_seed.py",
    "-- Run AFTER schema.sql.",
    "",
]
for table in ("customers", "products", "orders"):
    with open(ROOT / "data" / f"{table}.csv", newline="") as f:
        rows = list(csv.DictReader(f))
    cols = list(rows[0].keys())
    lines.append(f"-- {table}: {len(rows)} rows")
    for r in rows:
        vals = ", ".join(literal(c, r[c]) for c in cols)
        lines.append(f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({vals});")
    lines.append("")

(ROOT / "sql" / "seed_data.sql").write_text("\n".join(lines) + "\n")
print("seed_data.sql written")