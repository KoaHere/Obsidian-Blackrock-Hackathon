
import sqlite3


def get_conn(path="finance.db"):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_conn() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS loan_plans (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            threshold REAL NOT NULL,
            repayment_rate REAL NOT NULL,
            write_off_years INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS scenarios (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            plan_id INTEGER REFERENCES loan_plans(id),
            loan_balance REAL,
            salary REAL,
            monthly_invest REAL,
            annual_return REAL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            description TEXT NOT NULL,
            category TEXT NOT NULL,
            amount REAL NOT NULL CHECK (amount > 0),
            date TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        """)
