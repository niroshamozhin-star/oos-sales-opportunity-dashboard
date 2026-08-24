"""backfill_search_index.py - one-off catch-up: indexes every opportunity
already in SQLite that isn't yet in the Azure AI Search index. Needed
because a batch of ~128 real opportunities were added by the Refresh Data
button before the index-sync fix existed, so they're visible on the
dashboard but were never pushed to the index the Foundry Agent reads
from. Going forward, refresh_service.sync_latest_oos_data() keeps the
two in sync automatically - this script only needs to run once to close
the historical gap."""

import sys

sys.path.insert(0, r"C:\Users\nbaskaran\source\repos\SalesOpportunityDashboard\backend")

from app.database import get_connection
from app.services import refresh_service
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient


def main():
    conn = get_connection()
    all_rows = conn.execute(
        "SELECT dot_number, carrier_legal_name, oos_date, oos_reason, city, state FROM opportunities"
    ).fetchall()
    print(f"Total opportunities in SQLite: {len(all_rows)}")

    search_client = SearchClient(
        endpoint=refresh_service.search_index.SEARCH_ENDPOINT,
        index_name=refresh_service.search_index.INDEX_NAME,
        credential=AzureKeyCredential(refresh_service.search_index.SEARCH_KEY),
    )

    indexed_dot_numbers = set()
    results = search_client.search(search_text="*", select=["dot_number"], top=1000)
    for r in results:
        indexed_dot_numbers.add(r["dot_number"])
    print(f"Already indexed: {len(indexed_dot_numbers)}")

    missing = [
        {"dot_number": row["dot_number"], "legal_name": row["carrier_legal_name"], "oos_date": row["oos_date"],
         "oos_reason": row["oos_reason"], "city": row["city"], "state": row["state"]}
        for row in all_rows if row["dot_number"] not in indexed_dot_numbers
    ]
    print(f"Missing from index: {len(missing)}")

    if missing:
        indexed, error = refresh_service._index_new_records(missing)
        print(f"Indexed: {indexed}, error: {error}")
    else:
        print("Nothing to backfill - index is already in sync with SQLite.")

    conn.close()


if __name__ == "__main__":
    main()
