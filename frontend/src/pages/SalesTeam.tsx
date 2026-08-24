import { useEffect, useState } from "react";
import { getSalesTeam, getSalespersonOpportunities } from "../api/client";
import type { SalespersonSummary, Opportunity } from "../api/types";
import {
  PageHeader, Card, StatusBadge, LoadingState, KpiCard,
  TABLE_HEAD_ROW_CLASS, tableRowClass, SortableTh, nextSort,
} from "../components/shared";
import type { SortDir } from "../components/shared";
import OpportunityDrawer from "../components/OpportunityDrawer";

function sortRows<T>(rows: T[], sortBy: string | null, sortDir: SortDir): T[] {
  if (!sortBy) return rows;
  return [...rows].sort((a, b) => {
    const av = (a as any)[sortBy] ?? "";
    const bv = (b as any)[sortBy] ?? "";
    const cmp = typeof av === "number" && typeof bv === "number"
      ? av - bv
      : String(av).localeCompare(String(bv), undefined, { numeric: true });
    return sortDir === "asc" ? cmp : -cmp;
  });
}

export default function SalesTeam() {
  const [days, setDays] = useState(60);
  const [team, setTeam] = useState<SalespersonSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [regionFilter, setRegionFilter] = useState("");
  const [managerFilter, setManagerFilter] = useState("");
  const [selected, setSelected] = useState<SalespersonSummary | null>(null);
  const [portfolio, setPortfolio] = useState<Opportunity[]>([]);
  const [selectedOpp, setSelectedOpp] = useState<number | null>(null);
  const [teamSortBy, setTeamSortBy] = useState<string | null>("name");
  const [teamSortDir, setTeamSortDir] = useState<SortDir>("asc");
  const [portfolioSortBy, setPortfolioSortBy] = useState<string | null>("carrier_legal_name");
  const [portfolioSortDir, setPortfolioSortDir] = useState<SortDir>("asc");

  useEffect(() => {
    setLoading(true);
    getSalesTeam(days).then((data) => { setTeam(data); setLoading(false); });
  }, [days]);

  useEffect(() => {
    if (selected) {
      getSalespersonOpportunities(selected.salesperson_id, days).then((res) => setPortfolio(res.items));
    }
  }, [selected, days]);

  const regions = [...new Set(team.map((t) => t.region))];
  const managers = [...new Set(team.map((t) => t.manager_name))];

  const filtered = team.filter(
    (t) => (!regionFilter || t.region === regionFilter) && (!managerFilter || t.manager_name === managerFilter)
  );

  const totals = filtered.reduce(
    (acc, t) => ({
      assigned: acc.assigned + t.assigned,
      outreach_sent: acc.outreach_sent + t.outreach_sent,
      in_progress: acc.in_progress + t.in_progress,
      closed: acc.closed + t.closed,
    }),
    { assigned: 0, outreach_sent: 0, in_progress: 0, closed: 0 }
  );

  const handleTeamSort = (key: string) => {
    const { key: k, dir } = nextSort(teamSortBy, teamSortDir, key);
    setTeamSortBy(k); setTeamSortDir(dir);
  };
  const handlePortfolioSort = (key: string) => {
    const { key: k, dir } = nextSort(portfolioSortBy, portfolioSortDir, key);
    setPortfolioSortBy(k); setPortfolioSortDir(dir);
  };
  const sortedFiltered = sortRows(filtered, teamSortBy, teamSortDir);
  const sortedPortfolio = sortRows(portfolio, portfolioSortBy, portfolioSortDir);

  const dateRangeSelect = (
    <select
      value={days}
      onChange={(e) => setDays(Number(e.target.value))}
      className="border border-slate-300 rounded-lg px-3 py-2 text-sm bg-white"
    >
      <option value={30}>Last 30 Days</option>
      <option value={60}>Last 60 Days</option>
      <option value={90}>Last 90 Days</option>
    </select>
  );

  if (loading) return <LoadingState label="Loading sales team..." />;

  if (selected) {
    return (
      <div>
        <button onClick={() => setSelected(null)} className="text-sm text-blue-600 mb-4">&larr; Back to Sales Team</button>
        <PageHeader title={selected.name} subtitle={`${selected.region} Region`} action={dateRangeSelect} />
        <div className="grid grid-cols-4 gap-4 mb-6">
          <KpiCard label="Assigned" value={selected.assigned} />
          <KpiCard label="Outreach Sent" value={selected.outreach_sent} accent="#fab219" />
          <KpiCard label="In Progress" value={selected.in_progress} accent="#4a3aa7" />
          <KpiCard label="Closed" value={selected.closed} accent="#0ca30c" />
        </div>
        <Card>
          <h3 className="text-sm font-semibold text-slate-700 mb-3">Opportunity Portfolio</h3>
          <table className="w-full text-sm">
            <thead>
              <tr className={TABLE_HEAD_ROW_CLASS}>
                <SortableTh label="Carrier" sortKey="carrier_legal_name" activeKey={portfolioSortBy} dir={portfolioSortDir} onSort={handlePortfolioSort} />
                <SortableTh label="State" sortKey="state" activeKey={portfolioSortBy} dir={portfolioSortDir} onSort={handlePortfolioSort} />
                <SortableTh label="Status" sortKey="status" activeKey={portfolioSortBy} dir={portfolioSortDir} onSort={handlePortfolioSort} />
                <SortableTh label="Outreach" sortKey="outreach_status" activeKey={portfolioSortBy} dir={portfolioSortDir} onSort={handlePortfolioSort} />
              </tr>
            </thead>
            <tbody>
              {sortedPortfolio.map((o, i) => (
                <tr key={o.opportunity_id} onClick={() => setSelectedOpp(o.opportunity_id)}
                  className={tableRowClass(i, "hover:bg-blue-100 cursor-pointer border-b border-slate-100")}>
                  <td className="py-2 px-3 font-medium text-slate-900">{o.carrier_legal_name}</td>
                  <td className="py-2 px-3 text-slate-600">{o.state}</td>
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

  return (
    <div>
      <PageHeader title="Sales Team" subtitle={`${filtered.length} of ${team.length} salespeople`} action={dateRangeSelect} />

      <div className="grid grid-cols-4 gap-4 mb-6">
        <KpiCard label="Assigned" value={totals.assigned} />
        <KpiCard label="Outreach Sent" value={totals.outreach_sent} accent="#fab219" />
        <KpiCard label="In Progress" value={totals.in_progress} accent="#4a3aa7" />
        <KpiCard label="Closed" value={totals.closed} accent="#0ca30c" />
      </div>

      <Card className="mb-4">
        <div className="flex gap-3">
          <select value={regionFilter} onChange={(e) => setRegionFilter(e.target.value)}
            className="border border-slate-300 rounded-lg px-3 py-2 text-sm bg-white">
            <option value="">All Regions</option>
            {regions.map((r) => <option key={r} value={r}>{r}</option>)}
          </select>
          <select value={managerFilter} onChange={(e) => setManagerFilter(e.target.value)}
            className="border border-slate-300 rounded-lg px-3 py-2 text-sm bg-white">
            <option value="">All Managers</option>
            {managers.map((m) => <option key={m} value={m}>{m}</option>)}
          </select>
        </div>
      </Card>
      <Card>
        <table className="w-full text-sm">
          <thead>
            <tr className={TABLE_HEAD_ROW_CLASS}>
              <SortableTh label="Salesperson" sortKey="name" activeKey={teamSortBy} dir={teamSortDir} onSort={handleTeamSort} />
              <SortableTh label="Region" sortKey="region" activeKey={teamSortBy} dir={teamSortDir} onSort={handleTeamSort} />
              <SortableTh label="Manager" sortKey="manager_name" activeKey={teamSortBy} dir={teamSortDir} onSort={handleTeamSort} />
              <SortableTh label="Assigned" sortKey="assigned" activeKey={teamSortBy} dir={teamSortDir} onSort={handleTeamSort} />
              <SortableTh label="Outreach Sent" sortKey="outreach_sent" activeKey={teamSortBy} dir={teamSortDir} onSort={handleTeamSort} />
              <SortableTh label="In Progress" sortKey="in_progress" activeKey={teamSortBy} dir={teamSortDir} onSort={handleTeamSort} />
              <SortableTh label="Closed" sortKey="closed" activeKey={teamSortBy} dir={teamSortDir} onSort={handleTeamSort} />
            </tr>
          </thead>
          <tbody>
            {sortedFiltered.map((s, i) => (
              <tr key={s.salesperson_id} onClick={() => setSelected(s)}
                className={tableRowClass(i, "hover:bg-blue-100 cursor-pointer border-b border-slate-100")}>
                <td className="py-2 px-3 font-medium text-slate-900">{s.name}</td>
                <td className="py-2 px-3 text-slate-600">{s.region}</td>
                <td className="py-2 px-3 text-slate-600">{s.manager_name}</td>
                <td className="py-2 px-3 text-slate-600 tabular-nums">{s.assigned}</td>
                <td className="py-2 px-3 text-slate-600 tabular-nums">{s.outreach_sent}</td>
                <td className="py-2 px-3 text-slate-600 tabular-nums">{s.in_progress}</td>
                <td className="py-2 px-3 text-slate-600 tabular-nums">{s.closed}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  );
}
