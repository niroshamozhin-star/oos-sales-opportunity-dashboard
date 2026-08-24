"""refresh.py - the manual "Refresh Data" button's API. Deterministic
data-sync logic only - no LLM involved.

Deliberately does NOT use the shared Depends(get_db) connection - this
sync opens its own dedicated connection (see refresh_service) since it
runs long enough that sharing the app's single connection with other
concurrent requests can corrupt SQLite's cursor state."""

from fastapi import APIRouter

from ..services import refresh_service

router = APIRouter(prefix="/api/refresh", tags=["refresh"])


@router.post("")
def refresh_data():
    return refresh_service.sync_latest_oos_data()
