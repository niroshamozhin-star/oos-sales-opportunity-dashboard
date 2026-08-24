"""backfill_lifecycle_demo.py - one-off script to enrich the demo's
lifecycle data (salesperson/manager/status/outreach_status only) so the
dashboard tells a realistic story within the same 60-day window Overview
uses. Never touches carrier facts (dot_number, legal_name, oos_date,
oos_reason, city, state) - only opportunities.status/outreach_status and
the outreach table.

Run with the backend stopped (single-writer SQLite, avoids lock
contention with the app's long-lived connection).
"""

import random
import sqlite3
from datetime import datetime, timedelta

DB_PATH = r"C:\Users\nbaskaran\source\repos\SalesOpportunityDashboard\backend\sales_opportunity.db"

OUTREACH_TARGET = 300   # cumulative opportunities with outreach ever sent
IN_PROGRESS_TARGET = 70  # cumulative opportunities that ever reached IN_PROGRESS or CLOSED
CLOSED_TARGET = 25       # cumulative opportunities that ever reached CLOSED

TEMPLATE = (
    "Hi {carrier}, I see your operations were recently impacted by an "
    "out-of-service notice dated {oos_date}. Can we set up a call to "
    "discuss new sales opportunities?"
)


def ts(date_str, hour=9, minute=0):
    """Clamp to real 'today' (2026-08-24) so no synthetic timestamp is in the future."""
    today = datetime(2026, 8, 24)
    dt = datetime.strptime(date_str, "%Y-%m-%d").replace(hour=hour, minute=minute)
    return min(dt, today).strftime("%Y-%m-%d %H:%M:%S")


def main():
    random.seed(42)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")

    latest = conn.execute("SELECT MAX(oos_date) FROM opportunities").fetchone()[0]
    date_from = (datetime.strptime(latest, "%Y-%m-%d") - timedelta(days=59)).strftime("%Y-%m-%d")
    print(f"60-day window: {date_from} to {latest}")

    already_sent = conn.execute(
        "SELECT COUNT(*) FROM opportunities WHERE outreach_status = 'SENT'"
    ).fetchone()[0]
    already_progressed = conn.execute(
        "SELECT COUNT(*) FROM opportunities WHERE status IN ('IN_PROGRESS','CLOSED')"
    ).fetchone()[0]
    already_closed = conn.execute(
        "SELECT COUNT(*) FROM opportunities WHERE status = 'CLOSED'"
    ).fetchone()[0]
    print(f"Already sent: {already_sent}, already in-progress-or-beyond: {already_progressed}, already closed: {already_closed}")

    need_new_outreach = OUTREACH_TARGET - already_sent
    print(f"Need to newly send outreach for {need_new_outreach} more opportunities")

    # --- Step 1: newly send outreach for eligible ASSIGNED, in-window, state-assigned opportunities ---
    eligible = conn.execute(
        """SELECT opportunity_id, salesperson_id, carrier_legal_name, oos_date
           FROM opportunities
           WHERE status = 'ASSIGNED' AND salesperson_id IS NOT NULL
             AND oos_date >= ? AND oos_date <= ?""",
        (date_from, latest),
    ).fetchall()
    print(f"Eligible ASSIGNED pool in window: {len(eligible)}")

    chosen = random.sample(eligible, need_new_outreach)
    for row in chosen:
        opp_id, sp_id, carrier, oos_date = row["opportunity_id"], row["salesperson_id"], row["carrier_legal_name"], row["oos_date"]
        message = TEMPLATE.format(carrier=carrier, oos_date=oos_date)
        gen_ts = ts(oos_date, 9, 0)
        sent_ts = ts(oos_date, 9, 15)
        conn.execute(
            """INSERT INTO outreach (opportunity_id, salesperson_id, generated_at, sent_at, status, message)
               VALUES (?, ?, ?, ?, 'SENT', ?)""",
            (opp_id, sp_id, gen_ts, sent_ts, message),
        )
        conn.execute(
            "UPDATE opportunities SET outreach_status = 'SENT', status = 'OUTREACH_SENT', updated_at = ? WHERE opportunity_id = ?",
            (sent_ts, opp_id),
        )
        conn.execute(
            """INSERT INTO opportunity_status_history (opportunity_id, previous_status, new_status, changed_at, changed_by)
               VALUES (?, 'ASSIGNED', 'OUTREACH_SENT', ?, 'system-demo-seed')""",
            (opp_id, sent_ts),
        )
    conn.commit()
    print(f"Sent outreach for {len(chosen)} newly-chosen opportunities.")

    # --- Step 2: progress some currently-OUTREACH_SENT opportunities to IN_PROGRESS ---
    need_new_in_progress = IN_PROGRESS_TARGET - already_progressed
    currently_sent = conn.execute(
        """SELECT opportunity_id, oos_date FROM opportunities WHERE status = 'OUTREACH_SENT'"""
    ).fetchall()
    print(f"Currently OUTREACH_SENT pool: {len(currently_sent)}, need to progress {need_new_in_progress} to IN_PROGRESS")

    progressed = random.sample(currently_sent, need_new_in_progress)
    for row in progressed:
        opp_id, oos_date = row["opportunity_id"], row["oos_date"]
        changed_ts = ts(oos_date, 10, 0) if oos_date != latest else ts(oos_date, 14, 0)
        conn.execute(
            "UPDATE opportunities SET status = 'IN_PROGRESS', updated_at = ? WHERE opportunity_id = ?",
            (changed_ts, opp_id),
        )
        conn.execute(
            """INSERT INTO opportunity_status_history (opportunity_id, previous_status, new_status, changed_at, changed_by)
               VALUES (?, 'OUTREACH_SENT', 'IN_PROGRESS', ?, 'system-demo-seed')""",
            (opp_id, changed_ts),
        )
    conn.commit()
    print(f"Progressed {len(progressed)} opportunities to IN_PROGRESS.")

    # --- Step 3: close some currently-IN_PROGRESS opportunities ---
    need_new_closed = CLOSED_TARGET - already_closed
    currently_in_progress = conn.execute(
        """SELECT opportunity_id, oos_date FROM opportunities WHERE status = 'IN_PROGRESS'"""
    ).fetchall()
    print(f"Currently IN_PROGRESS pool: {len(currently_in_progress)}, need to close {need_new_closed}")

    closed = random.sample(currently_in_progress, need_new_closed)
    for row in closed:
        opp_id, oos_date = row["opportunity_id"], row["oos_date"]
        changed_ts = ts(oos_date, 16, 0)
        conn.execute(
            "UPDATE opportunities SET status = 'CLOSED', updated_at = ? WHERE opportunity_id = ?",
            (changed_ts, opp_id),
        )
        conn.execute(
            """INSERT INTO opportunity_status_history (opportunity_id, previous_status, new_status, changed_at, changed_by)
               VALUES (?, 'IN_PROGRESS', 'CLOSED', ?, 'system-demo-seed')""",
            (opp_id, changed_ts),
        )
    conn.commit()
    print(f"Closed {len(closed)} opportunities.")

    print("\n--- Final in-window status breakdown ---")
    for row in conn.execute(
        "SELECT status, COUNT(*) FROM opportunities WHERE oos_date >= ? AND oos_date <= ? GROUP BY status",
        (date_from, latest),
    ):
        print(dict(row) if isinstance(row, sqlite3.Row) else row)

    conn.close()


if __name__ == "__main__":
    main()
