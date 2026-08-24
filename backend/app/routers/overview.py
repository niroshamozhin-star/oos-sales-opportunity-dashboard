"""overview.py - the Overview dashboard's API: KPIs, trend, by-state,
by-status, recent opportunities. Every number here comes from SQL
aggregation - no LLM involved anywhere in this file."""

from fastapi import APIRouter, Depends, Query

from .. import repository as repo
from ..deps import get_db

router = APIRouter(prefix="/api/overview", tags=["overview"])


def _resolve_range(conn, days):
    return repo.compute_last_n_days_range(conn, days=days)


@router.get("/metrics")
def metrics(days: int = Query(60), conn=Depends(get_db)):
    date_from, date_to = _resolve_range(conn, days)
    data = repo.get_dashboard_metrics(conn, date_from, date_to)
    return {**data, "date_from": date_from, "date_to": date_to, "label": f"Last {days} Days"}


@router.get("/trend")
def trend(days: int = Query(60), granularity: str = Query("daily"), conn=Depends(get_db)):
    date_from, date_to = _resolve_range(conn, days)
    return {"date_from": date_from, "date_to": date_to,
            "data": repo.get_opportunity_trend(conn, date_from, date_to, granularity)}


@router.get("/by-state")
def by_state(days: int = Query(60), limit: int = Query(10), conn=Depends(get_db)):
    date_from, date_to = _resolve_range(conn, days)
    return {"data": repo.get_opportunities_by_state(conn, date_from, date_to, limit)}


@router.get("/by-status")
def by_status(days: int = Query(60), conn=Depends(get_db)):
    date_from, date_to = _resolve_range(conn, days)
    return {"data": repo.get_opportunities_by_status(conn, date_from, date_to)}


@router.get("/recent")
def recent(limit: int = Query(10), conn=Depends(get_db)):
    return {"data": repo.get_recent_opportunities(conn, limit)}
