"""repository.py - the data access layer. All SQLite-specific code lives
here; the service/router layers above never write raw SQL themselves.
This is the seam where SQLite could later be swapped for Azure SQL
without touching anything above it."""

from datetime import datetime, timedelta

ALLOWED_TRANSITIONS = {
    "NEW": {"ASSIGNED"},
    "ASSIGNED": {"OUTREACH_SENT", "CLOSED"},
    "OUTREACH_SENT": {"IN_PROGRESS", "CLOSED"},
    "IN_PROGRESS": {"CLOSED"},
    "CLOSED": set(),
}


def now():
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")


# ---- Salespeople / Managers ----

def get_or_create_manager(conn, name, region):
    row = conn.execute("SELECT manager_id FROM managers WHERE name = ?", (name,)).fetchone()
    if row:
        return row["manager_id"]
    cur = conn.execute("INSERT INTO managers (name, region) VALUES (?, ?)", (name, region))
    conn.commit()
    return cur.lastrowid


def get_or_create_salesperson(conn, name, region, manager_id, territories):
    row = conn.execute("SELECT salesperson_id FROM salespersons WHERE name = ?", (name,)).fetchone()
    if row:
        return row["salesperson_id"]
    cur = conn.execute(
        "INSERT INTO salespersons (name, region, manager_id, territories) VALUES (?, ?, ?, ?)",
        (name, region, manager_id, ",".join(territories)),
    )
    conn.commit()
    return cur.lastrowid


def get_salespeople(conn, region=None, manager_id=None, state=None):
    query = """
        SELECT sp.*, m.name AS manager_name
        FROM salespersons sp
        JOIN managers m ON m.manager_id = sp.manager_id
        WHERE 1=1
    """
    params = []
    if region:
        query += " AND sp.region = ?"
        params.append(region)
    if manager_id:
        query += " AND sp.manager_id = ?"
        params.append(manager_id)
    if state:
        query += " AND (',' || sp.territories || ',') LIKE ?"
        params.append(f"%,{state},%")
    return [dict(r) for r in conn.execute(query, params).fetchall()]


def get_salesperson_summary(conn, date_from=None, date_to=None):
    """Per-salesperson counts for the Sales Team page table. Scoped to
    the same oos_date window as the Overview page (date_from/date_to) so
    the two pages' counts reconcile - the date condition lives in the
    JOIN's ON clause, not WHERE, so a rep with zero opportunities in the
    window still shows a row of zeros instead of disappearing."""
    query = """
        SELECT sp.salesperson_id, sp.name, sp.region, m.name AS manager_name,
            COUNT(o.opportunity_id) AS assigned,
            SUM(CASE WHEN o.outreach_status = 'SENT' THEN 1 ELSE 0 END) AS outreach_sent,
            SUM(CASE WHEN o.status = 'IN_PROGRESS' THEN 1 ELSE 0 END) AS in_progress,
            SUM(CASE WHEN o.status = 'CLOSED' THEN 1 ELSE 0 END) AS closed
        FROM salespersons sp
        JOIN managers m ON m.manager_id = sp.manager_id
        LEFT JOIN opportunities o ON o.salesperson_id = sp.salesperson_id
    """
    params = []
    if date_from:
        query += " AND o.oos_date >= ?"
        params.append(date_from)
    if date_to:
        query += " AND o.oos_date <= ?"
        params.append(date_to)
    query += " GROUP BY sp.salesperson_id ORDER BY assigned DESC"
    return [dict(r) for r in conn.execute(query, params).fetchall()]


# ---- Opportunities ----

def create_opportunity(conn, dot_number, carrier_legal_name, oos_date, oos_reason, city, state,
                        salesperson_id, manager_id):
    ts = now()
    status = "NEW" if salesperson_id is None else "ASSIGNED"
    cur = conn.execute(
        """INSERT OR IGNORE INTO opportunities
           (dot_number, carrier_legal_name, oos_date, oos_reason, city, state,
            salesperson_id, manager_id, status, outreach_status, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'NOT_STARTED', ?, ?)""",
        (dot_number, carrier_legal_name, oos_date, oos_reason, city, state,
         salesperson_id, manager_id, status, ts, ts),
    )
    conn.commit()
    if cur.rowcount:
        record_status_history(conn, cur.lastrowid, None, status, "system")
    return cur.lastrowid


