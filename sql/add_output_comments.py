import sqlite3
from pathlib import Path

SQL = Path(__file__).resolve().parent
REPORTS = SQL / "reports.sql"
MARK = "--| "  # every output line starts with this, so old output can be removed and re-added

conn = sqlite3.connect(":memory:")
conn.executescript((SQL / "schema.sql").read_text())
conn.executescript((SQL / "seed_data.sql").read_text())

# Start from the file without any earlier output comments (so running this twice is safe)
lines = [l for l in REPORTS.read_text().splitlines() if not l.startswith(MARK)]

out, buffer = [], []
for line in lines:
    buffer.append(line)
    if sqlite3.complete_statement("\n".join(buffer)):
        stmt = "\n".join(buffer)
        cur = conn.execute(stmt)
        # split: leading comment/blank lines stay on top, output goes just above the SQL
        i = 0
        while i < len(buffer) and (buffer[i].strip() == "" or buffer[i].startswith("--")):
            i += 1
        out += buffer[:i]
        if cur.description:
            cols = [d[0] for d in cur.description]
            rows = cur.fetchall()
            table = [cols] + [["NULL" if v is None else str(v) for v in r] for r in rows]
            out.append(MARK + "Output:")
            out += [MARK + " | ".join(r) for r in table]
            out.append(MARK + f"({len(rows)} rows)")
        else:
            out.append(MARK + "Output: (statement executed, no result set)")
        out += buffer[i:]
        buffer = []
out += buffer  # any trailing lines

REPORTS.write_text("\n".join(out) + "\n")
print("Output comments added to reports.sql")