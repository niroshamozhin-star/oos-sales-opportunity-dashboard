"""load_to_db.py - loads the enriched OOS CSV (produced by the existing,
untouched AzureFoundry pipeline) into a local SQLite database.

Schema note: a state can have MULTIPLE reps (Sampath's "10 reps get
emailed, whoever claims first wins" scenario), so assignment is modeled as
a separate notifications table - one row per (opportunity, rep) pair -
rather than a single owner column on the opportunity itself."""

import sqlite3
import pandas as pd

SOURCE_CSV = r"C:\Users\nbaskaran\source\repos\AzureFoundry\data\OOS_Enriched_2026.csv"
HIERARCHY_CSV = "sales_hierarchy.csv"
DB_PATH = "sales_opportunities.db"


def create_schema(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sales_hierarchy (
            state TEXT,
            region TEXT,
            salesperson_name TEXT,
            salesperson_email TEXT,
            manager_name TEXT,
            manager_email TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS opportunities (
            dot_number TEXT PRIMARY KEY,
            legal_name TEXT,
            oos_date TEXT,
            oos_reason TEXT,
            phy_city TEXT,
            phy_state TEXT,
            first_seen_date TEXT,
            status TEXT DEFAULT 'open',
            claimed_by TEXT,
            claimed_at TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dot_number TEXT,
            salesperson_name TEXT,
            salesperson_email TEXT,
            sent_at TEXT,
            FOREIGN KEY (dot_number) REFERENCES opportunities(dot_number)
        )
    """)
    conn.commit()


def load_hierarchy(conn):
    hierarchy_df = pd.read_csv(HIERARCHY_CSV)
    hierarchy_df.to_sql("sales_hierarchy", conn, if_exists="replace", index=False)
    print(f"Loaded {len(hierarchy_df)} state->rep mappings ({hierarchy_df['state'].nunique()} distinct states).")
    return hierarchy_df


def create_notifications_for_new_opportunity(cursor, dot_number, phy_state, hierarchy_df):
    """One notification row per rep assigned to this opportunity's state -
    this is what makes 'multiple reps get emailed' possible."""
    reps = hierarchy_df[hierarchy_df["state"] == phy_state]
    for _, rep in reps.iterrows():
        cursor.execute(
            "INSERT INTO notifications (dot_number, salesperson_name, salesperson_email) VALUES (?, ?, ?)",
            (dot_number, rep["salesperson_name"], rep["salesperson_email"]),
        )


def load_opportunities(conn, hierarchy_df):
    df = pd.read_csv(SOURCE_CSV, dtype={"dot_number": str})

    cursor = conn.cursor()
    inserted, updated = 0, 0
    for _, row in df.iterrows():
        existing = cursor.execute(
            "SELECT dot_number FROM opportunities WHERE dot_number = ?",
            (row["dot_number"],),
        ).fetchone()

        if existing:
            cursor.execute(
                """UPDATE opportunities SET legal_name=?, oos_date=?, oos_reason=?,
                   phy_city=?, phy_state=? WHERE dot_number=?""",
                (row["legal_name"], row["oos_date"], row["oos_reason"],
                 row["phy_city"], row["phy_state"], row["dot_number"]),
            )
            updated += 1
        else:
            cursor.execute(
                """INSERT INTO opportunities
                   (dot_number, legal_name, oos_date, oos_reason, phy_city, phy_state,
                    first_seen_date, status)
                   VALUES (?, ?, ?, ?, ?, ?, date('now'), 'open')""",
                (row["dot_number"], row["legal_name"], row["oos_date"], row["oos_reason"],
                 row["phy_city"], row["phy_state"]),
            )
            create_notifications_for_new_opportunity(cursor, row["dot_number"], row["phy_state"], hierarchy_df)
            inserted += 1

    conn.commit()
    print(f"Opportunities: {inserted} new, {updated} updated.")


def main():
    conn = sqlite3.connect(DB_PATH)
    create_schema(conn)
    hierarchy_df = load_hierarchy(conn)
    load_opportunities(conn, hierarchy_df)
    conn.close()
    print(f"Done. Database at {DB_PATH}")


if __name__ == "__main__":
    main()