def record_status_history(conn, opportunity_id, previous_status, new_status, changed_by):
    conn.execute(
        """INSERT INTO opportunity_status_history
           (opportunity_id, previous_status, new_status, changed_at, changed_by)
           VALUES (?, ?, ?, ?, ?)""",
        (opportunity_id, previous_status, new_status, now(), changed_by),
    )
    conn.commit()


def get_opportunity_by_id(conn, opportunity_id):
    row = conn.execute("""
        SELECT o.*, sp.name AS salesperson_name, m.name AS manager_name
        FROM opportunities o
        LEFT JOIN salespersons sp ON sp.salesperson_id = o.salesperson_id
        LEFT JOIN managers m ON m.manager_id = o.manager_id
        WHERE o.opportunity_id = ?
    """, (opportunity_id,)).fetchone()
    return dict(row) if row else None


def get_opportunity_history(conn, opportunity_id):
    rows = conn.execute(
        "SELECT * FROM opportunity_status_history WHERE opportunity_id = ? ORDER BY changed_at",
        (opportunity_id,),
    ).fetchall()
    return [dict(r) for r in rows]


OPPORTUNITY_SORT_COLUMNS = {
    "opportunity_id": "o.opportunity_id", "carrier_legal_name": "o.carrier_legal_name",
    "oos_date": "o.oos_date", "city": "o.city", "state": "o.state",
    "salesperson_name": "sp.name", "manager_name": "m.name",
    "status": "o.status", "outreach_status": "o.outreach_status", "updated_at": "o.updated_at",
}


def get_opportunities(conn, state=None, salesperson_id=None, manager_id=None, status=None,
                       outreach_status=None, search=None, date_from=None, date_to=None,
                       limit=50, offset=0, sort_by=None, sort_dir="desc"):
    query = """
        SELECT o.*, sp.name AS salesperson_name, m.name AS manager_name
        FROM opportunities o
        LEFT JOIN salespersons sp ON sp.salesperson_id = o.salesperson_id
        LEFT JOIN managers m ON m.manager_id = o.manager_id
        WHERE 1=1
    """
    params = []
    if state:
        query += " AND o.state = ?"
        params.append(state)
    if salesperson_id:
        query += " AND o.salesperson_id = ?"
        params.append(salesperson_id)
    if manager_id:
        query += " AND o.manager_id = ?"
        params.append(manager_id)
    if status:
        query += " AND o.status = ?"
        params.append(status)
    if outreach_status:
        query += " AND o.outreach_status = ?"
        params.append(outreach_status)
    if search:
        query += " AND o.carrier_legal_name LIKE ?"
        params.append(f"%{search}%")
    if date_from:
        query += " AND o.oos_date >= ?"
        params.append(date_from)
    if date_to:
        query += " AND o.oos_date <= ?"
        params.append(date_to)

    count_query = f"SELECT COUNT(*) AS c FROM ({query})"
    total = conn.execute(count_query, params).fetchone()["c"]

    sort_col = OPPORTUNITY_SORT_COLUMNS.get(sort_by, "o.oos_date")
    direction = "ASC" if str(sort_dir).lower() == "asc" else "DESC"
    query += f" ORDER BY {sort_col} {direction} LIMIT ? OFFSET ?"
    params += [limit, offset]
    rows = conn.execute(query, params).fetchall()
    return {"total": total, "items": [dict(r) for r in rows]}


def assign_opportunity(conn, opportunity_id, salesperson_id, manager_id):
    """Manually assigns a NEW opportunity to a salesperson/manager and
    advances it to ASSIGNED - the only entry point for the "Assign
    Salesperson" drawer action. Only valid from NEW, same as the rest of
    the state machine."""
    opp = get_opportunity_by_id(conn, opportunity_id)
    if not opp:
        raise ValueError(f"Opportunity {opportunity_id} not found")
    if opp["status"] != "NEW":
        raise ValueError(f"Opportunity is already {opp['status']} - it has already been assigned.")

    conn.execute(
        "UPDATE opportunities SET salesperson_id = ?, manager_id = ?, updated_at = ? WHERE opportunity_id = ?",
        (salesperson_id, manager_id, now(), opportunity_id),
    )
    conn.commit()
    return update_opportunity_status(conn, opportunity_id, "ASSIGNED", "user")


