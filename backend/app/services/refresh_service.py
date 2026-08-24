"""refresh_service.py - manual "Refresh Data" action. Pulls the live
FMCSA OOS feed, finds carriers not already in our local database,
enriches ONLY those new ones via MCMIS, inserts them into SQLite, AND
pushes them into the same Azure AI Search index the Foundry Agent reads
from - so a newly-added carrier is immediately askable/outreach-able,
not just visible on the dashboard.

Reuses the existing, untouched fetch_and_enrich_oos_data.py and
build_search_index.py functions (same pattern as init_db.py) rather than
reimplementing the live API calls or the indexing logic. Never modifies
an existing opportunity's carrier facts or demo assignment/status data -
create_opportunity's INSERT OR IGNORE means a carrier already in the
database is always skipped untouched, and the search index push is a
pure additive upload (upsert by dot_number), never a rebuild."""

import sys

from dotenv import load_dotenv

# build_search_index.py reads AZURE_SEARCH_ENDPOINT/AZURE_SEARCH_KEY from
# os.environ at import time via its own load_dotenv() - but that call
# resolves relative to THIS process's cwd (backend/), not the AzureFoundry
# repo, so its .env would never be found. Loading it explicitly here first
# populates os.environ before the import runs; python-dotenv doesn't
# override already-set vars, so build_search_index's own load_dotenv()
# call becomes a harmless no-op afterward.
load_dotenv(r"C:\Users\nbaskaran\source\repos\AzureFoundry\.env")

sys.path.insert(0, r"C:\Users\nbaskaran\source\repos\AzureFoundry\src")
import fetch_and_enrich_oos_data as fmcsa  # noqa: E402
import build_search_index as search_index  # noqa: E402

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient

from .. import repository as repo
from ..database import get_connection
from . import assignment_service


def _index_new_records(new_records):
    """Uploads just these new carriers to the existing search index -
    additive only (upload_documents upserts by the 'id'/dot_number key),
    never touches rebuild_index() so the rest of the index is untouched.
    Returns (indexed_count, error) - error is None on success."""
    try:
        search_client = SearchClient(
            endpoint=search_index.SEARCH_ENDPOINT,
            index_name=search_index.INDEX_NAME,
            credential=AzureKeyCredential(search_index.SEARCH_KEY),
        )
        documents = [
            {
                "id": rec["dot_number"],
                "dot_number": rec["dot_number"],
                "legal_name": rec["legal_name"],
                "oos_date": rec["oos_date"],
                "oos_reason": rec["oos_reason"] or "",
                "phy_city": rec["city"] or "",
                "phy_state": rec["state"] or "",
                "content": search_index.build_content_sentence({
                    "legal_name": rec["legal_name"], "phy_city": rec["city"],
                    "phy_state": rec["state"], "oos_date": rec["oos_date"],
                    "oos_reason": rec["oos_reason"],
                }),
            }
            for rec in new_records
        ]
        for start in range(0, len(documents), search_index.BATCH_SIZE):
            search_client.upload_documents(documents=documents[start:start + search_index.BATCH_SIZE])
        return len(documents), None
    except Exception as e:
        return 0, f"Added to the dashboard, but could not update the AI search index: {e}"


def sync_latest_oos_data():
    """Returns a summary dict describing what happened. Never raises -
    network/API failures come back as {"ok": False, "error": ...} so the
    button can show a friendly message instead of crashing the page.

    Opens its OWN dedicated SQLite connection rather than sharing the
    app's single long-lived connection (see deps.get_db) - this sync can
    run for many seconds across dozens of sequential statements, and
    sharing one connection object across concurrent requests corrupts
    SQLite's cursor state (a real crash hit during testing: a second
    request landing mid-sync threw "bad parameter or other API misuse").
    A separate connection to the same file is the normal, safe way for
    SQLite to handle this."""
    conn = get_connection()
    try:
        try:
            oos_df = fmcsa.fetch_oos_data()
            oos_df = fmcsa.dedupe_by_carrier(oos_df)
        except Exception as e:
            return {"ok": False, "error": f"Could not reach the FMCSA data feed: {e}"}

        existing = {r["dot_number"] for r in conn.execute("SELECT dot_number FROM opportunities").fetchall()}
        oos_df["dot_number"] = oos_df["dot_number"].astype("Int64").astype(str)
        new_df = oos_df[~oos_df["dot_number"].isin(existing)]

        checked = len(oos_df)
        if new_df.empty:
            return {"ok": True, "checked": checked, "added": 0,
                    "message": f"Checked {checked} FMCSA records - already up to date, no new opportunities."}

        try:
            location_lookup = fmcsa.enrich_with_location([int(d) for d in new_df["dot_number"]])
        except Exception as e:
            return {"ok": False, "error": f"Could not reach the MCMIS enrichment feed: {e}"}

        before = conn.execute("SELECT COUNT(*) AS c FROM opportunities").fetchone()["c"]
        indexable = []

        for _, row in new_df.iterrows():
            dot_number = row["dot_number"]
            loc = location_lookup.get(int(dot_number), {})
            city, state = loc.get("city"), loc.get("state")

            assignment = assignment_service.assign_salesperson(state) if state else None
            if assignment:
                sp_name, region, manager_name = assignment
                manager_id = repo.get_or_create_manager(conn, manager_name, region)
                salesperson_id = repo.get_or_create_salesperson(conn, sp_name, region, manager_id, [state])
            else:
                salesperson_id, manager_id = None, None

            oos_date = row["oos_date"]
            oos_date = oos_date.strftime("%Y-%m-%d") if hasattr(oos_date, "strftime") else str(oos_date)[:10]
            oos_reason = row.get("oos_reason")

            repo.create_opportunity(
                conn, dot_number, row["legal_name"], oos_date, oos_reason,
                city, state, salesperson_id, manager_id,
            )
            indexable.append({
                "dot_number": dot_number, "legal_name": row["legal_name"], "oos_date": oos_date,
                "oos_reason": oos_reason, "city": city, "state": state,
            })

        after = conn.execute("SELECT COUNT(*) AS c FROM opportunities").fetchone()["c"]
        added = after - before

        indexed, index_error = _index_new_records(indexable)

        if added == 0:
            message = f"Checked {checked} FMCSA records - already up to date, no new opportunities."
        elif index_error:
            message = f"Checked {checked} FMCSA records - added {added} new opportunit{'y' if added == 1 else 'ies'}. {index_error}"
        else:
            message = (f"Checked {checked} FMCSA records - added {added} new opportunit{'y' if added == 1 else 'ies'} "
                        f"and indexed {indexed} for the AI Sales Assistant.")

        return {"ok": True, "checked": checked, "added": added, "indexed": indexed, "message": message}
    finally:
        conn.close()
