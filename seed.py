"""seed.py - load UK student loan policy figures into the `loan_plans` table.
Run: python seed.py (safe to re-run; upserts by plan name). Also exposes load_plans()."""
import sqlite3

DB_PATH = "finance.db"
TAX_YEAR = "2026/27"
# VERIFY on gov.uk before presenting - these change every year.
# Plan 1 / Plan 4 interest is the lower of RPI or base rate + 1%; interest_cap 0.045 is an ASSUMED stand-in, update it.
PLAN_ROWS = [
    {"name": "Plan 1", "threshold": 26_900, "repayment_rate": 0.09, "write_off_years": 25,
     "rpi_margin_max": 0.0, "interest_cap": 0.045, "income_upper": None,
     "note": "Pre-2012 England/Wales, NI. Often also written off at 65."},
    {"name": "Plan 2", "threshold": 29_385, "repayment_rate": 0.09, "write_off_years": 30,
     "rpi_margin_max": 0.03, "interest_cap": 0.06, "income_upper": 52_000,
     "note": "RPI to RPI+3% sliding with income; 6% cap in year 1 only. income_upper APPROXIMATE."},
    {"name": "Plan 4", "threshold": 33_795, "repayment_rate": 0.09, "write_off_years": 30,
     "rpi_margin_max": 0.0, "interest_cap": 0.045, "income_upper": None,
     "note": "Scottish students (SAAS)."},
    {"name": "Plan 5", "threshold": 25_000, "repayment_rate": 0.09, "write_off_years": 40,
     "rpi_margin_max": 0.0, "interest_cap": None, "income_upper": None,
     "note": "RPI only. English/Welsh starters from Aug 2023."},
    {"name": "Postgraduate", "threshold": 21_000, "repayment_rate": 0.06, "write_off_years": 30,
     "rpi_margin_max": 0.03, "interest_cap": 0.06, "income_upper": 21_000,
     "note": "RPI + 3% flat; 6% cap in year 1 only."},
]
EXTRA_COLUMNS = {"rpi_margin_max": "REAL NOT NULL DEFAULT 0", "interest_cap": "REAL", "income_upper": "REAL",
                 "tax_year": "TEXT", "note": "TEXT"}


def _ensure_schema(conn):
    conn.execute("""CREATE TABLE IF NOT EXISTS loan_plans (id INTEGER PRIMARY KEY, name TEXT UNIQUE NOT NULL,
        threshold REAL NOT NULL, repayment_rate REAL NOT NULL, write_off_years INTEGER NOT NULL)""")
    existing = {row[1] for row in conn.execute("PRAGMA table_info(loan_plans)")}
    for col, ddl in EXTRA_COLUMNS.items():
        if col not in existing:
            conn.execute(f"ALTER TABLE loan_plans ADD COLUMN {col} {ddl}")


def seed(db_path=DB_PATH):
    """Upsert every plan; row ids stay stable so saved scenarios keep working."""
    with sqlite3.connect(db_path) as conn:
        _ensure_schema(conn)
        conn.executemany("""INSERT INTO loan_plans (name, threshold, repayment_rate, write_off_years,
            rpi_margin_max, interest_cap, income_upper, tax_year, note)
            VALUES (:name, :threshold, :repayment_rate, :write_off_years, :rpi_margin_max, :interest_cap,
                    :income_upper, :tax_year, :note)
            ON CONFLICT(name) DO UPDATE SET threshold=excluded.threshold, repayment_rate=excluded.repayment_rate,
                write_off_years=excluded.write_off_years, rpi_margin_max=excluded.rpi_margin_max,
                interest_cap=excluded.interest_cap, income_upper=excluded.income_upper,
                tax_year=excluded.tax_year, note=excluded.note""",
                         [{**r, "tax_year": TAX_YEAR} for r in PLAN_ROWS])
        return len(PLAN_ROWS)


def load_plans(db_path=DB_PATH):
    """Read plans from SQLite as {name: LoanPlan} for calc.py."""
    from calc import LoanPlan

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM loan_plans ORDER BY id"
        ).fetchall()

    return {
        r["name"]: LoanPlan(
            r["name"],
            r["threshold"],
            r["repayment_rate"],
            r["write_off_years"],
            r["rpi_margin_max"],
            r["interest_cap"],
            r["income_upper"],
        )
        for r in rows
    }
if __name__ == "__main__":
    print(f"Seeded {seed()} loan plans into {DB_PATH} ({TAX_YEAR} figures).")
    for name, p in load_plans().items():
        print(f"  {name:<13} threshold £{p.threshold:>8,.0f}  rate {p.repayment_rate:.0%}  write-off {p.write_off_years}y")