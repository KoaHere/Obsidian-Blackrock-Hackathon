"""
seed.py - load UK student loan policy figures into the `loan_plans` table.

Run:  python seed.py            (safe to re-run; it upserts by plan name)

Why this exists: thresholds and interest rules change every year. Keeping them
in the database means updating a number is a one-row change, not a code change.

Also exposes load_plans() which turns DB rows back into the LoanPlan objects
that calc.py uses, so the app reads policy from SQLite, not from calc.PLANS.
"""

import sqlite3
from calc import LoanPlan

DB_PATH = "finance.db"
TAX_YEAR = "2026/27"

# Source: HMRC/GOV.UK 2026/27 thresholds; DfE/SLC interest update 10 Aug 2026.
# VERIFY on gov.uk before presenting - these change every year.
PLAN_ROWS = [
    {
        "name": "Plan 2",
        "threshold": 29_385,
        "repayment_rate": 0.09,
        "write_off_years": 30,
        "rpi_margin_max": 0.03,
        "interest_cap": 0.06,      # temporary cap, Sep 2026 - Aug 2027
        "income_upper": 52_000,    # APPROXIMATE - confirm on gov.uk
        "note": "RPI to RPI+3% sliding with income; 6% cap in year 1 only.",
    },
    {
        "name": "Plan 5",
        "threshold": 25_000,
        "repayment_rate": 0.09,
        "write_off_years": 40,
        "rpi_margin_max": 0.0,
        "interest_cap": None,
        "income_upper": None,
        "note": "RPI only. English/Welsh starters from Aug 2023.",
    },
    {
        "name": "Postgraduate",
        "threshold": 21_000,
        "repayment_rate": 0.06,
        "write_off_years": 30,
        "rpi_margin_max": 0.03,
        "interest_cap": 0.06,
        "income_upper": 21_000,
        "note": "RPI + 3% flat; 6% cap in year 1 only.",
    },
]

# Columns added after the first version of the table (see db.py).
EXTRA_COLUMNS = {
    "rpi_margin_max": "REAL NOT NULL DEFAULT 0",
    "interest_cap": "REAL",
    "income_upper": "REAL",
    "tax_year": "TEXT",
    "note": "TEXT",
}


def _ensure_schema(conn: sqlite3.Connection) -> None:
    """Create loan_plans if missing, and add any new columns to an old one."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS loan_plans (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            threshold REAL NOT NULL,
            repayment_rate REAL NOT NULL,
            write_off_years INTEGER NOT NULL
        )
    """)
    existing = {row[1] for row in conn.execute("PRAGMA table_info(loan_plans)")}
    for col, ddl in EXTRA_COLUMNS.items():
        if col not in existing:
            conn.execute(f"ALTER TABLE loan_plans ADD COLUMN {col} {ddl}")


def seed(db_path: str = DB_PATH) -> int:
    """Insert or update every plan. Keeps row ids stable so saved scenarios
    that reference loan_plans(id) are not broken by re-seeding."""
    with sqlite3.connect(db_path) as conn:
        _ensure_schema(conn)
        conn.executemany(
            """
            INSERT INTO loan_plans
                (name, threshold, repayment_rate, write_off_years,
                 rpi_margin_max, interest_cap, income_upper, tax_year, note)
            VALUES
                (:name, :threshold, :repayment_rate, :write_off_years,
                 :rpi_margin_max, :interest_cap, :income_upper, :tax_year,
                 :note)
            ON CONFLICT(name) DO UPDATE SET
                threshold       = excluded.threshold,
                repayment_rate  = excluded.repayment_rate,
                write_off_years = excluded.write_off_years,
                rpi_margin_max  = excluded.rpi_margin_max,
                interest_cap    = excluded.interest_cap,
                income_upper    = excluded.income_upper,
                tax_year        = excluded.tax_year,
                note            = excluded.note
            """,
            [{**row, "tax_year": TAX_YEAR} for row in PLAN_ROWS],
        )
        return len(PLAN_ROWS)


def load_plans(db_path: str = DB_PATH) -> dict[str, LoanPlan]:
    """Read plans from SQLite as {name: LoanPlan} for use with calc.py."""
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM loan_plans ORDER BY id").fetchall()
    return {
        r["name"]: LoanPlan(
            name=r["name"],
            threshold=r["threshold"],
            repayment_rate=r["repayment_rate"],
            write_off_years=r["write_off_years"],
            rpi_margin_max=r["rpi_margin_max"],
            interest_cap=r["interest_cap"],
            income_upper=r["income_upper"],
        )
        for r in rows
    }


if __name__ == "__main__":
    n = seed()
    print(f"Seeded {n} loan plans into {DB_PATH} ({TAX_YEAR} figures).")
    for name, p in load_plans().items():
        print(f"  {name:<13} threshold £{p.threshold:>8,.0f}  "
              f"rate {p.repayment_rate:.0%}  write-off {p.write_off_years}y")