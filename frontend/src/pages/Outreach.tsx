import { useEffect, useMemo, useState } from "react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, LabelList, Cell,
} from "recharts";
import { getOutreachKpis, getOutreachByState, getOutreachBySalesperson, getOutreachTrend, getOutreachList } from "../api/client";
import type { OutreachKpis, StateCount, OutreachListItem } from "../api/types";
import {
  PageHeader, Card, DarkCard, KpiCard, StatusBadge, LoadingState, EmptyState,
  SERIES_BLUE, TABLE_HEAD_ROW_CLASS, tableRowClass, SortableTh, nextSort, PageSizeSelect,
} from "../components/shared";
import type { SortDir } from "../components/shared";

const TOP_N_STATES = 10;
const OTHER_COLOR = "#64748b";
const MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

function monthLabel(yyyyMm: string) {
  const [year, month] = yyyyMm.split("-");
  return `${MONTH_NAMES[Number(month) - 1]} ${year}`;
}

export default function Outreach() {
  const [kpis, setKpis] = useState<OutreachKpis | null>(null);
  const [byState, setByState] = useState<StateCount[]>([]);
  const [bySalesperson, setBySalesperson] = useState<{ salesperson: string; count: number }[]>([]);
  const [availableMonths, setAvailableMonths] = useState<{ date: string; count: number }[]>([]);
  const [selectedMonth, setSelectedMonth] = useState<string | null>(null);
  const [trend, setTrend] = useState<{ date: string; count: number }[]>([]);
  const [list, setList] = useState<OutreachListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(10);
  const [sortBy, setSortBy] = useState<string | null>("generated_at");
  const [sortDir, setSortDir] = useState<SortDir>("desc");
  const [statusFilter, setStatusFilter] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([getOutreachKpis(), getOutreachByState(), getOutreachBySalesperson(), getOutreachTrend("monthly")])
      .then(([k, s, sp, months]) => {
        setKpis(k); setByState(s); setBySalesperson(sp); setAvailableMonths(months);
        if (months.length) setSelectedMonth(months[months.length - 1].date);
      })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (selectedMonth) getOutreachTrend("week_of_month", selectedMonth).then(setTrend);
  }, [selectedMonth]);

  useEffect(() => {
    getOutreachList({
      status: statusFilter || undefined, limit: pageSize, offset: page * pageSize,
      sort_by: sortBy ?? undefined, sort_dir: sortDir,
    }).then((res) => { setList(res.data); setTotal(res.total); });
  }, [statusFilter, page, pageSize, sortBy, sortDir]);

  useEffect(() => setPage(0), [statusFilter, pageSize, sortBy, sortDir]);

  const handleSort = (key: string) => {
    const { key: k, dir } = nextSort(sortBy, sortDir, key);
    setSortBy(k); setSortDir(dir);
  };

  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  // Stabilize the array reference passed to Recharts - otherwise a filter
  // change elsewhere in this component (status, page, sort) forces a
  // re-render that recomputes a brand-new array every time, which Recharts
  // treats as "new data" and re-triggers its grow-in animation, looking
  // like a flicker even though the underlying values never changed.
  const stateChartData = useMemo(() => {
    // byState already arrives sorted highest-to-lowest from the API - take
    // the top 10 real states and fold everything else into one "Other" bar.
    const top = byState.slice(0, TOP_N_STATES);
    const rest = byState.slice(TOP_N_STATES);
    const otherTotal = rest.reduce((sum, s) => sum + s.count, 0);
    return [...top, ...(otherTotal > 0 ? [{ state: "Other", count: otherTotal }] : [])].reverse();
  }, [byState]);

  if (loading || !kpis) return <LoadingState label="Loading outreach data..." />;

  return (
    <div>
      <PageHeader title="Outreach Management" subtitle="Track generated and sent outreach across all opportunities." />

      <div className="grid grid-cols-3 gap-4 mb-6">
        <KpiCard label="Outreach Generated" value={kpis.generated} />
        <KpiCard label="Outreach Sent" value={kpis.sent} accent="#0ca30c" />
        <KpiCard label="Pending Outreach" value={kpis.pending} accent="#fab219" />
      </div>

      <div className="grid grid-cols-3 gap-4 mb-6">
        <DarkCard>
          <h3 className="text-sm font-semibold text-white mb-3">Outreach by State (Top 10)</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={stateChartData} layout="vertical" margin={{ left: 0, right: 24 }}>
              <defs>
                <linearGradient id="outreachStateGradient" x1="0" y1="0" x2="1" y2="0">
                  <stop offset="0%" stopColor="#9ec5f4" />
                  <stop offset="100%" stopColor={SERIES_BLUE} />
                </linearGradient>
              </defs>
              <CartesianGrid stroke="#1e293b" horizontal={false} />
              <XAxis type="number" tick={{ fontSize: 11, fill: "#64748b" }} allowDecimals={false} axisLine={{ stroke: "#1e293b" }} tickLine={false} />
              <YAxis type="category" dataKey="state" tick={{ fontSize: 12, fill: "#cbd5e1" }} width={44} axisLine={false} tickLine={false} interval={0} />
              <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #1e293b", borderRadius: 8, color: "#e2e8f0" }} />
              <Bar dataKey="count" radius={[0, 4, 4, 0]} barSize={14} isAnimationActive={false}>
                {stateChartData.map((d) => (
                  <Cell key={d.state} fill={d.state === "Other" ? OTHER_COLOR : "url(#outreachStateGradient)"} />
                ))}
                <LabelList dataKey="count" position="right" fontSize={11} fill="#cbd5e1" />
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </DarkCard>

        <DarkCard>
          <h3 className="text-sm font-semibold text-white mb-3">Outreach by Salesperson</h3>
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={bySalesperson}>
              <CartesianGrid stroke="#1e293b" vertical={false} />
              <XAxis dataKey="salesperson" tick={{ fontSize: 10, fill: "#64748b" }} interval={0} angle={-20} textAnchor="end" height={50} axisLine={{ stroke: "#1e293b" }} tickLine={false} />
              <YAxis tick={{ fontSize: 11, fill: "#64748b" }} allowDecimals={false} axisLine={false} tickLine={false} />
              <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #1e293b", borderRadius: 8, color: "#e2e8f0" }} />
              <Bar dataKey="count" fill={SERIES_BLUE} radius={[4, 4, 0, 0]} isAnimationActive={false} />
            </BarChart>
          </ResponsiveContainer>
        </DarkCard>

        <DarkCard>
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-semibold text-white">Outreach Trend</h3>
            <select
              value={selectedMonth ?? ""}
              onChange={(e) => setSelectedMonth(e.target.value)}
              className="border border-white/20 bg-white/10 text-white text-xs rounded-lg px-2 py-1"
            >
              {availableMonths.map((m) => (
                <option key={m.date} value={m.date} className="text-slate-900">{monthLabel(m.date)}</option>
              ))}
            </select>
          </div>
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={trend}>
              <defs>
                <linearGradient id="outreachTrendBarGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#5598e7" />
                  <stop offset="100%" stopColor={SERIES_BLUE} />
                </linearGradient>
              </defs>
              <CartesianGrid stroke="#1e293b" vertical={false} />
              <XAxis dataKey="date" tick={{ fontSize: 10, fill: "#64748b" }} axisLine={{ stroke: "#1e293b" }} tickLine={false} />
              <YAxis tick={{ fontSize: 11, fill: "#64748b" }} allowDecimals={false} axisLine={false} tickLine={false} />
              <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #1e293b", borderRadius: 8, color: "#e2e8f0" }} />
              <Bar dataKey="count" fill="url(#outreachTrendBarGradient)" radius={[4, 4, 0, 0]} barSize={28} isAnimationActive={false} />
            </BarChart>
          </ResponsiveContainer>
        </DarkCard>
      </div>

      <Card>
        <div className="flex items-center justify-between mb-3 flex-wrap gap-3">
          <h3 className="text-sm font-semibold text-slate-700">Outreach Records <span className="text-slate-400 font-normal">({total} total)</span></h3>
          <div className="flex items-center gap-2">
            <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}
              className="border border-slate-300 rounded-lg px-3 py-1.5 text-sm bg-white">
              <option value="">All Statuses</option>
              <option value="GENERATED">Generated</option>
              <option value="SENT">Sent</option>
            </select>
            <PageSizeSelect value={pageSize} onChange={setPageSize} />
            <span className="text-sm text-slate-600 whitespace-nowrap">Page {page + 1} of {totalPages}</span>
            <button disabled={page === 0} onClick={() => setPage((p) => p - 1)}
              className="px-3 py-1.5 border border-slate-300 rounded-lg text-sm disabled:opacity-40">Previous</button>
            <button disabled={page >= totalPages - 1} onClick={() => setPage((p) => p + 1)}
              className="px-3 py-1.5 border border-slate-300 rounded-lg text-sm disabled:opacity-40">Next</button>
          </div>
        </div>
        {list.length === 0 ? <EmptyState message="No outreach records yet." /> : (
          <table className="w-full text-sm">
            <thead>
              <tr className={TABLE_HEAD_ROW_CLASS}>
                <SortableTh label="Carrier" sortKey="carrier" activeKey={sortBy} dir={sortDir} onSort={handleSort} />
                <SortableTh label="Salesperson" sortKey="salesperson" activeKey={sortBy} dir={sortDir} onSort={handleSort} />
                <SortableTh label="Generated At" sortKey="generated_at" activeKey={sortBy} dir={sortDir} onSort={handleSort} />
                <SortableTh label="Sent At" sortKey="sent_at" activeKey={sortBy} dir={sortDir} onSort={handleSort} />
                <SortableTh label="Status" sortKey="status" activeKey={sortBy} dir={sortDir} onSort={handleSort} />
              </tr>
            </thead>
            <tbody>
              {list.map((r, i) => (
                <tr key={r.outreach_id} className={tableRowClass(i, "border-b border-slate-100")}>
                  <td className="py-2 px-3 font-medium text-slate-900">{r.carrier}</td>
                  <td className="py-2 px-3 text-slate-600">{r.salesperson ?? "—"}</td>
                  <td className="py-2 px-3 text-slate-500 text-xs">{r.generated_at ?? "—"}</td>
                  <td className="py-2 px-3 text-slate-500 text-xs">{r.sent_at ?? "—"}</td>
                  <td className="py-2 px-3"><StatusBadge status={r.status} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  );
}
