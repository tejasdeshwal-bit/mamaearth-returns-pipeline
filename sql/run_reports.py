import sqlite3
from pathlib import Path

SQL = Path(__file__).resolve().parent

# Fresh in-memory database every run: schema, then data
conn = sqlite3.connect(":memory:")
conn.executescript((SQL / "schema.sql").read_text())
conn.executescript((SQL / "seed_data.sql").read_text())

# Run reports.sql one statement at a time and print each result
buffer = ""
for line in (SQL / "reports.sql").read_text().splitlines():
    buffer += line + "\n"
    if sqlite3.complete_statement(buffer):
        cur = conn.execute(buffer)
        if cur.description:
            cols = [d[0] for d in cur.description]
            rows = cur.fetchall()
            print(" | ".join(cols))
            for r in rows:
                print(" | ".join("NULL" if v is None else str(v) for v in r))
            print(f"({len(rows)} rows)\n")
        buffer = ""