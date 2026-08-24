import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, LabelList,
} from "recharts";
import { ChevronRight } from "lucide-react";
import { getMetrics, getByState, getByStatus, getRecentOpportunities } from "../api/client";
import type { DashboardMetrics, StateCount, StatusCount, Opportunity } from "../api/types";
import {
  PageHeader, KpiCard, Card, StatusBadge, LoadingState,
  TABLE_HEAD_ROW_CLASS, tableRowClass, SortableTh, nextSort,
} from "../components/shared";
import type { SortDir } from "../components/shared";
import OpportunityDrawer from "../components/OpportunityDrawer";

// Donut/legend colors - a dedicated palette for this one chart, matching
// the reference design exactly. Deliberately distinct from StatusBadge's
// colors used elsewhere (this is a visual restyle scoped to the Overview
// charts only, per the request - it doesn't touch any other screen).
const DONUT_COLORS: Record<string, string> = {
  NEW: "#f97316", ASSIGNED: "#2a78d6", OUTREACH_SENT: "#14b8a6",
  IN_PROGRESS: "#8b5cf6", CLOSED: "#84cc16",
};
const STATUS_LABELS: Record<string, string> = {
  NEW: "New (Unassigned)", ASSIGNED: "Assigned", OUTREACH_SENT: "Outreach Sent",
  IN_PROGRESS: "In Progress", CLOSED: "Closed",
};
const STATUS_ORDER = ["NEW", "ASSIGNED", "OUTREACH_SENT", "IN_PROGRESS", "CLOSED"];

const US_STATE_NAMES: Record<string, string> = {
  AL: "Alabama", AK: "Alaska", AZ: "Arizona", AR: "Arkansas", CA: "California",
  CO: "Colorado", CT: "Connecticut", DE: "Delaware", DC: "District of Columbia",
  FL: "Florida", GA: "Georgia", HI: "Hawaii", ID: "Idaho", IL: "Illinois",
  IN: "Indiana", IA: "Iowa", KS: "Kansas", KY: "Kentucky", LA: "Louisiana",
  ME: "Maine", MD: "Maryland", MA: "Massachusetts", MI: "Michigan", MN: "Minnesota",
  MS: "Mississippi", MO: "Missouri", MT: "Montana", NE: "Nebraska", NV: "Nevada",
  NH: "New Hampshire", NJ: "New Jersey", NM: "New Mexico", NY: "New York",
  NC: "North Carolina", ND: "North Dakota", OH: "Ohio", OK: "Oklahoma", OR: "Oregon",
  PA: "Pennsylvania", RI: "Rhode Island", SC: "South Carolina", SD: "South Dakota",
  TN: "Tennessee", TX: "Texas", UT: "Utah", VT: "Vermont", VA: "Virginia",
  WA: "Washington", WV: "West Virginia", WI: "Wisconsin", WY: "Wyoming",
  PR: "Puerto Rico", VI: "US Virgin Islands", GU: "Guam",
};

function formatK(value: number) {
  if (value >= 1000) {
    const k = value / 1000;
    return `${Number.isInteger(k) ? k : k.toFixed(1)}K`;
  }
  return String(value);
}

