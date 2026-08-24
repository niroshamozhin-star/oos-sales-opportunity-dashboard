// client.ts - the ONLY place the frontend talks to the backend. No
// secrets live here - just the backend base URL, which is public
// information (it's just an HTTP endpoint on localhost/the deployed API).

import axios from "axios";
import type {
  OpportunitiesResponse, OpportunityDetail, DashboardMetrics, TrendPoint,
  StateCount, StatusCount, Opportunity, SalespersonSummary, OutreachKpis,
  OutreachListItem, GenerateOutreachResponse, AssistantResponse, OpportunityStatus,
} from "./types";

const api = axios.create({ baseURL: "http://localhost:8700/api" });

export interface OpportunityFilters {
  state?: string;
  salesperson_id?: number;
  manager_id?: number;
  status?: string;
  outreach_status?: string;
  search?: string;
  date_from?: string;
  date_to?: string;
  limit?: number;
  offset?: number;
  sort_by?: string;
  sort_dir?: "asc" | "desc";
}

export const getMetrics = (days = 60) =>
  api.get<DashboardMetrics>("/overview/metrics", { params: { days } }).then((r) => r.data);

export const getTrend = (days = 60, granularity: "daily" | "weekly" = "daily") =>
  api.get<{ data: TrendPoint[] }>("/overview/trend", { params: { days, granularity } }).then((r) => r.data.data);

export const getByState = (days = 60, limit = 10) =>
  api.get<{ data: StateCount[] }>("/overview/by-state", { params: { days, limit } }).then((r) => r.data.data);

export const getByStatus = (days = 60) =>
  api.get<{ data: StatusCount[] }>("/overview/by-status", { params: { days } }).then((r) => r.data.data);

export const getRecentOpportunities = (limit = 10) =>
  api.get<{ data: Opportunity[] }>("/overview/recent", { params: { limit } }).then((r) => r.data.data);

export const getOpportunities = (filters: OpportunityFilters) =>
  api.get<OpportunitiesResponse>("/opportunities", { params: filters }).then((r) => r.data);

export const getOpportunity = (id: number) =>
  api.get<OpportunityDetail>(`/opportunities/${id}`).then((r) => r.data);

export const updateOpportunityStatus = (id: number, status: OpportunityStatus) =>
  api.post(`/opportunities/${id}/status`, { status }).then((r) => r.data);

export const assignSalesperson = (id: number) =>
  api.post<{ status: string; salesperson_name: string; manager_name: string }>(`/opportunities/${id}/assign`).then((r) => r.data);

export const generateOutreach = (id: number) =>
  api.post<GenerateOutreachResponse>(`/opportunities/${id}/generate-outreach`).then((r) => r.data);

export const sendOutreach = (id: number) =>
  api.post(`/opportunities/${id}/send-outreach`).then((r) => r.data);

export const getSalesTeam = (days = 60) =>
  api.get<{ data: SalespersonSummary[] }>("/sales-team", { params: { days } }).then((r) => r.data.data);

export const getSalespersonOpportunities = (id: number, days = 60, limit = 50, offset = 0) =>
  api.get<OpportunitiesResponse>(`/sales-team/${id}/opportunities`, { params: { days, limit, offset } }).then((r) => r.data);

export const getOutreachKpis = () =>
  api.get<OutreachKpis>("/outreach/kpis").then((r) => r.data);

export const getOutreachByState = () =>
  api.get<{ data: StateCount[] }>("/outreach/by-state").then((r) => r.data.data);

export const getOutreachBySalesperson = () =>
  api.get<{ data: { salesperson: string; count: number }[] }>("/outreach/by-salesperson").then((r) => r.data.data);

export const getOutreachTrend = (
  granularity: "daily" | "weekly" | "monthly" | "week_of_month" = "monthly",
  month?: string,
) =>
  api.get<{ data: { date: string; count: number }[] }>("/outreach/trend", { params: { granularity, month } }).then((r) => r.data.data);

export const getOutreachList = (filters: {
  state?: string; salesperson_id?: number; status?: string; limit?: number; offset?: number;
  sort_by?: string; sort_dir?: "asc" | "desc";
}) =>
  api.get<{ total: number; data: OutreachListItem[] }>("/outreach", { params: filters }).then((r) => r.data);

export const askAssistant = (question: string) =>
  api.post<AssistantResponse>("/assistant/ask", { question }).then((r) => r.data);

// Starts a fresh Foundry conversation thread - call this whenever the AI
// Assistant page is opened, so leftover context from an earlier, unrelated
// conversation (including backend testing traffic) never bleeds into a
// new session's answers.
export const resetAssistant = () =>
  api.post("/assistant/reset").then((r) => r.data);

export interface RefreshResult {
  ok: boolean;
  checked?: number;
  added?: number;
  indexed?: number;
  message?: string;
  error?: string;
}

// No client-side timeout - a live FMCSA/MCMIS sync can legitimately take
// up to a minute or so; the button shows its own "syncing" state instead.
export const refreshData = () =>
  api.post<RefreshResult>("/refresh", undefined, { timeout: 0 }).then((r) => r.data);
