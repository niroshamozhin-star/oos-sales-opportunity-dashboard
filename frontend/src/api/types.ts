// types.ts - mirrors the FastAPI backend's response shapes exactly.
// Keeping these in one file makes it obvious when the frontend and
// backend drift apart.

export type OpportunityStatus = "NEW" | "ASSIGNED" | "OUTREACH_SENT" | "IN_PROGRESS" | "CLOSED";
export type OutreachStatus = "NOT_STARTED" | "SENT";

export interface Opportunity {
  opportunity_id: number;
  dot_number: string;
  carrier_legal_name: string;
  oos_date: string;
  oos_reason: string;
  city: string;
  state: string;
  salesperson_id: number | null;
  manager_id: number | null;
  salesperson_name: string | null;
  manager_name: string | null;
  status: OpportunityStatus;
  outreach_status: OutreachStatus;
  created_at: string;
  updated_at: string;
}

export interface StatusHistoryEntry {
  history_id: number;
  opportunity_id: number;
  previous_status: OpportunityStatus | null;
  new_status: OpportunityStatus;
  changed_at: string;
  changed_by: string;
}

export interface OutreachRecord {
  outreach_id: number;
  opportunity_id: number;
  salesperson_id: number | null;
  generated_at: string | null;
  sent_at: string | null;
  status: "NOT_GENERATED" | "GENERATED" | "SENT";
  message: string | null;
}

export interface OpportunityDetail extends Opportunity {
  history: StatusHistoryEntry[];
  outreach: OutreachRecord | null;
}

export interface OpportunitiesResponse {
  total: number;
  items: Opportunity[];
}

export interface DashboardMetrics {
  new_opportunities: number;
  assigned: number;
  outreach_sent: number;
  in_progress: number;
  closed: number;
  date_from: string | null;
  date_to: string | null;
  label: string;
}

export interface TrendPoint {
  bucket: string;
  count: number;
}

export interface StateCount {
  state: string;
  count: number;
}

export interface StatusCount {
  status: OpportunityStatus;
  count: number;
}

export interface SalespersonSummary {
  salesperson_id: number;
  name: string;
  region: string;
  manager_name: string;
  assigned: number;
  outreach_sent: number;
  in_progress: number;
  closed: number;
}

export interface OutreachKpis {
  generated: number;
  sent: number;
  pending: number;
}

export interface OutreachListItem {
  outreach_id: number;
  carrier: string;
  salesperson: string | null;
  generated_at: string | null;
  sent_at: string | null;
  status: string;
}

export interface GenerateOutreachResponse {
  available: boolean;
  message: string | null;
  error: string | null;
}

export interface AssistantResponse {
  available: boolean;
  answer: string | null;
  error: string | null;
}