def update_opportunity_status(conn, opportunity_id, new_status, changed_by="user"):
    opp = get_opportunity_by_id(conn, opportunity_id)
    if not opp:
        raise ValueError(f"Opportunity {opportunity_id} not found")
    current = opp["status"]
    if new_status not in ALLOWED_TRANSITIONS.get(current, set()):
        raise ValueError(f"Invalid transition: {current} -> {new_status}")
    conn.execute(
        "UPDATE opportunities SET status = ?, updated_at = ? WHERE opportunity_id = ?",
        (new_status, now(), opportunity_id),
    )
    conn.commit()
    record_status_history(conn, opportunity_id, current, new_status, changed_by)
    return get_opportunity_by_id(conn, opportunity_id)


# ---- Outreach ----

def create_outreach_record(conn, opportunity_id, salesperson_id):
    cur = conn.execute(
        "INSERT INTO outreach (opportunity_id, salesperson_id, status) VALUES (?, ?, 'NOT_GENERATED')",
        (opportunity_id, salesperson_id),
    )
    conn.commit()
    return cur.lastrowid


def get_outreach_for_opportunity(conn, opportunity_id):
    row = conn.execute(
        "SELECT * FROM outreach WHERE opportunity_id = ? ORDER BY outreach_id DESC LIMIT 1",
        (opportunity_id,),
    ).fetchone()
    return dict(row) if row else None


def save_generated_outreach(conn, opportunity_id, message):
    ts = now()
    existing = get_outreach_for_opportunity(conn, opportunity_id)
    if existing:
        conn.execute(
            "UPDATE outreach SET message = ?, generated_at = ?, status = 'GENERATED' WHERE outreach_id = ?",
            (message, ts, existing["outreach_id"]),
        )
    else:
        opp = get_opportunity_by_id(conn, opportunity_id)
        conn.execute(
            """INSERT INTO outreach (opportunity_id, salesperson_id, generated_at, status, message)
               VALUES (?, ?, ?, 'GENERATED', ?)""",
            (opportunity_id, opp["salesperson_id"], ts, message),
        )
    conn.commit()


def mark_outreach_sent(conn, opportunity_id):
    opp = get_opportunity_by_id(conn, opportunity_id)
    if not opp:
        raise ValueError(f"Opportunity {opportunity_id} not found")
    if not opp["salesperson_id"]:
        raise ValueError(
            "This opportunity has no assigned salesperson (no territory mapping for its "
            "state) - outreach can't be sent until someone owns it."
        )

    ts = now()
    conn.execute(
        "UPDATE outreach SET sent_at = ?, status = 'SENT' WHERE opportunity_id = ?",
        (ts, opportunity_id),
    )
    conn.execute(
        "UPDATE opportunities SET outreach_status = 'SENT', updated_at = ? WHERE opportunity_id = ?",
        (ts, opportunity_id),
    )
    conn.commit()
    update_opportunity_status(conn, opportunity_id, "OUTREACH_SENT", "user")


def get_outreach_by_state(conn, date_from=None, date_to=None):
    query = """
        SELECT o.state, COUNT(*) AS count
        FROM outreach out JOIN opportunities o ON o.opportunity_id = out.opportunity_id
        WHERE out.status IN ('GENERATED', 'SENT') AND o.state IS NOT NULL
    """
    params = []
    if date_from:
        query += " AND o.oos_date >= ?"
        params.append(date_from)
    if date_to:
        query += " AND o.oos_date <= ?"
        params.append(date_to)
    query += " GROUP BY o.state ORDER BY count DESC"
    return [dict(r) for r in conn.execute(query, params).fetchall()]


