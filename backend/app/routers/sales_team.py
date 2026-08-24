"""sales_team.py - the Sales Team page API. Pure aggregation over the
opportunities/salespersons tables - no LLM involved.

Takes the same days=30/60/90 query param as the Overview page (default
60) so this page's own date-range selector can match whatever window
Overview is showing, and their totals reconcile for the same selection."""

from fastapi import APIRouter, Depends, Query

from .. import repository as repo
from ..deps import get_db

router = APIRouter(prefix="/api/sales-team", tags=["sales-team"])


@router.get("")
def sales_team_summary(days: int = Query(60), conn=Depends(get_db)):
    date_from, date_to = repo.compute_last_n_days_range(conn, days=days)
    return {"data": repo.get_salesperson_summary(conn, date_from, date_to)}


@router.get("/{salesperson_id}/opportunities")
def salesperson_opportunities(salesperson_id: int, days: int = Query(60), limit: int = 50, offset: int = 0, conn=Depends(get_db)):
    date_from, date_to = repo.compute_last_n_days_range(conn, days=days)
    return repo.get_opportunities(
        conn, salesperson_id=salesperson_id, date_from=date_from, date_to=date_to,
        limit=limit, offset=offset,
    )
