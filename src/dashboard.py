"""dashboard.py - the reporting dashboard requested in the TR1 review:
a visual, data-driven view of sales opportunities (not a chatbot), showing
volume, assignment, and status at a glance. Reads only from the local
database - never calls the LLM or any external API.

Schema note: a state can have multiple reps, so assignment/notification
status lives in a separate notifications table (one row per opportunity x
rep), joined here rather than stored directly on the opportunity.

Colors follow the validated reference palette (see dataviz skill /
references/palette.md) - sequential blue for magnitude, the fixed status
palette (never themed) for SLA state, paired with icon + label so status
is never color-alone."""

import sqlite3
from datetime import datetime, timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

DB_PATH = "sales_opportunities.db"

st.set_page_config(page_title="Sales Opportunity Dashboard", page_icon="📊", layout="wide")

# ---- Palette (reference instance - see dataviz skill references/palette.md) ----
SEQUENTIAL_BLUE = ["#cde2fb", "#9ec5f4", "#5598e7", "#2a78d6", "#184f95"]
SERIES_BLUE = "#2a78d6"
STATUS_GOOD = "#0ca30c"
STATUS_CRITICAL = "#d03b3b"
STATUS_MUTED = "#898781"

CUSTOM_CSS = """
<style>
:root {
    --surface-1: #fcfcfb; --page: #f9f9f7; --text-primary: #0b0b0b;
    --text-secondary: #52514e; --border: rgba(11,11,11,0.10);
}
@media (prefers-color-scheme: dark) {
    :root {
        --surface-1: #1a1a19; --page: #0d0d0d; --text-primary: #ffffff;
        --text-secondary: #c3c2b7; --border: rgba(255,255,255,0.10);
    }
}
.kpi-card {
    background: var(--surface-1); border: 1px solid var(--border);
    border-radius: 10px; padding: 16px 18px; height: 100%;
}
.kpi-label {
    color: var(--text-secondary); font-size: 0.8rem; font-weight: 600;
    text-transform: uppercase; letter-spacing: 0.03em; margin-bottom: 6px;
}
.kpi-value {
    color: var(--text-primary); font-size: 2rem; font-weight: 700;
    font-variant-numeric: tabular-nums; line-height: 1.1;
}
.kpi-accent { border-top: 3px solid var(--accent-color, #2a78d6); }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def kpi_card(label, value, accent):
    st.markdown(
        f'<div class="kpi-card kpi-accent" style="--accent-color:{accent}">'
        f'<div class="kpi-label">{label}</div>'
        f'<div class="kpi-value">{value:,}</div></div>',
        unsafe_allow_html=True,
    )


def get_connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False)


conn = get_connection()
df = pd.read_sql("SELECT * FROM opportunities", conn)
notif_df = pd.read_sql("SELECT * FROM notifications", conn)

this_month = datetime.now().strftime("%Y-%m")
last_3_days_cutoff = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")

st.title("📊 Sales Opportunity Dashboard")
st.caption("Background job + database view - the reporting layer requested alongside the chat agent.")
st.caption(
    "Volume metrics use the carrier's actual out-of-service date (oos_date), not database "
    "ingestion time - the source FMCSA feed has a ~2-4 day publishing lag, so 'New (Last 3 Days)' "
    "accounts for that rather than showing 'New Today' as always zero."
)

# ---- KPI row ----
new_last_3_days = int((df["oos_date"] >= last_3_days_cutoff).sum())
new_this_month = int(df["oos_date"].str.startswith(this_month).sum())
resolved_this_month = int(
    ((df["status"] == "closed") & (df["claimed_at"].fillna("").str.startswith(this_month))).sum()
)
currently_open = int((df["status"] == "open").sum())
notifications_sent = int(notif_df["sent_at"].notna().sum())
notifications_pending = int(notif_df["sent_at"].isna().sum())

cols = st.columns(6)
with cols[0]:
    kpi_card("New (Last 3 Days)", new_last_3_days, SERIES_BLUE)
with cols[1]:
    kpi_card("New This Month", new_this_month, SERIES_BLUE)
with cols[2]:
    kpi_card("Resolved This Month", resolved_this_month, STATUS_GOOD)
with cols[3]:
    kpi_card("Currently Open", currently_open, SERIES_BLUE)
with cols[4]:
    kpi_card("Notifications Sent", notifications_sent, STATUS_GOOD)
with cols[5]:
    kpi_card("Pending (Unsent)", notifications_pending, "#fab219")

st.divider()

# ---- Charts row ----
left, right = st.columns(2)

with left:
    st.subheader("Opportunities by State (Top 10)")
    by_state = df["phy_state"].value_counts().head(10).reset_index()
    by_state.columns = ["state", "count"]
    by_state = by_state.sort_values("count")  # ascending so tallest bar reads top-to-bottom
    fig = go.Figure(go.Bar(
        x=by_state["count"], y=by_state["state"], orientation="h",
        marker=dict(
            color=by_state["count"], colorscale=SEQUENTIAL_BLUE,
            line=dict(width=0),
        ),
        hovertemplate="%{y}: %{x} opportunities<extra></extra>",
    ))
    fig.update_layout(
        margin=dict(l=10, r=10, t=10, b=10), height=340,
        xaxis=dict(title="Opportunities", gridcolor="#e1e0d9"),
        yaxis=dict(title=""), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig, width="stretch")

with right:
    st.subheader("Opportunities by OOS Date (last 30 days with data)")
    trend = df["oos_date"].value_counts().reset_index()
    trend.columns = ["date", "count"]
    trend = trend.sort_values("date").tail(30)
    fig2 = go.Figure(go.Scatter(
        x=trend["date"], y=trend["count"], mode="lines+markers",
        line=dict(color=SERIES_BLUE, width=2),
        marker=dict(size=8, color=SERIES_BLUE),
        hovertemplate="%{x}: %{y} opportunities<extra></extra>",
    ))
    fig2.update_layout(
        margin=dict(l=10, r=10, t=10, b=10), height=340,
        xaxis=dict(title="", gridcolor="#e1e0d9"),
        yaxis=dict(title="Opportunities", gridcolor="#e1e0d9"),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig2, width="stretch")

st.divider()

# ---- By salesperson: how many notified, sent, pending, and claims won ----
st.subheader("Notifications by Salesperson")
claims = df[df["status"] == "closed"][["claimed_by"]].rename(columns={"claimed_by": "salesperson_name"})
claims["won"] = 1
claims_by_rep = claims.groupby("salesperson_name")["won"].sum().reset_index()

by_rep = (
    notif_df.groupby("salesperson_name")
    .agg(
        total_notified=("id", "count"),
        sent=("sent_at", lambda s: s.notna().sum()),
        pending=("sent_at", lambda s: s.isna().sum()),
    )
    .reset_index()
    .merge(claims_by_rep, on="salesperson_name", how="left")
)
by_rep["won"] = by_rep["won"].fillna(0).astype(int)
by_rep = by_rep.sort_values("total_notified", ascending=False)
st.dataframe(by_rep, width="stretch", hide_index=True)
st.caption(
    "'won' = opportunities this rep actually claimed first - since multiple reps can be "
    "notified about the same opportunity, being notified doesn't guarantee winning it."
)

st.divider()


# ---- SLA status: icon + label, never color-alone (status palette is fixed/never themed) ----
def sla_status(row):
    if row["status"] == "closed":
        return "⚪ Closed"
    try:
        days_open = (datetime.now() - datetime.strptime(row["first_seen_date"], "%Y-%m-%d")).days
    except (TypeError, ValueError):
        return "— Unknown"
    return "🔴 Overdue (>2 days)" if days_open > 2 else "🟢 On Track"


df["sla_status"] = df.apply(sla_status, axis=1)

notif_counts = (
    notif_df.groupby("dot_number")
    .agg(reps_notified=("id", "count"), reps_pending=("sent_at", lambda s: s.isna().sum()))
    .reset_index()
)
df = df.merge(notif_counts, on="dot_number", how="left")

st.subheader("Individual Opportunities")
detail_cols = [
    "dot_number", "legal_name", "phy_state", "reps_notified", "reps_pending",
    "status", "sla_status", "claimed_by",
]
st.dataframe(df[detail_cols].head(200), width="stretch", hide_index=True)

# ---- Manual claim action ----
st.divider()
st.subheader("Mark an Opportunity as Claimed")
open_opps = df[df["status"] == "open"]
if not open_opps.empty:
    choice = st.selectbox(
        "Select an opportunity",
        open_opps["dot_number"] + " - " + open_opps["legal_name"],
    )
    claimer = st.text_input("Claimed by (salesperson name)")
    if st.button("Mark as Claimed") and claimer:
        dot_number = choice.split(" - ")[0]
        conn.execute(
            "UPDATE opportunities SET status='closed', claimed_by=?, claimed_at=datetime('now') WHERE dot_number=?",
            (claimer, dot_number),
        )
        conn.commit()
        st.success(f"Marked {choice} as claimed by {claimer}. Any other pending notifications for this opportunity are now moot.")
        st.rerun()
