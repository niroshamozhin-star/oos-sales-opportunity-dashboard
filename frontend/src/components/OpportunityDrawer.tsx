import { useEffect, useState } from "react";
import { X, Copy, Check, Sparkles, Send, PlayCircle, CheckCircle2, UserPlus } from "lucide-react";
import {
  getOpportunity, generateOutreach, sendOutreach, updateOpportunityStatus, assignSalesperson,
} from "../api/client";
import type { OpportunityDetail } from "../api/types";
import { StatusBadge, LoadingState, ErrorBanner } from "./shared";

export default function OpportunityDrawer({ opportunityId, onClose, onChanged }: {
  opportunityId: number | null;
  onClose: () => void;
  onChanged?: () => void;
}) {
  const [opp, setOpp] = useState<OpportunityDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [generating, setGenerating] = useState(false);
  const [sending, setSending] = useState(false);
  const [copied, setCopied] = useState(false);
  const [aiUnavailable, setAiUnavailable] = useState<string | null>(null);
  const [confirmingAssign, setConfirmingAssign] = useState(false);
  const [assigning, setAssigning] = useState(false);
  const [assignError, setAssignError] = useState<string | null>(null);

  const load = () => {
    if (!opportunityId) return;
    setLoading(true);
    setError(null);
    setConfirmingAssign(false);
    setAssignError(null);
    getOpportunity(opportunityId)
      .then(setOpp)
      .catch(() => setError("Could not load this opportunity."))
      .finally(() => setLoading(false));
  };

  useEffect(load, [opportunityId]);

  if (!opportunityId) return null;

  const handleGenerate = async () => {
    setGenerating(true);
    setAiUnavailable(null);
    try {
      const res = await generateOutreach(opportunityId);
      if (!res.available) {
        setAiUnavailable(res.error ?? "AI Assistant is temporarily unavailable.");
      } else {
        load();
      }
    } finally {
      setGenerating(false);
    }
  };

  const handleSend = async () => {
    setSending(true);
    try {
      await sendOutreach(opportunityId);
      load();
      onChanged?.();
    } finally {
      setSending(false);
    }
  };

  const handleStatus = async (status: string) => {
    await updateOpportunityStatus(opportunityId, status as any);
    load();
    onChanged?.();
  };

  const handleAssign = async () => {
    setAssigning(true);
    setAssignError(null);
    try {
      await assignSalesperson(opportunityId);
      load();
      onChanged?.();
    } catch (e: any) {
      setAssignError(e?.response?.data?.detail ?? "Could not assign this opportunity.");
      setConfirmingAssign(false);
    } finally {
      setAssigning(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      <div className="absolute inset-0 bg-black/30" onClick={onClose} />
      <div className="relative bg-white w-full max-w-md h-full shadow-xl overflow-y-auto">
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-200 sticky top-0 bg-white z-10">
          <h2 className="text-base font-semibold text-slate-900">Opportunity Details</h2>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600">
            <X className="w-5 h-5" />
          </button>
        </div>

        {loading && <LoadingState />}
        {error && <div className="p-5"><ErrorBanner message={error} /></div>}

        {opp && (
          <div className="p-5 space-y-6">
            <section>
              <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">Carrier Information</h3>
              <dl className="text-sm space-y-1">
                <Row label="Legal Name" value={opp.carrier_legal_name} />
                <Row label="OOS Date" value={opp.oos_date} />
                <Row label="OOS Reason" value={opp.oos_reason} />
                <Row label="City" value={opp.city} />
                <Row label="State" value={opp.state} />
              </dl>
            </section>

            <section>
              <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">Sales Assignment</h3>
              <dl className="text-sm space-y-1">
                <Row label="Salesperson" value={opp.salesperson_name ?? "Unassigned"} />
                <Row label="Manager" value={opp.manager_name ?? "Unassigned"} />
              </dl>

              {!opp.salesperson_id && (
                <div className="mt-3">
                  {assignError && <div className="mb-2"><ErrorBanner message={assignError} /></div>}
                  {!confirmingAssign ? (
                    <button
                      onClick={() => setConfirmingAssign(true)}
                      className="w-full flex items-center justify-center gap-2 bg-slate-900 text-white text-sm font-medium rounded-lg py-2.5 hover:bg-slate-800"
                    >
                      <UserPlus className="w-4 h-4" /> Assign Salesperson
                    </button>
                  ) : (
                    <div className="bg-slate-50 border border-slate-200 rounded-lg p-3 space-y-2">
                      <p className="text-xs text-slate-600">
                        Assign this opportunity to the salesperson responsible for {opp.state}?
                      </p>
                      <div className="flex gap-2">
                        <button
                          onClick={handleAssign}
                          disabled={assigning}
                          className="flex-1 bg-blue-600 text-white text-sm font-medium rounded-lg py-2 disabled:opacity-50 hover:bg-blue-700"
                        >
                          {assigning ? "Assigning..." : "Confirm"}
                        </button>
                        <button
                          onClick={() => setConfirmingAssign(false)}
                          disabled={assigning}
                          className="flex-1 bg-white border border-slate-300 text-slate-700 text-sm font-medium rounded-lg py-2 disabled:opacity-50 hover:bg-slate-50"
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </section>

            <section>
              <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">Opportunity</h3>
              <dl className="text-sm space-y-1">
                <Row label="Opportunity ID" value={`#${opp.opportunity_id}`} />
                <Row label="Status" value={<StatusBadge status={opp.status} />} />
                <Row label="Created" value={opp.created_at} />
                <Row label="Last Updated" value={opp.updated_at} />
                <Row label="Outreach Status" value={<StatusBadge status={opp.outreach_status} />} />
              </dl>
            </section>

            <section>
              <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">Activity Timeline</h3>
              <ol className="text-sm space-y-1">
                {opp.history.map((h) => (
                  <li key={h.history_id} className="flex justify-between text-slate-600">
                    <span>{h.previous_status ? `${h.previous_status} → ${h.new_status}` : h.new_status}</span>
                    <span className="text-slate-400 text-xs">{h.changed_at}</span>
                  </li>
                ))}
              </ol>
            </section>

            {aiUnavailable && <ErrorBanner message={aiUnavailable} />}

            {opp.outreach?.message && (
              <section className="bg-slate-50 border border-slate-200 rounded-lg p-3">
                <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">Outreach Message</h3>
                <p className="text-sm text-slate-700">{opp.outreach.message}</p>
                <button
                  onClick={() => { navigator.clipboard.writeText(opp.outreach!.message!); setCopied(true); setTimeout(() => setCopied(false), 1500); }}
                  className="mt-2 inline-flex items-center gap-1.5 text-xs font-medium text-blue-600 hover:text-blue-700"
                >
                  {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                  {copied ? "Copied" : "Copy Message"}
                </button>
              </section>
            )}

            <section className="space-y-2">
              <button
                onClick={handleGenerate}
                disabled={generating || !opp.salesperson_id}
                className="w-full flex items-center justify-center gap-2 bg-blue-600 text-white text-sm font-medium rounded-lg py-2.5 disabled:opacity-50 hover:bg-blue-700"
              >
                <Sparkles className="w-4 h-4" />
                {generating ? "Generating via Foundry Agent..." : "Generate Outreach"}
              </button>
              <button
                onClick={handleSend}
                disabled={sending || !opp.outreach?.message || opp.outreach_status === "SENT"}
                className="w-full flex items-center justify-center gap-2 bg-white border border-slate-300 text-slate-700 text-sm font-medium rounded-lg py-2.5 disabled:opacity-50 hover:bg-slate-50"
              >
                <Send className="w-4 h-4" />
                {sending ? "Sending..." : "Send Outreach"}
              </button>
              <div className="flex gap-2">
                <button
                  onClick={() => handleStatus("IN_PROGRESS")}
                  disabled={opp.status !== "OUTREACH_SENT"}
                  className="flex-1 flex items-center justify-center gap-1.5 bg-white border border-slate-300 text-slate-700 text-xs font-medium rounded-lg py-2 disabled:opacity-50 hover:bg-slate-50"
                >
                  <PlayCircle className="w-3.5 h-3.5" /> Mark In Progress
                </button>
                <button
                  onClick={() => handleStatus("CLOSED")}
                  disabled={opp.status === "CLOSED" || opp.status === "NEW"}
                  className="flex-1 flex items-center justify-center gap-1.5 bg-white border border-slate-300 text-slate-700 text-xs font-medium rounded-lg py-2 disabled:opacity-50 hover:bg-slate-50"
                >
                  <CheckCircle2 className="w-3.5 h-3.5" /> Mark Closed
                </button>
              </div>
              {!opp.salesperson_id && (
                <p className="text-xs text-slate-400 text-center">Assign a salesperson above to enable outreach.</p>
              )}
            </section>
          </div>
        )}
      </div>
    </div>
  );
}

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex justify-between gap-4">
      <dt className="text-slate-500">{label}</dt>
      <dd className="text-slate-900 font-medium text-right">{value}</dd>
    </div>
  );
}
