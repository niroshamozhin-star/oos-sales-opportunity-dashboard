"""opportunities.py - the Opportunities page and Opportunity Details API.
Status changes and pagination are deterministic application logic - the
LLM is only ever invoked for the one 'generate outreach' action, and even
then only to produce the message text, not to decide anything."""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from .. import repository as repo
from ..deps import get_db
from ..services import foundry_service, email_service, assignment_service

router = APIRouter(prefix="/api/opportunities", tags=["opportunities"])

# Default oos_date scope for this page when no explicit date_from/date_to is
# given - the same trailing window as the Overview page, so the "X total
# opportunities" figure here reconciles with Overview's headline KPIs
# instead of silently including the full historical archive.
WINDOW_DAYS = 60


@router.get("")
def list_opportunities(
    state: str = None, salesperson_id: int = None, manager_id: int = None,
    status: str = None, outreach_status: str = None, search: str = None,
    date_from: str = None, date_to: str = None,
    limit: int = Query(50, le=500), offset: int = Query(0),
    sort_by: str = None, sort_dir: str = Query("desc"),
    conn=Depends(get_db),
):
    if date_from is None and date_to is None:
        date_from, date_to = repo.compute_last_n_days_range(conn, days=WINDOW_DAYS)
    return repo.get_opportunities(
        conn, state=state, salesperson_id=salesperson_id, manager_id=manager_id,
        status=status, outreach_status=outreach_status, search=search,
        date_from=date_from, date_to=date_to, limit=limit, offset=offset,
        sort_by=sort_by, sort_dir=sort_dir,
    )


@router.get("/{opportunity_id}")
def get_opportunity(opportunity_id: int, conn=Depends(get_db)):
    opp = repo.get_opportunity_by_id(conn, opportunity_id)
    if not opp:
        raise HTTPException(404, "Opportunity not found")
    opp["history"] = repo.get_opportunity_history(conn, opportunity_id)
    opp["outreach"] = repo.get_outreach_for_opportunity(conn, opportunity_id)
    return opp


class StatusUpdate(BaseModel):
    status: str
    changed_by: str = "user"


@router.post("/{opportunity_id}/status")
def update_status(opportunity_id: int, body: StatusUpdate, conn=Depends(get_db)):
    try:
        return repo.update_opportunity_status(conn, opportunity_id, body.status, body.changed_by)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/{opportunity_id}/assign")
def assign_salesperson(opportunity_id: int, conn=Depends(get_db)):
    """Deterministic assignment for a NEW opportunity - no LLM involved.
    Looks up the salesperson/manager for the opportunity's state (falling
    back to the closest region if there's no formally owned territory),
    reuses the existing salespersons/managers rows for that name, and
    advances the opportunity to ASSIGNED."""
    opp = repo.get_opportunity_by_id(conn, opportunity_id)
    if not opp:
        raise HTTPException(404, "Opportunity not found")
    if opp["status"] != "NEW":
        raise HTTPException(400, f"Opportunity is already {opp['status']} - it has already been assigned.")

    salesperson_name, region, manager_name = assignment_service.assign_salesperson_with_fallback(opp["state"])
    manager_id = repo.get_or_create_manager(conn, manager_name, region)
    salesperson_id = repo.get_or_create_salesperson(conn, salesperson_name, region, manager_id, [opp["state"]])

    try:
        updated = repo.assign_opportunity(conn, opportunity_id, salesperson_id, manager_id)
    except ValueError as e:
        raise HTTPException(400, str(e))

    return {"status": "ok", "salesperson_name": salesperson_name, "manager_name": manager_name, "opportunity": updated}


@router.post("/{opportunity_id}/generate-outreach")
def generate_outreach(opportunity_id: int, conn=Depends(get_db)):
    opp = repo.get_opportunity_by_id(conn, opportunity_id)
    if not opp:
        raise HTTPException(404, "Opportunity not found")

    message, error = foundry_service.generate_outreach_for_carrier(opp["carrier_legal_name"], opp["oos_date"])
    if error:
        # Dashboard keeps working even if Foundry is unreachable - this
        # is a 200 with an explicit unavailable flag, not a crash.
        return {"available": False, "message": None,
                "error": "AI Assistant is temporarily unavailable. Dashboard functionality is still available."}

    repo.save_generated_outreach(conn, opportunity_id, message)
    return {"available": True, "message": message, "error": None}


@router.post("/{opportunity_id}/send-outreach")
def send_outreach(opportunity_id: int, conn=Depends(get_db)):
    """DEMO send workflow: sends a real email (via email_service) to a
    fixed demo inbox, standing in for the assigned salesperson's real
    address, which this schema doesn't have. If SMTP isn't configured,
    falls back to a simulated confirmation instead of failing the whole
    action - never claim a real email was sent when it wasn't."""
    opp = repo.get_opportunity_by_id(conn, opportunity_id)
    if not opp:
        raise HTTPException(404, "Opportunity not found")

    outreach = repo.get_outreach_for_opportunity(conn, opportunity_id)
    if not outreach or not outreach.get("message"):
        raise HTTPException(400, "Generate an outreach message before sending.")

    try:
        repo.mark_outreach_sent(conn, opportunity_id)
    except ValueError as e:
        raise HTTPException(400, str(e))

    if email_service.is_configured():
        sent, error = email_service.send_outreach_email(
            carrier_name=opp["carrier_legal_name"],
            salesperson_name=opp["salesperson_name"] or "Unassigned",
            message=outreach["message"],
        )
        if sent:
            return {
                "status": "ok", "demo": True, "email_sent": True,
                "message": f"Outreach emailed to {email_service.DEMO_TO_EMAIL} (Demo Email Workflow).",
            }
        return {
            "status": "ok", "demo": True, "email_sent": False,
            "message": f"Outreach marked as sent, but the demo email failed to send: {error}",
        }

    return {
        "status": "ok", "demo": True, "email_sent": False,
        "message": "Outreach marked as sent. (Demo Email Workflow - SMTP not configured, no real email sent.)",
    }
