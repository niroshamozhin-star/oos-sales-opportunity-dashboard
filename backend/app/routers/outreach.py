"""outreach.py - the Outreach Management page API. Pure aggregation - no
LLM involved (outreach generation itself lives on the opportunity detail
endpoint, since it's scoped to one carrier at a time).

Scoped to the same trailing 60-day oos_date window as the Overview page
(fixed, not a query param - there's no date picker on this page) so its
counts reconcile with Overview's headline KPIs."""

from fastapi import APIRouter, Depends, Query

from .. import repository as repo
from ..deps import get_db

router = APIRouter(prefix="/api/outreach", tags=["outreach"])

WINDOW_DAYS = 60


@router.get("/kpis")
def outreach_kpis(conn=Depends(get_db)):
    date_from, date_to = repo.compute_last_n_days_range(conn, days=WINDOW_DAYS)
    _, rows = repo.get_outreach_summary(conn, date_from=date_from, date_to=date_to)
    generated = sum(1 for r in rows if r["status"] in ("GENERATED", "SENT"))
    sent = sum(1 for r in rows if r["status"] == "SENT")
    return {"generated": generated, "sent": sent, "pending": generated - sent}


@router.get("/by-state")
def by_state(conn=Depends(get_db)):
    date_from, date_to = repo.compute_last_n_days_range(conn, days=WINDOW_DAYS)
    return {"data": repo.get_outreach_by_state(conn, date_from, date_to)}


@router.get("/by-salesperson")
def by_salesperson(conn=Depends(get_db)):
    date_from, date_to = repo.compute_last_n_days_range(conn, days=WINDOW_DAYS)
    return {"data": repo.get_outreach_by_salesperson(conn, date_from, date_to)}


@router.get("/trend")
def trend(granularity: str = Query("monthly"), month: str = None, conn=Depends(get_db)):
    date_from, date_to = repo.compute_last_n_days_range(conn, days=WINDOW_DAYS)
    return {"data": repo.get_outreach_trend(conn, date_from, date_to, granularity=granularity, month=month)}


@router.get("")
def list_outreach(
    state: str = None, salesperson_id: int = None, status: str = None,
    limit: int = Query(20, le=500), offset: int = Query(0),
    sort_by: str = None, sort_dir: str = Query("desc"),
    conn=Depends(get_db),
):
    date_from, date_to = repo.compute_last_n_days_range(conn, days=WINDOW_DAYS)
    total, items = repo.get_outreach_summary(
        conn, state=state, salesperson_id=salesperson_id, status=status,
        date_from=date_from, date_to=date_to, limit=limit, offset=offset,
        sort_by=sort_by, sort_dir=sort_dir,
    )
    return {"total": total, "data": items}
