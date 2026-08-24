"""init_db.py - creates the SQLite schema and loads the real FMCSA
assessment data (via the existing, untouched AzureFoundry enrichment
pipeline), then deterministically assigns each opportunity to a
salesperson/manager by state. Carrier facts (name, OOS date/reason,
city, state) are never modified - only the assignment layer is
demo/prototype data, as required by the spec."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd

from app.database import get_connection, init_schema
from app import repository as repo
from app.services import assignment_service

SOURCE_CSV = r"C:\Users\nbaskaran\source\repos\AzureFoundry\data\OOS_Enriched_2026.csv"


def seed_org(conn):
    manager_ids = {}
    for m in assignment_service.all_managers():
        manager_ids[m["name"]] = repo.get_or_create_manager(conn, m["name"], m["region"])

    salesperson_ids = {}
    for sp in assignment_service.all_salespeople():
        manager_id = manager_ids[sp["manager"]]
        salesperson_ids[sp["name"]] = repo.get_or_create_salesperson(
            conn, sp["name"], sp["region"], manager_id, sp["territories"]
        )
    return manager_ids, salesperson_ids


def load_opportunities(conn, manager_ids, salesperson_ids):
    df = pd.read_csv(SOURCE_CSV, dtype={"dot_number": str})
    created = 0
    for _, row in df.iterrows():
        assignment = assignment_service.assign_salesperson(row["phy_state"])
        if assignment:
            sp_name, _, manager_name = assignment
            salesperson_id = salesperson_ids[sp_name]
            manager_id = manager_ids[manager_name]
        else:
            salesperson_id, manager_id = None, None

        repo.create_opportunity(
            conn, row["dot_number"], row["legal_name"], row["oos_date"], row["oos_reason"],
            row["phy_city"], row["phy_state"], salesperson_id, manager_id,
        )
        created += 1
    print(f"Processed {created} opportunities from real FMCSA assessment data.")


def seed_sample_outreach(conn, sample_size=15):
    """A handful of opportunities pre-populated through the full lifecycle
    (generated -> sent -> in progress -> closed), purely so the Overview
    dashboard has non-zero KPIs the first time you open it - not real
    outreach activity. Real outreach happens through the actual
    Generate/Send Outreach actions in the UI."""
    assigned = repo.get_opportunities(conn, status=None, limit=sample_size * 4, offset=0)["items"]
    assigned = [o for o in assigned if o["salesperson_id"]][:sample_size]

    for i, opp in enumerate(assigned):
        message = (
            f"Hi {opp['carrier_legal_name']}, I see your operations were recently impacted by an "
            f"out-of-service notice dated {opp['oos_date']}. Can we set up a call to discuss new "
            f"sales opportunities?"
        )
        repo.save_generated_outreach(conn, opp["opportunity_id"], message)
        if i % 3 != 0:  # leave some as generated-only, most as sent
            repo.mark_outreach_sent(conn, opp["opportunity_id"])
            if i % 2 == 0:
                repo.update_opportunity_status(conn, opp["opportunity_id"], "IN_PROGRESS", "seed")
                if i % 5 == 0:
                    repo.update_opportunity_status(conn, opp["opportunity_id"], "CLOSED", "seed")
    print(f"Seeded {len(assigned)} sample outreach records for initial dashboard KPIs.")


def main():
    conn = get_connection()
    init_schema(conn)
    manager_ids, salesperson_ids = seed_org(conn)
    print(f"Seeded {len(manager_ids)} managers, {len(salesperson_ids)} salespeople.")
    load_opportunities(conn, manager_ids, salesperson_ids)
    seed_sample_outreach(conn)
    print("Database initialized at backend/sales_opportunity.db")


if __name__ == "__main__":
    main()
