import { useState } from "react";
import { NavLink } from "react-router-dom";
import { LayoutDashboard, ListChecks, Users, Send, Bot, Truck, RefreshCw } from "lucide-react";
import { refreshData } from "../api/client";

const navItems = [
  { to: "/", label: "Overview", icon: LayoutDashboard, end: true },
  { to: "/opportunities", label: "Opportunities", icon: ListChecks },
  { to: "/sales-team", label: "Sales Team", icon: Users },
  { to: "/outreach", label: "Outreach", icon: Send },
  { to: "/assistant", label: "AI Sales Assistant", icon: Bot },
];

export default function Sidebar() {
  const [syncing, setSyncing] = useState(false);
  const [result, setResult] = useState<{ text: string; isError: boolean } | null>(null);

  const handleRefresh = async () => {
    setSyncing(true);
    setResult(null);
    try {
      const res = await refreshData();
      if (!res.ok) {
        setResult({ text: res.error ?? "Refresh failed.", isError: true });
      } else {
        setResult({ text: res.message ?? "Done.", isError: false });
        if (res.added) {
          setTimeout(() => window.location.reload(), 1800);
        } else {
          setTimeout(() => setResult(null), 4000);
        }
      }
    } catch {
      setResult({ text: "Could not reach the backend to refresh data.", isError: true });
    } finally {
      setSyncing(false);
    }
  };

  return (
    <aside className="w-64 shrink-0 bg-gradient-to-b from-slate-950 via-slate-900 to-indigo-950 text-slate-200 h-screen sticky top-0 flex flex-col shadow-lg">
      <div className="flex items-center gap-2.5 px-5 py-5 border-b border-white/10">
        <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-blue-500 to-violet-600 flex items-center justify-center shadow-md shadow-blue-900/40 shrink-0">
          <Truck className="w-5 h-5 text-white" />
        </div>
        <div className="leading-tight">
          <div className="font-display text-sm font-bold text-white tracking-tight">OOS Sales Opportunity</div>
          <div className="text-xs text-slate-400">Dashboard</div>
        </div>
      </div>

      <nav className="flex-1 py-4 px-3 space-y-1.5 overflow-y-auto">
        {navItems.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              `flex items-center gap-3 px-4 py-3 rounded-lg text-base font-semibold transition-all ${
                isActive
                  ? "bg-gradient-to-r from-blue-600 to-violet-600 text-white shadow-md"
                  : "text-slate-300 hover:bg-white/10 hover:text-white"
              }`
            }
          >
            <Icon className="w-5 h-5 shrink-0" />
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="px-3 pb-4 pt-2 border-t border-white/10 space-y-2">
        {result && (
          <div className={`text-xs px-1 ${result.isError ? "text-red-300" : "text-emerald-300"}`}>
            {result.text}
          </div>
        )}
        <button
          onClick={handleRefresh}
          disabled={syncing}
          title="Fetch the latest OOS data from FMCSA and MCMIS"
          className="w-full flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg text-xs font-semibold bg-white/10 text-slate-200 hover:bg-white/20 disabled:opacity-60 transition-colors"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${syncing ? "animate-spin" : ""}`} />
          {syncing ? "Syncing..." : "Refresh Data"}
        </button>
      </div>
    </aside>
  );
}
