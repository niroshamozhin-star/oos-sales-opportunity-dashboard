import type { ReactNode } from "react";
import { Loader2, AlertTriangle, Inbox, ChevronUp, ChevronDown, ChevronsUpDown } from "lucide-react";

// ---- Palette (same reference instance used across the project) ----
export const SERIES_BLUE = "#2a78d6";
export const SEQUENTIAL_BLUE = ["#cde2fb", "#9ec5f4", "#5598e7", "#2a78d6", "#184f95"];
export const STATUS_GOOD = "#0ca30c";
export const STATUS_WARNING = "#fab219";
export const STATUS_CRITICAL = "#d03b3b";

export function PageHeader({ title, subtitle, action }: { title: string; subtitle?: string; action?: ReactNode }) {
  return (
    <div className="flex items-start justify-between mb-6">
      <div>
        <h1 className="text-3xl md:text-4xl font-extrabold tracking-tight bg-gradient-to-r from-blue-700 via-indigo-600 to-violet-600 bg-clip-text text-transparent">
          {title}
        </h1>
        {subtitle && <p className="text-sm text-slate-500 mt-1.5">{subtitle}</p>}
      </div>
      {action}
    </div>
  );
}

export function KpiCard({ label, value, accent = SERIES_BLUE, onClick }: {
  label: string; value: number | string; accent?: string; onClick?: () => void;
}) {
  return (
    <div
      onClick={onClick}
      className={`bg-white/90 backdrop-blur-sm border border-slate-200/70 shadow-sm rounded-xl p-4 border-t-4 ${onClick ? "cursor-pointer hover:shadow-lg hover:-translate-y-0.5 transition-all" : ""}`}
      style={{ borderTopColor: accent }}
    >
      <div className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">{label}</div>
      <div className="font-display text-3xl font-extrabold text-slate-900 tabular-nums">{value}</div>
    </div>
  );
}

const STATUS_STYLES: Record<string, string> = {
  NEW: "bg-slate-100 text-slate-700",
  ASSIGNED: "bg-blue-100 text-blue-700",
  OUTREACH_SENT: "bg-amber-100 text-amber-700",
  IN_PROGRESS: "bg-violet-100 text-violet-700",
  CLOSED: "bg-emerald-100 text-emerald-700",
  NOT_STARTED: "bg-slate-100 text-slate-700",
  SENT: "bg-emerald-100 text-emerald-700",
  NOT_GENERATED: "bg-slate-100 text-slate-700",
  GENERATED: "bg-amber-100 text-amber-700",
};

export function StatusBadge({ status }: { status: string }) {
  const style = STATUS_STYLES[status] ?? "bg-slate-100 text-slate-700";
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${style}`}>
      {status.replace(/_/g, " ")}
    </span>
  );
}

export function LoadingState({ label = "Loading..." }: { label?: string }) {
  return (
    <div className="flex items-center justify-center gap-2 text-slate-400 py-16">
      <Loader2 className="w-5 h-5 animate-spin" />
      <span className="text-sm">{label}</span>
    </div>
  );
}

export function ErrorBanner({ message }: { message: string }) {
  return (
    <div className="flex items-center gap-2 bg-red-50 border border-red-200 text-red-700 rounded-lg px-4 py-3 text-sm">
      <AlertTriangle className="w-4 h-4 shrink-0" />
      {message}
    </div>
  );
}

export function EmptyState({ message = "No results found." }: { message?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 text-slate-400 py-16">
      <Inbox className="w-8 h-8" />
      <span className="text-sm">{message}</span>
    </div>
  );
}

export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <div className={`bg-white/95 backdrop-blur-sm border border-slate-200/70 shadow-sm rounded-xl p-5 ${className}`}>{children}</div>;
}

// Deep-navy enterprise chart card - same treatment as the Overview charts.
export function DarkCard({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <div className={`bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm ${className}`}>{children}</div>;
}

// Shared table styling: navy header with white text, light-blue zebra
// striping on alternating rows - applied to every data table in the app.
export const TABLE_HEAD_ROW_CLASS = "text-left text-xs font-semibold uppercase tracking-wide bg-slate-900 text-white";

export function tableRowClass(index: number, extra = "") {
  return `${index % 2 === 1 ? "bg-blue-50" : "bg-white"} ${extra}`.trim();
}

export type SortDir = "asc" | "desc";

// Clickable, sortable table header cell - works for both server-side sort
// (pass a callback that refetches) and client-side sort (pass a callback
// that just re-sorts the already-loaded array in state).
export function SortableTh({ label, sortKey, activeKey, dir, onSort, className = "" }: {
  label: string; sortKey: string; activeKey: string | null; dir: SortDir;
  onSort: (key: string) => void; className?: string;
}) {
  const active = activeKey === sortKey;
  return (
    <th
      onClick={() => onSort(sortKey)}
      className={`py-2.5 px-3 cursor-pointer select-none bg-slate-900 hover:bg-slate-800 transition-colors ${className}`}
    >
      <span className="inline-flex items-center gap-1">
        {label}
        {active ? (
          dir === "asc" ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />
        ) : (
          <ChevronsUpDown className="w-3.5 h-3.5 opacity-40" />
        )}
      </span>
    </th>
  );
}

// Toggles asc/desc when the same key is clicked again, otherwise starts a
// new sort on the new key in descending order.
export function nextSort(activeKey: string | null, dir: SortDir, key: string): { key: string; dir: SortDir } {
  if (activeKey === key) return { key, dir: dir === "asc" ? "desc" : "asc" };
  return { key, dir: "desc" };
}

export const PAGE_SIZE_OPTIONS = [10, 20, 50, 100];

export function PageSizeSelect({ value, onChange }: { value: number; onChange: (n: number) => void }) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(Number(e.target.value))}
      className="border border-slate-300 rounded-lg px-2.5 py-1.5 text-sm bg-white"
      aria-label="Rows per page"
    >
      {PAGE_SIZE_OPTIONS.map((n) => <option key={n} value={n}>{n} / page</option>)}
    </select>
  );
}