def get_outreach_by_salesperson(conn, date_from=None, date_to=None):
    query = """
        SELECT sp.name AS salesperson, COUNT(*) AS count
        FROM outreach out
        JOIN salespersons sp ON sp.salesperson_id = out.salesperson_id
        JOIN opportunities o ON o.opportunity_id = out.opportunity_id
        WHERE out.status IN ('GENERATED', 'SENT')
    """
    params = []
    if date_from:
        query += " AND o.oos_date >= ?"
        params.append(date_from)
    if date_to:
        query += " AND o.oos_date <= ?"
        params.append(date_to)
    query += " GROUP BY sp.name ORDER BY count DESC"
    return [dict(r) for r in conn.execute(query, params).fetchall()]


def get_outreach_trend(conn, date_from=None, date_to=None, granularity="daily", month=None):
    """granularity: "daily" | "weekly" (year-week) | "monthly" (year-month,
    used to list which months have data) | "week_of_month" (requires
    month="YYYY-MM" - buckets that one month's records into W1..W5 by
    day-of-month, for the Outreach Trend month drill-down)."""
    if granularity == "week_of_month":
        date_expr = "'W' || (((CAST(strftime('%d', out.generated_at) AS INTEGER) - 1) / 7) + 1)"
    elif granularity == "monthly":
        date_expr = "strftime('%Y-%m', out.generated_at)"
    elif granularity == "weekly":
        date_expr = "strftime('%Y-W%W', out.generated_at)"
    else:
        date_expr = "date(out.generated_at)"
    query = f"""
        SELECT {date_expr} AS date, COUNT(*) AS count
        FROM outreach out JOIN opportunities o ON o.opportunity_id = out.opportunity_id
        WHERE out.generated_at IS NOT NULL
    """
    params = []
    if granularity == "week_of_month" and month:
        query += " AND strftime('%Y-%m', out.generated_at) = ?"
        params.append(month)
    if date_from:
        query += " AND o.oos_date >= ?"
        params.append(date_from)
    if date_to:
        query += " AND o.oos_date <= ?"
        params.append(date_to)
    query += " GROUP BY date ORDER BY date"
    return [dict(r) for r in conn.execute(query, params).fetchall()]


OUTREACH_SORT_COLUMNS = {
    "carrier": "o.carrier_legal_name", "salesperson": "sp.name",
    "generated_at": "out.generated_at", "sent_at": "out.sent_at", "status": "out.status",
}


def get_outreach_summary(conn, state=None, salesperson_id=None, status=None, date_from=None, date_to=None,
                          limit=None, offset=0, sort_by=None, sort_dir="desc"):
    """Returns (total, items). limit=None returns everything unpaginated
    (used by /outreach/kpis, which needs the full matching set to compute
    correct counts) - pass a limit to paginate (used by the Outreach
    Records list)."""
    query = """
        SELECT out.outreach_id, o.carrier_legal_name AS carrier, sp.name AS salesperson,
               out.generated_at, out.sent_at, out.status
        FROM outreach out
        JOIN opportunities o ON o.opportunity_id = out.opportunity_id
        LEFT JOIN salespersons sp ON sp.salesperson_id = out.salesperson_id
        WHERE 1=1
    """
    params = []
    if state:
        query += " AND o.state = ?"
        params.append(state)
    if salesperson_id:
        query += " AND out.salesperson_id = ?"
        params.append(salesperson_id)
    if status:
        query += " AND out.status = ?"
        params.append(status)
    if date_from:
        query += " AND o.oos_date >= ?"
        params.append(date_from)
    if date_to:
        query += " AND o.oos_date <= ?"
        params.append(date_to)

    total = conn.execute(f"SELECT COUNT(*) AS c FROM ({query})", params).fetchone()["c"]

    sort_col = OUTREACH_SORT_COLUMNS.get(sort_by, "out.generated_at")
    direction = "ASC" if str(sort_dir).lower() == "asc" else "DESC"
    query += f" ORDER BY {sort_col} {direction}"
    if limit is not None:
        query += " LIMIT ? OFFSET ?"
        params = params + [limit, offset]

    items = [dict(r) for r in conn.execute(query, params).fetchall()]
    return total, items


# ---- Dashboard metrics ----

def get_latest_oos_date(conn):
    row = conn.execute("SELECT MAX(oos_date) AS latest FROM opportunities").fetchone()
    return row["latest"]


