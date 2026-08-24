import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Search } from "lucide-react";
import { getOpportunities, getSalesTeam, generateOutreach } from "../api/client";
import type { Opportunity, SalespersonSummary } from "../api/types";
import {
  PageHeader, Card, StatusBadge, LoadingState, EmptyState, ErrorBanner,
  TABLE_HEAD_ROW_CLASS, tableRowClass, SortableTh, nextSort, PageSizeSelect,
} from "../components/shared";
import type { SortDir } from "../components/shared";
import OpportunityDrawer from "../components/OpportunityDrawer";

const STATUSES = ["NEW", "ASSIGNED", "OUTREACH_SENT", "IN_PROGRESS", "CLOSED"];
const OUTREACH_STATUSES = ["NOT_STARTED", "SENT"];

export default function Opportunities() {
  const [params, setParams] = useSearchParams();
  const [items, setItems] = useState<Opportunity[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(10);
  const [sortBy, setSortBy] = useState<string | null>("oos_date");
  const [sortDir, setSortDir] = useState<SortDir>("desc");
  const [loading, setLoading] = useState(true);
  const [salespeople, setSalespeople] = useState<SalespersonSummary[]>([]);
  const [selectedOpp, setSelectedOpp] = useState<number | null>(null);
  const [generatingId, setGeneratingId] = useState<number | null>(null);
  const [genError, setGenError] = useState<string | null>(null);

  const [search, setSearch] = useState("");
  const state = params.get("state") ?? "";
  const status = params.get("status") ?? "";
  const outreachStatus = params.get("outreach_status") ?? "";
  const salespersonId = params.get("salesperson_id") ?? "";

  useEffect(() => {
    getSalesTeam().then(setSalespeople);
  }, []);

  const load = () => {
    setLoading(true);
    getOpportunities({
      state: state || undefined,
      status: status || undefined,
      outreach_status: outreachStatus || undefined,
      salesperson_id: salespersonId ? Number(salespersonId) : undefined,
      search: search || undefined,
      limit: pageSize,
      offset: page * pageSize,
      sort_by: sortBy ?? undefined,
      sort_dir: sortDir,
    }).then((res) => {
      setItems(res.items);
      setTotal(res.total);
    }).finally(() => setLoading(false));
  };

  useEffect(load, [state, status, outreachStatus, salespersonId, search, page, pageSize, sortBy, sortDir]);
  useEffect(() => setPage(0), [state, status, outreachStatus, salespersonId, search, pageSize, sortBy, sortDir]);

  const updateFilter = (key: string, value: string) => {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value); else next.delete(key);
    setParams(next);
  };

  const handleSort = (key: string) => {
    const { key: k, dir } = nextSort(sortBy, sortDir, key);
    setSortBy(k); setSortDir(dir);
  };

  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  const handleGenerate = async (opp: Opportunity, e: React.MouseEvent) => {
    e.stopPropagation();
    setGenError(null);
    setGeneratingId(opp.opportunity_id);
    try {
      const res = await generateOutreach(opp.opportunity_id);
      if (!res.available) {
        setGenError(res.error ?? "AI Assistant is temporarily unavailable.");
      } else {
        load();
        setSelectedOpp(opp.opportunity_id);
      }
    } finally {
      setGeneratingId(null);
    }
  };

  return (
    <div>
      <PageHeader title="Opportunities" subtitle={`${total} total opportunities`} />

      <Card className="mb-4">
        <div className="flex flex-wrap gap-3 items-center">
          <div className="relative">
            <Search className="absolute left-3 top-2.5 w-4 h-4 text-slate-400" />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search carrier name..."
              className="pl-9 pr-3 py-2 border border-slate-300 rounded-lg text-sm w-64"
            />
          </div>
          <Select label="State" value={state} onChange={(v) => updateFilter("state", v)}
            options={[...new Set(items.map((i) => i.state))].sort()} allLabel="All States" />
          <Select label="Status" value={status} onChange={(v) => updateFilter("status", v)}
            options={STATUSES} allLabel="All Statuses" />
          <Select label="Outreach" value={outreachStatus} onChange={(v) => updateFilter("outreach_status", v)}
            options={OUTREACH_STATUSES} allLabel="All Outreach" />
          <Select label="Salesperson" value={salespersonId} onChange={(v) => updateFilter("salesperson_id", v)}
            options={salespeople.map((s) => String(s.salesperson_id))}
            optionLabels={Object.fromEntries(salespeople.map((s) => [String(s.salesperson_id), s.name]))}
            allLabel="All Salespeople" />
        </div>
      </Card>

      {genError && <div className="mb-4"><ErrorBanner message={genError} /></div>}

      <Card>
        <div className="flex items-center justify-between mb-3 flex-wrap gap-3">
          <h3 className="text-sm font-semibold text-slate-700">Opportunities <span className="text-slate-400 font-normal">({total} total)</span></h3>
          <div className="flex items-center gap-2">
            <PageSizeSelect value={pageSize} onChange={setPageSize} />
            <span className="text-sm text-slate-600 whitespace-nowrap">Page {page + 1} of {totalPages}</span>
            <button disabled={page === 0} onClick={() => setPage((p) => p - 1)}
              className="px-3 py-1.5 border border-slate-300 rounded-lg text-sm disabled:opacity-40">Previous</button>
            <button disabled={page >= totalPages - 1} onClick={() => setPage((p) => p + 1)}
              className="px-3 py-1.5 border border-slate-300 rounded-lg text-sm disabled:opacity-40">Next</button>
          </div>
        </div>
        {loading ? <LoadingState /> : items.length === 0 ? <EmptyState message="No opportunities match these filters." /> : (
          <>
            <table className="w-full text-sm">
              <thead>
                <tr className={TABLE_HEAD_ROW_CLASS}>
                  <SortableTh label="ID" sortKey="opportunity_id" activeKey={sortBy} dir={sortDir} onSort={handleSort} />
                  <SortableTh label="Carrier" sortKey="carrier_legal_name" activeKey={sortBy} dir={sortDir} onSort={handleSort} />
                  <SortableTh label="OOS Date" sortKey="oos_date" activeKey={sortBy} dir={sortDir} onSort={handleSort} />
                  <th className="py-2.5 px-3 bg-slate-900">OOS Reason</th>
                  <SortableTh label="City" sortKey="city" activeKey={sortBy} dir={sortDir} onSort={handleSort} />
                  <SortableTh label="State" sortKey="state" activeKey={sortBy} dir={sortDir} onSort={handleSort} />
                  <SortableTh label="Salesperson" sortKey="salesperson_name" activeKey={sortBy} dir={sortDir} onSort={handleSort} />
                  <SortableTh label="Manager" sortKey="manager_name" activeKey={sortBy} dir={sortDir} onSort={handleSort} />
                  <SortableTh label="Status" sortKey="status" activeKey={sortBy} dir={sortDir} onSort={handleSort} />
                  <SortableTh label="Outreach" sortKey="outreach_status" activeKey={sortBy} dir={sortDir} onSort={handleSort} />
                  <SortableTh label="Last Updated" sortKey="updated_at" activeKey={sortBy} dir={sortDir} onSort={handleSort} />
                </tr>
              </thead>
              <tbody>
                {items.map((o, i) => (
                  <tr key={o.opportunity_id} onClick={() => setSelectedOpp(o.opportunity_id)}
                    className={tableRowClass(i, "hover:bg-blue-100 cursor-pointer border-b border-slate-100")}>
                    <td className="py-2 px-3 text-slate-400">#{o.opportunity_id}</td>
                    <td className="py-2 px-3 font-medium text-slate-900">{o.carrier_legal_name}</td>
                    <td className="py-2 px-3 text-slate-600">{o.oos_date}</td>
                    <td className="py-2 px-3 text-slate-600 max-w-[200px] truncate">{o.oos_reason}</td>
                    <td className="py-2 px-3 text-slate-600">{o.city}</td>
                    <td className="py-2 px-3 text-slate-600">{o.state}</td>
                    <td className="py-2 px-3 text-slate-600">{o.salesperson_name ?? "Unassigned"}</td>
                    <td className="py-2 px-3 text-slate-600">{o.manager_name ?? "—"}</td>
                    <td className="py-2 px-3"><StatusBadge status={o.status} /></td>
                    <td className="py-2 px-3">
                      {o.outreach_status === "NOT_STARTED" ? (
                        <button
                          onClick={(e) => handleGenerate(o, e)}
                          disabled={!o.salesperson_id || generatingId === o.opportunity_id}
                          className="text-blue-600 hover:text-blue-700 text-xs font-semibold underline disabled:opacity-40 disabled:no-underline disabled:cursor-not-allowed"
                        >
                          {generatingId === o.opportunity_id ? "Generating..." : "Generate"}
                        </button>
                      ) : (
                        <StatusBadge status={o.outreach_status} />
                      )}
                    </td>
                    <td className="py-2 px-3 text-slate-500 text-xs">{o.updated_at}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </>
        )}
      </Card>

      <OpportunityDrawer opportunityId={selectedOpp} onClose={() => setSelectedOpp(null)} onChanged={load} />
    </div>
  );
}

function Select({ label, value, onChange, options, optionLabels, allLabel }: {
  label: string; value: string; onChange: (v: string) => void; options: string[];
  optionLabels?: Record<string, string>; allLabel: string;
}) {
  return (
    <select
      aria-label={label}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="border border-slate-300 rounded-lg px-3 py-2 text-sm bg-white"
    >
      <option value="">{allLabel}</option>
      {options.map((o) => (
        <option key={o} value={o}>{optionLabels?.[o] ?? o.replace(/_/g, " ")}</option>
      ))}
    </select>
  );
}