export default function Overview() {
  const navigate = useNavigate();
  const [days, setDays] = useState(60);
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [byState, setByState] = useState<StateCount[]>([]);
  const [byStatus, setByStatus] = useState<StatusCount[]>([]);
  const [recent, setRecent] = useState<Opportunity[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedOpp, setSelectedOpp] = useState<number | null>(null);
  const [recentSortBy, setRecentSortBy] = useState<string | null>("oos_date");
  const [recentSortDir, setRecentSortDir] = useState<SortDir>("desc");

  useEffect(() => {
    setLoading(true);
    Promise.all([
      getMetrics(days), getByState(days, 10), getByStatus(days), getRecentOpportunities(10),
    ]).then(([m, s, st, r]) => {
      setMetrics(m); setByState(s); setByStatus(st); setRecent(r);
    }).finally(() => setLoading(false));
  }, [days]);

  // Stabilize these array references - otherwise any unrelated re-render
  // (e.g. the days selector, sorting Recent Opportunities) recomputes a
  // brand-new array every time, which Recharts treats as "new data" and
  // re-triggers its grow-in animation, looking like a flicker even though
  // the underlying values never changed.
  const orderedStatus = useMemo(
    () => STATUS_ORDER.map((key) => byStatus.find((s) => s.status === key)).filter((s): s is StatusCount => Boolean(s)),
    [byStatus]
  );
  const stateChartData = useMemo(
    () => [...byState].reverse().map((s) => ({ code: s.state, name: US_STATE_NAMES[s.state] ?? s.state, count: s.count })),
    [byState]
  );

  if (loading || !metrics) return <LoadingState label="Loading dashboard..." />;

  const statusTotal = orderedStatus.reduce((sum, s) => sum + s.count, 0);

  const handleRecentSort = (key: string) => {
    const { key: k, dir } = nextSort(recentSortBy, recentSortDir, key);
    setRecentSortBy(k); setRecentSortDir(dir);
  };
  const sortedRecent = [...recent].sort((a, b) => {
    const av = (a as any)[recentSortBy ?? "oos_date"] ?? "";
    const bv = (b as any)[recentSortBy ?? "oos_date"] ?? "";
    const cmp = String(av).localeCompare(String(bv), undefined, { numeric: true });
    return recentSortDir === "asc" ? cmp : -cmp;
  });

  return (
    <div>
      <PageHeader
        title="OOS Sales Opportunity Dashboard"
        subtitle="Identify, assign and track FMCSA Out-of-Service sales opportunities."
        action={
          <select
            value={days}
            onChange={(e) => setDays(Number(e.target.value))}
            className="border border-slate-300 rounded-lg px-3 py-2 text-sm bg-white"
          >
            <option value={30}>Last 30 Days</option>
            <option value={60}>Last 60 Days</option>
            <option value={90}>Last 90 Days</option>
          </select>
        }
      />
      <p className="text-xs text-slate-400 -mt-4 mb-6">
        {metrics.label}
        {metrics.date_from && metrics.date_to && ` (${metrics.date_from} to ${metrics.date_to})`}
      </p>

      <div className="grid grid-cols-5 gap-4 mb-6">
        <KpiCard label="New Opportunities" value={metrics.new_opportunities} accent="#898781" onClick={() => navigate("/opportunities?status=NEW")} />
        <KpiCard label="Assigned" value={metrics.assigned} onClick={() => navigate("/opportunities?status=ASSIGNED")} />
        <KpiCard label="Outreach Sent" value={metrics.outreach_sent} accent="#fab219" onClick={() => navigate("/opportunities?outreach_status=SENT")} />
        <KpiCard label="In Progress" value={metrics.in_progress} accent="#4a3aa7" onClick={() => navigate("/opportunities?status=IN_PROGRESS")} />
        <KpiCard label="Closed" value={metrics.closed} accent="#0ca30c" onClick={() => navigate("/opportunities?status=CLOSED")} />
      </div>

      <div className="grid grid-cols-2 gap-4 mb-6">
        {/* Opportunities by Status - donut */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold text-white">Opportunities by Status</h3>
            <button
              onClick={() => navigate("/opportunities")}
              className="flex items-center gap-0.5 text-xs font-medium text-blue-400 hover:text-blue-300"
            >
              View Details <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>
          <div className="flex items-center justify-center gap-10">
            <div className="relative shrink-0" style={{ width: 300, height: 300 }}>
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={orderedStatus}
                    dataKey="count"
                    nameKey="status"
                    innerRadius={100}
                    outerRadius={145}
                    paddingAngle={2}
                    stroke="none"
                    cursor="pointer"
                    isAnimationActive={false}
                    onClick={(d: any) => navigate(`/opportunities?status=${d.status}`)}
                  >
                    {orderedStatus.map((s) => (
                      <Cell key={s.status} fill={DONUT_COLORS[s.status]} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(value: any, _name: any, p: any) => [value, STATUS_LABELS[p.payload.status]]} />
                </PieChart>
              </ResponsiveContainer>
              <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                <div className="font-display text-4xl font-extrabold text-white tabular-nums">{statusTotal.toLocaleString()}</div>
                <div className="text-sm text-slate-400">Total</div>
              </div>
            </div>
            <div className="flex flex-col gap-3">
              {orderedStatus.map((s) => (
                <button
                  key={s.status}
                  onClick={() => navigate(`/opportunities?status=${s.status}`)}
                  className="flex items-center gap-2.5 text-left hover:opacity-80 transition-opacity"
                >
                  <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ background: DONUT_COLORS[s.status] }} />
                  <span className="text-sm text-slate-300 whitespace-nowrap">{STATUS_LABELS[s.status]}</span>
                  <span className="text-sm font-semibold text-white tabular-nums whitespace-nowrap">
                    {s.count.toLocaleString()}
                    <span className="text-slate-500 font-normal"> ({statusTotal ? ((s.count / statusTotal) * 100).toFixed(1) : "0.0"}%)</span>
                  </span>
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Opportunities by State - horizontal bars */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold text-white">Opportunities by State (Top 10)</h3>
            <button
              onClick={() => navigate("/opportunities")}
              className="flex items-center gap-0.5 text-xs font-medium text-blue-400 hover:text-blue-300"
            >
              View All <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={stateChartData} layout="vertical" margin={{ left: 0, right: 28 }}>
              <defs>
                <linearGradient id="stateBarGradient" x1="0" y1="0" x2="1" y2="0">
                  <stop offset="0%" stopColor="#5598e7" />
                  <stop offset="100%" stopColor="#2a78d6" />
                </linearGradient>
              </defs>
              <CartesianGrid stroke="#1e293b" horizontal={false} />
              <XAxis
                type="number"
                tick={{ fontSize: 11, fill: "#64748b" }}
                tickFormatter={formatK}
                axisLine={{ stroke: "#1e293b" }}
                tickLine={false}
              />
              <YAxis
                type="category"
                dataKey="name"
                tick={{ fontSize: 12, fill: "#cbd5e1" }}
                width={110}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip
                formatter={(value: any) => [Number(value).toLocaleString(), "Opportunities"]}
                contentStyle={{ background: "#0f172a", border: "1px solid #1e293b", borderRadius: 8, color: "#e2e8f0" }}
              />
              <Bar
                dataKey="count"
                fill="url(#stateBarGradient)"
                radius={[0, 4, 4, 0]}
                barSize={16}
                cursor="pointer"
                isAnimationActive={false}
                onClick={(d: any) => navigate(`/opportunities?state=${d.code}`)}
              >
                <LabelList
                  dataKey="count"
                  position="right"
                  fill="#e2e8f0"
                  fontSize={12}
                  formatter={(v: any) => Number(v).toLocaleString()}
                />
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <Card>
        <h3 className="text-sm font-semibold text-slate-700 mb-3">Recent Opportunities</h3>
        <table className="w-full text-sm">
          <thead>
            <tr className={TABLE_HEAD_ROW_CLASS}>
              <SortableTh label="Carrier" sortKey="carrier_legal_name" activeKey={recentSortBy} dir={recentSortDir} onSort={handleRecentSort} />
              <SortableTh label="OOS Date" sortKey="oos_date" activeKey={recentSortBy} dir={recentSortDir} onSort={handleRecentSort} />
              <SortableTh label="City" sortKey="city" activeKey={recentSortBy} dir={recentSortDir} onSort={handleRecentSort} />
              <SortableTh label="State" sortKey="state" activeKey={recentSortBy} dir={recentSortDir} onSort={handleRecentSort} />
              <SortableTh label="Salesperson" sortKey="salesperson_name" activeKey={recentSortBy} dir={recentSortDir} onSort={handleRecentSort} />
              <SortableTh label="Manager" sortKey="manager_name" activeKey={recentSortBy} dir={recentSortDir} onSort={handleRecentSort} />
              <SortableTh label="Status" sortKey="status" activeKey={recentSortBy} dir={recentSortDir} onSort={handleRecentSort} />
              <SortableTh label="Outreach" sortKey="outreach_status" activeKey={recentSortBy} dir={recentSortDir} onSort={handleRecentSort} />
            </tr>
          </thead>
          <tbody>
            {sortedRecent.map((o, i) => (
              <tr
                key={o.opportunity_id}
                onClick={() => setSelectedOpp(o.opportunity_id)}
                className={tableRowClass(i, "hover:bg-blue-100 cursor-pointer border-b border-slate-100")}
              >
                <td className="py-2 px-3 font-medium text-slate-900">{o.carrier_legal_name}</td>
                <td className="py-2 px-3 text-slate-600">{o.oos_date}</td>
                <td className="py-2 px-3 text-slate-600">{o.city}</td>
                <td className="py-2 px-3 text-slate-600">{o.state}</td>
                <td className="py-2 px-3 text-slate-600">{o.salesperson_name ?? "Unassigned"}</td>
                <td className="py-2 px-3 text-slate-600">{o.manager_name ?? "—"}</td>
                <td className="py-2 px-3"><StatusBadge status={o.status} /></td>
                <td className="py-2 px-3"><StatusBadge status={o.outreach_status} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>

      <OpportunityDrawer opportunityId={selectedOpp} onClose={() => setSelectedOpp(null)} />
    </div>
  );
}