def compute_last_n_days_range(conn, days=60):
    """date_to = latest OOS date actually in the dataset (never assumes
    today), date_from = date_to - (days-1). Matches the spec's explicit
    instruction not to assume today's date if the dataset doesn't contain
    today's records - the FMCSA source has a real multi-day publishing lag."""
    latest = get_latest_oos_date(conn)
    if not latest:
        return None, None
    date_to = datetime.strptime(latest, "%Y-%m-%d")
    date_from = date_to - timedelta(days=days - 1)
    return date_from.strftime("%Y-%m-%d"), date_to.strftime("%Y-%m-%d")


def get_dashboard_metrics(conn, date_from=None, date_to=None):
    params = []
    if date_from:
        params.append(date_from)
    if date_to:
        params.append(date_to)

    status_query = "SELECT status, COUNT(*) AS c FROM opportunities WHERE 1=1"
    if date_from:
        status_query += " AND oos_date >= ?"
    if date_to:
        status_query += " AND oos_date <= ?"
    status_query += " GROUP BY status"
    status_rows = conn.execute(status_query, params).fetchall()
    status_counts = {r["status"]: r["c"] for r in status_rows}

    outreach_query = "SELECT outreach_status, COUNT(*) AS c FROM opportunities WHERE 1=1"
    if date_from:
        outreach_query += " AND oos_date >= ?"
    if date_to:
        outreach_query += " AND oos_date <= ?"
    outreach_query += " GROUP BY outreach_status"
    outreach_rows = conn.execute(outreach_query, params).fetchall()
    outreach_counts = {r["outreach_status"]: r["c"] for r in outreach_rows}

    return {
        "new_opportunities": status_counts.get("NEW", 0),
        "assigned": sum(v for k, v in status_counts.items() if k != "NEW"),
        "outreach_sent": outreach_counts.get("SENT", 0),
        "in_progress": status_counts.get("IN_PROGRESS", 0),
        "closed": status_counts.get("CLOSED", 0),
    }


def get_opportunities_by_state(conn, date_from=None, date_to=None, limit=10):
    query = "SELECT state, COUNT(*) AS count FROM opportunities WHERE state IS NOT NULL"
    params = []
    if date_from:
        query += " AND oos_date >= ?"
        params.append(date_from)
    if date_to:
        query += " AND oos_date <= ?"
        params.append(date_to)
    query += " GROUP BY state ORDER BY count DESC LIMIT ?"
    params.append(limit)
    return [dict(r) for r in conn.execute(query, params).fetchall()]


def get_opportunities_by_status(conn, date_from=None, date_to=None):
    query = "SELECT status, COUNT(*) AS count FROM opportunities WHERE 1=1"
    params = []
    if date_from:
        query += " AND oos_date >= ?"
        params.append(date_from)
    if date_to:
        query += " AND oos_date <= ?"
        params.append(date_to)
    query += " GROUP BY status"
    return [dict(r) for r in conn.execute(query, params).fetchall()]


def get_opportunity_trend(conn, date_from=None, date_to=None, granularity="daily"):
    date_expr = "oos_date" if granularity == "daily" else "strftime('%Y-W%W', oos_date)"
    query = f"SELECT {date_expr} AS bucket, COUNT(*) AS count FROM opportunities WHERE 1=1"
    params = []
    if date_from:
        query += " AND oos_date >= ?"
        params.append(date_from)
    if date_to:
        query += " AND oos_date <= ?"
        params.append(date_to)
    query += " GROUP BY bucket ORDER BY bucket"
    return [dict(r) for r in conn.execute(query, params).fetchall()]


def get_recent_opportunities(conn, limit=10):
    query = """
        SELECT o.*, sp.name AS salesperson_name, m.name AS manager_name
        FROM opportunities o
        LEFT JOIN salespersons sp ON sp.salesperson_id = o.salesperson_id
        LEFT JOIN managers m ON m.manager_id = o.manager_id
        ORDER BY o.oos_date DESC LIMIT ?
    """
    return [dict(r) for r in conn.execute(query, (limit,)).fetchall()]
