/**
 * T038: Typed API client for the Customer Success FTE backend.
 *
 * submitSupportForm(data) — POST /api/support
 * getTicketStatus(ticketId) — GET /api/support/{ticketId}/status
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
