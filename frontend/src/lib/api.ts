/**
 * Typed API client for the Customer Success FTE backend.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// --- Types ---

export interface SupportFormData {
  name: string;
  email: string;
  category: string;
  message: string;
}

export interface SubmitResponse {
  ticket_id: string;
  status: string;
  message: string;
}

export interface TicketStatus {
  ticket_id: string;
  status: "processing" | "responded" | "escalated";
  response: string | null;
  escalated: boolean;
}

export interface DailyReport {
  date: string;
  total_messages: number;
  average_sentiment: number;
  sentiment_trend: string;
  escalation_rate: number;
  top_issues: { reason: string; count: number }[];
  channel_breakdown: Record<
    string,
    { count: number; avg_sentiment: number; escalations: number }
  >;
}

export interface PendingApproval {
  ticket_id: string;
  customer_name: string;
  customer_email: string | null;
  channel: string;
  issue: string;
  priority: string;
  status: string;
  ai_response: string | null;
  response_generated_at: string | null;
  created_at: string;
  updated_at: string;
  metadata: Record<string, unknown>;
}

export interface AdminTicket {
  ticket_id: string;
  customer_name: string;
  customer_email: string | null;
  channel: string;
  issue: string;
  priority: string;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface AdminStats {
  total_tickets: number;
  pending_approval: number;
  resolved: number;
  escalated: number;
  open: number;
  recent_24h: number;
  channel_breakdown: { channel: string; count: number }[];
}

// --- API functions ---

export async function submitSupportForm(
  data: SupportFormData
): Promise<SubmitResponse> {
  const res = await fetch(`${API_BASE}/api/support`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Submission failed" }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }

  return res.json();
}

export async function getTicketStatus(
  ticketId: string
): Promise<TicketStatus> {
  const res = await fetch(`${API_BASE}/api/support/${ticketId}/status`);

  if (!res.ok) {
    if (res.status === 404) {
      throw new Error("Ticket not found");
    }
    throw new Error(`HTTP ${res.status}`);
  }

  return res.json();
}

export async function getDailyReport(
  date?: string
): Promise<DailyReport> {
  const params = date ? `?date=${date}` : "";
  const res = await fetch(`${API_BASE}/api/reports/daily${params}`);

  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`);
  }

  return res.json();
}

export async function getHealthStatus(): Promise<{
  status: string;
  checks: Record<string, string>;
}> {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

// --- Admin API ---

export async function getPendingApprovals(): Promise<PendingApproval[]> {
  const res = await fetch(`${API_BASE}/api/admin/pending-approvals`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function approveResponse(ticketId: string): Promise<{ status: string; message: string }> {
  const res = await fetch(`${API_BASE}/api/admin/approve/${ticketId}`, {
    method: "POST",
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Approval failed" }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

export async function rejectResponse(ticketId: string): Promise<{ status: string; message: string }> {
  const res = await fetch(`${API_BASE}/api/admin/reject/${ticketId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action: "reject" }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Rejection failed" }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

export async function getAdminTickets(status?: string): Promise<AdminTicket[]> {
  const params = status ? `?status=${status}` : "";
  const res = await fetch(`${API_BASE}/api/admin/tickets${params}`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function getAdminStats(): Promise<AdminStats> {
  const res = await fetch(`${API_BASE}/api/admin/stats`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}
