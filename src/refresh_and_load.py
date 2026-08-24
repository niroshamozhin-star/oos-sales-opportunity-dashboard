"""refresh_and_load.py - the background job Sampath asked for: polls the
live FMCSA source directly every 5 minutes and loads straight into SQLite
- no CSV in between. Only genuinely new carriers get enriched each cycle,
so repeat cycles are fast even though the full dataset is 12,000+ records.

Schema note: a state can have MULTIPLE reps, so each new opportunity gets
one notifications row per rep assigned to its state (see load_to_db.py).

Reuses the existing, untouched fetch_and_enrich_oos_data.py via import -
this never modifies that file, just calls its functions."""

import sys
import time
import sqlite3
from datetime import datetime

import pandas as pd

sys.path.insert(0, r"C:\Users\nbaskaran\source\repos\AzureFoundry\src")
import fetch_and_enrich_oos_data as source  # noqa: E402

DB_PATH = "sales_opportunities.db"
HIERARCHY_CSV = "sales_hierarchy.csv"
REFRESH_INTERVAL_SECONDS = 300  # 5 minutes


def ensure_schema(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sales_hierarchy (
            state TEXT, region TEXT, salesperson_name TEXT,
            salesperson_email TEXT, manager_name TEXT, manager_email TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS opportunities (
            dot_number TEXT PRIMARY KEY, legal_name TEXT, oos_date TEXT,
            oos_reason TEXT, phy_city TEXT, phy_state TEXT,
            first_seen_date TEXT, status TEXT DEFAULT 'open',
            claimed_by TEXT, claimed_at TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT, dot_number TEXT,
            salesperson_name TEXT, salesperson_email TEXT, sent_at TEXT,
            FOREIGN KEY (dot_number) REFERENCES opportunities(dot_number)
        )
    """)
    conn.commit()


def load_hierarchy(conn):
    hierarchy_df = pd.read_csv(HIERARCHY_CSV)
    hierarchy_df.to_sql("sales_hierarchy", conn, if_exists="replace", index=False)
    return hierarchy_df


def get_existing_dot_numbers(conn):
    rows = conn.execute("SELECT dot_number FROM opportunities").fetchall()
    return {r[0] for r in rows}


def create_notifications_for_new_opportunity(cursor, dot_number, phy_state, hierarchy_df):
    reps = hierarchy_df[hierarchy_df["state"] == phy_state]
    for _, rep in reps.iterrows():
        cursor.execute(
            "INSERT INTO notifications (dot_number, salesperson_name, salesperson_email) VALUES (?, ?, ?)",
            (dot_number, rep["salesperson_name"], rep["salesperson_email"]),
        )


def run_one_cycle(conn, hierarchy_df):
    stamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{stamp}] Fetching latest OOS data from FMCSA...")
    raw_df = source.fetch_oos_data()
    deduped_df = source.dedupe_by_carrier(raw_df)

    existing = get_existing_dot_numbers(conn)
    deduped_df["dot_number_str"] = deduped_df["dot_number"].astype("Int64").astype(str)
    new_rows = deduped_df[~deduped_df["dot_number_str"].isin(existing)].copy()

    if new_rows.empty:
        print(f"[{stamp}] No new opportunities - source hasn't published anything new this cycle.")
        return 0

    print(f"[{stamp}] Found {len(new_rows)} new carrier(s) - enriching city/state...")
    location_lookup = source.enrich_with_location(new_rows["dot_number"].tolist())
    new_rows["phy_city"] = new_rows["dot_number"].map(lambda n: location_lookup.get(int(n), {}).get("city"))
    new_rows["phy_state"] = new_rows["dot_number"].map(lambda n: location_lookup.get(int(n), {}).get("state"))
    new_rows["oos_date_str"] = new_rows["oos_date"].dt.strftime("%Y-%m-%d")

    cursor = conn.cursor()
    for _, row in new_rows.iterrows():
        cursor.execute(
            """INSERT OR IGNORE INTO opportunities
               (dot_number, legal_name, oos_date, oos_reason, phy_city, phy_state,
                first_seen_date, status)
               VALUES (?, ?, ?, ?, ?, ?, date('now'), 'open')""",
            (row["dot_number_str"], row["legal_name"], row["oos_date_str"], row["oos_reason"],
             row["phy_city"], row["phy_state"]),
        )
        create_notifications_for_new_opportunity(cursor, row["dot_number_str"], row["phy_state"], hierarchy_df)

    conn.commit()
    print(f"[{stamp}] Loaded {len(new_rows)} new opportunities into the database.")
    return len(new_rows)


def main():
    conn = sqlite3.connect(DB_PATH)
    ensure_schema(conn)
    hierarchy_df = load_hierarchy(conn)

    print(f"Background refresh job started - polling every {REFRESH_INTERVAL_SECONDS // 60} minutes.")
    while True:
        start = time.time()
        try:
            run_one_cycle(conn, hierarchy_df)
        except Exception as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Cycle failed: {e}")

        elapsed = time.time() - start
        sleep_time = max(0, REFRESH_INTERVAL_SECONDS - elapsed)
        print(f"Sleeping {sleep_time:.0f}s until next cycle...\n")
        time.sleep(sleep_time)


if __name__ == "__main__":
    main()
