"""database.py - SQLite connection and schema for the OOS Sales Opportunity
Command Center. Deliberately raw sqlite3 (not an ORM) so the repository
layer's SQL is explicit and easy to port to Azure SQL later - only this
file and repository.py would need to change for that migration."""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "sales_opportunity.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS managers (
    manager_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    region TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS salespersons (
    salesperson_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    region TEXT NOT NULL,
    manager_id INTEGER NOT NULL,
    territories TEXT NOT NULL,
    FOREIGN KEY (manager_id) REFERENCES managers(manager_id)
);

CREATE TABLE IF NOT EXISTS opportunities (
    opportunity_id INTEGER PRIMARY KEY AUTOINCREMENT,
    dot_number TEXT UNIQUE,
    carrier_legal_name TEXT NOT NULL,
    oos_date TEXT NOT NULL,
    oos_reason TEXT,
    city TEXT,
    state TEXT,
    salesperson_id INTEGER,
    manager_id INTEGER,
    status TEXT NOT NULL DEFAULT 'NEW',
    outreach_status TEXT NOT NULL DEFAULT 'NOT_STARTED',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (salesperson_id) REFERENCES salespersons(salesperson_id),
    FOREIGN KEY (manager_id) REFERENCES managers(manager_id)
);

CREATE TABLE IF NOT EXISTS outreach (
    outreach_id INTEGER PRIMARY KEY AUTOINCREMENT,
    opportunity_id INTEGER NOT NULL,
    salesperson_id INTEGER,
    generated_at TEXT,
    sent_at TEXT,
    status TEXT NOT NULL DEFAULT 'NOT_GENERATED',
    message TEXT,
    FOREIGN KEY (opportunity_id) REFERENCES opportunities(opportunity_id),
    FOREIGN KEY (salesperson_id) REFERENCES salespersons(salesperson_id)
);

CREATE TABLE IF NOT EXISTS opportunity_status_history (
    history_id INTEGER PRIMARY KEY AUTOINCREMENT,
    opportunity_id INTEGER NOT NULL,
    previous_status TEXT,
    new_status TEXT NOT NULL,
    changed_at TEXT NOT NULL,
    changed_by TEXT,
    FOREIGN KEY (opportunity_id) REFERENCES opportunities(opportunity_id)
);

CREATE INDEX IF NOT EXISTS idx_opportunities_state ON opportunities(state);
CREATE INDEX IF NOT EXISTS idx_opportunities_status ON opportunities(status);
CREATE INDEX IF NOT EXISTS idx_opportunities_salesperson ON opportunities(salesperson_id);
CREATE INDEX IF NOT EXISTS idx_opportunities_oos_date ON opportunities(oos_date);
"""


def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_schema(conn):
    conn.executescript(SCHEMA)
    conn.commit()
